"""Local multi-user face unlock for JARVIS (convenience security, not anti-spoofing)."""
from __future__ import annotations
import argparse, json, os, time
from pathlib import Path

DATA_DIR = Path(os.getenv("LOCALAPPDATA", str(Path.home()))) / "JARVIS" / "face_auth"
DATA_FILE = DATA_DIR / "face_samples.npz"
USERS_FILE = DATA_DIR / "users.json"
CASCADE_NAME = "haarcascade_frontalface_default.xml"
LAST_AUTH = {"name": None, "role": None}


def _opencv():
    try:
        import cv2
        import numpy as np
    except ImportError as exc:
        raise RuntimeError("Face unlock requires opencv-contrib-python. Install requirements-face.txt.") from exc
    if not hasattr(cv2, "face") or not hasattr(cv2.face, "LBPHFaceRecognizer_create"):
        raise RuntimeError("OpenCV face recognizer missing. Install opencv-contrib-python (not opencv-python).")
    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + CASCADE_NAME)
    if cascade.empty(): raise RuntimeError("OpenCV face detector could not load its cascade.")
    return cv2, np, cascade


def _load_profiles():
    if not USERS_FILE.exists(): return []
    try:
        data = json.loads(USERS_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, list): raise ValueError("profiles must be a list")
        return data
    except Exception as exc:
        raise RuntimeError(f"Face profile file is invalid: {exc}") from exc


def _load_samples():
    cv2, np, _ = _opencv()
    profiles = _load_profiles()
    if not DATA_FILE.exists() or not profiles: raise RuntimeError("No face profiles enrolled. Run --enroll-face Owner first.")
    archive = np.load(DATA_FILE, allow_pickle=False)
    faces, labels = archive.get("faces"), archive.get("labels")
    if faces is None or labels is None or len(faces) != len(labels): raise RuntimeError("Face sample database is damaged.")
    return cv2, np, profiles, faces, labels


def _capture(name, samples_required=35, camera_index=0):
    cv2, np, cascade = _opencv()
    cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
    if not cap.isOpened(): cap.release(); cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened(): raise RuntimeError("Cannot open webcam. Check Windows camera permissions.")
    samples=[]; last=0
    try:
        while len(samples) < samples_required:
            ok, frame=cap.read()
            if not ok: raise RuntimeError("Webcam frame capture failed during enrollment.")
            gray=cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            detected=cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(90,90))
            crop=None
            if len(detected)==1:
                x,y,w,h=detected[0]; crop=gray[y:y+h,x:x+w]
            if crop is not None and crop.size and time.time()-last>=0.18:
                samples.append(cv2.resize(crop,(160,160))); last=time.time()
            cv2.putText(frame,f"Enroll {name}: {len(samples)}/{samples_required} | Q cancel",(12,28),cv2.FONT_HERSHEY_SIMPLEX,.65,(0,220,0),2)
            cv2.imshow("JARVIS Face Enrollment",frame)
            if cv2.waitKey(1)&0xFF==ord('q'): break
    finally:
        cap.release(); cv2.destroyAllWindows()
    if len(samples)<max(12,samples_required//2): raise RuntimeError(f"Enrollment incomplete ({len(samples)} samples); nothing saved.")
    return np.asarray(samples,dtype=np.uint8)


def enroll(name="Owner", samples_required=35, camera_index=0):
    name=name.strip()
    if not name or len(name)>48: raise ValueError("Name must be 1–48 characters.")
    profiles=_load_profiles()
    if profiles:
        if not authenticate(role_required="admin", timeout_seconds=30): raise RuntimeError("Owner authentication required; enrollment cancelled.")
        if any(p["name"].casefold()==name.casefold() for p in profiles): raise ValueError("That face profile name already exists.")
        role="user"
    else:
        if name.casefold()!="owner": raise ValueError("First enrollment must be named Owner; it becomes administrator.")
        role="admin"
    samples=_capture(name,samples_required,camera_index)
    cv2,np,_=_opencv()
    if DATA_FILE.exists():
        old=np.load(DATA_FILE,allow_pickle=False); faces=old["faces"]; labels=old["labels"]
    else: faces=np.empty((0,160,160),dtype=np.uint8); labels=np.empty((0,),dtype=np.int32)
    label=max([int(p["id"]) for p in profiles],default=-1)+1
    faces=np.concatenate([faces,samples]); labels=np.concatenate([labels,np.full(len(samples),label,dtype=np.int32)])
    DATA_DIR.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(DATA_FILE,faces=faces,labels=labels)
    profiles.append({"id":label,"name":name,"role":role,"created":int(time.time())})
    USERS_FILE.write_text(json.dumps(profiles,indent=2),encoding="utf-8")
    print(f"Enrolled {name} ({role}) with {len(samples)} samples locally.")
    return len(samples)


def authenticate(timeout_seconds=30, threshold=58.0, camera_index=0, role_required=None):
    cv2,np,profiles,faces,labels=_load_samples()
    recognizer=cv2.face.LBPHFaceRecognizer_create(); recognizer.train(faces,labels)
    cap=cv2.VideoCapture(camera_index,cv2.CAP_DSHOW)
    if not cap.isOpened(): cap.release(); cap=cv2.VideoCapture(camera_index)
    if not cap.isOpened(): raise RuntimeError("Cannot open webcam. JARVIS remains locked.")
    deadline=time.monotonic()+timeout_seconds; streak=0; last_id=None
    cascade=cv2.CascadeClassifier(cv2.data.haarcascades+CASCADE_NAME)
    try:
        while time.monotonic()<deadline:
            ok,frame=cap.read()
            if not ok: raise RuntimeError("Webcam frame capture failed. JARVIS remains locked.")
            gray=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY); detected=cascade.detectMultiScale(gray,1.1,5,minSize=(90,90))
            match=None
            if len(detected)==1:
                x,y,w,h=detected[0]; crop=cv2.resize(gray[y:y+h,x:x+w],(160,160)); label,confidence=recognizer.predict(crop)
                p=next((u for u in profiles if int(u["id"])==int(label)),None)
                if p and confidence<=threshold and (role_required is None or p["role"]==role_required): match=p
            if match:
                if last_id==match["id"]: streak+=1
                else: last_id=match["id"]; streak=1
            else: streak=0; last_id=None
            msg=f"LOCKED - verified {streak}/5" if match else "LOCKED - unknown / no single face"
            cv2.putText(frame,msg,(12,28),cv2.FONT_HERSHEY_SIMPLEX,.65,(0,180,255),2); cv2.imshow("JARVIS Face Unlock",frame)
            if streak>=5:
                LAST_AUTH.update(name=match["name"],role=match["role"]); print(f"Authenticated: {match['name']} ({match['role']})"); return True
            if cv2.waitKey(1)&0xFF==ord('q'): return False
    finally: cap.release(); cv2.destroyAllWindows()
    LAST_AUTH.update(name=None,role=None); print("Authentication timed out; locked."); return False


def list_users():
    for p in _load_profiles(): print(f"{p['id']}: {p['name']} [{p['role']}]")


def remove_user(name):
    profiles=_load_profiles()
    if not profiles: raise RuntimeError("No enrolled profiles.")
    if not authenticate(role_required="admin"): raise RuntimeError("Owner authentication required; removal cancelled.")
    target=next((p for p in profiles if p["name"].casefold()==name.casefold()),None)
    if not target: raise ValueError("User not found.")
    if target["role"]=="admin": raise ValueError("The owner/admin profile cannot be removed through this command.")
    cv2,np,profiles,faces,labels=_load_samples(); keep=labels!=int(target["id"])
    np.savez_compressed(DATA_FILE,faces=faces[keep],labels=labels[keep])
    USERS_FILE.write_text(json.dumps([p for p in profiles if p["id"]!=target["id"]],indent=2),encoding="utf-8")
    print(f"Removed profile {name}.")


def main():
    parser=argparse.ArgumentParser(description="JARVIS local multi-user face enrollment/authentication")
    parser.add_argument("--enroll-face",nargs="?",const="Owner",help="enroll Owner first, or add a named user")
    parser.add_argument("--remove-face",help="remove a user profile (owner auth required)")
    parser.add_argument("--list-faces",action="store_true")
    args=parser.parse_args()
    if args.enroll_face is not None: enroll(args.enroll_face)
    elif args.remove_face: remove_user(args.remove_face)
    elif args.list_faces: list_users()
    else: print("Authentication result:",authenticate())
if __name__=="__main__": main()
