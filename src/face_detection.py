import logging
import threading

LOG = logging.getLogger("jarvis.face_detection")


class FaceDetectionMonitor:
    def __init__(self, on_count, on_status, on_error):
        self._on_count = on_count
        self._on_status = on_status
        self._on_error = on_error
        self._stop_event = threading.Event()
        self._thread = None

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._detect, daemon=True)
        self._thread.start()

    def stop(self, wait=False, timeout=5.0):
        self._stop_event.set()
        thread = self._thread
        if wait and thread and thread is not threading.current_thread():
            thread.join(timeout=max(0.0, float(timeout)))
        return not (thread and thread.is_alive())

    def _detect(self):
        capture = None
        try:
            import cv2

            cascade_path = (
                cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            )
            detector = cv2.CascadeClassifier(cascade_path)
            if detector.empty():
                raise RuntimeError("OpenCV's frontal-face detector could not be loaded.")

            capture = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            if not capture.isOpened():
                capture.release()
                capture = cv2.VideoCapture(0)
            if not capture.isOpened():
                raise RuntimeError(
                    "No camera is available. Check camera connection and Windows privacy settings."
                )
            capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self._on_status("CAMERA ACTIVE • LOCAL FACE DETECTION ONLY")

            last_count = None
            while not self._stop_event.is_set():
                ok, frame = capture.read()
                if not ok:
                    if self._stop_event.is_set():
                        break
                    raise RuntimeError("The camera stopped returning frames.")
                grayscale = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = detector.detectMultiScale(
                    grayscale,
                    scaleFactor=1.1,
                    minNeighbors=5,
                    minSize=(30, 30),
                )
                count = len(faces)
                if count != last_count:
                    self._on_count(count)
                    last_count = count
                self._stop_event.wait(0.05)
        except Exception as exc:
            if not self._stop_event.is_set():
                LOG.exception("local face detection failed")
                self._on_error(str(exc))
        finally:
            if capture is not None:
                capture.release()
            self._on_count(0)
            if self._stop_event.is_set():
                self._on_status("CAMERA OFF")
