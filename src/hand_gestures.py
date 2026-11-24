import logging
import threading

LOG = logging.getLogger("jarvis.gestures")


def classify_hand(landmarks):
    """Classify a normalized MediaPipe hand landmark list."""
    if landmarks is None or len(landmarks) < 21:
        return "UNKNOWN"
    # Finger tips compared with the joint closer to the palm. For non-thumb
    # fingers, y decreases toward the top of the image.
    index = landmarks[8].y < landmarks[6].y
    middle = landmarks[12].y < landmarks[10].y
    ring = landmarks[16].y < landmarks[14].y
    pinky = landmarks[20].y < landmarks[18].y
    # Thumb extension is approximated by tip-to-index-base distance. This is
    # intentionally orientation tolerant but not a sign-language interpreter.
    thumb = (
        abs(landmarks[4].x - landmarks[2].x)
        + abs(landmarks[4].y - landmarks[2].y)
        > 0.08
    )
    if index and middle and ring and pinky:
        return "OPEN PALM"
    if not index and not middle and not ring and not pinky:
        return "THUMBS UP" if thumb else "FIST"
    if index and middle and not ring and not pinky:
        return "PEACE"
    if index and not middle and not ring and not pinky:
        return "POINT"
    return "UNKNOWN"


class HandGestureMonitor:
    """Local camera hand-landmark recognition; emits labels, not commands."""

    def __init__(self, on_gesture, on_status, on_error):
        self._on_gesture = on_gesture
        self._on_status = on_status
        self._on_error = on_error
        self._stop_event = threading.Event()
        self._thread = None

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self, wait=False, timeout=5.0):
        self._stop_event.set()
        thread = self._thread
        if wait and thread and thread is not threading.current_thread():
            thread.join(max(0.0, float(timeout)))
        return not (thread and thread.is_alive())

    def _run(self):
        capture = None
        hands = None
        try:
            import cv2
            import mediapipe as mp

            hands_api = mp.solutions.hands
            hands = hands_api.Hands(
                static_image_mode=False,
                max_num_hands=2,
                model_complexity=0,
                min_detection_confidence=0.6,
                min_tracking_confidence=0.5,
            )
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
            self._on_status("HAND GESTURES ACTIVE • LOCAL CAMERA")
            previous = None
            stable_count = 0
            last_emit = None
            while not self._stop_event.is_set():
                ok, frame = capture.read()
                if not ok:
                    if self._stop_event.is_set():
                        break
                    raise RuntimeError("The camera stopped returning frames.")
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                result = hands.process(rgb)
                labels = []
                for hand in (result.multi_hand_landmarks or []):
                    labels.append(classify_hand(hand.landmark))
                label = " + ".join(labels) if labels else "NO HAND"
                if label == previous:
                    stable_count += 1
                else:
                    previous = label
                    stable_count = 1
                # Emit after 5 consecutive frames, and only when the label changes.
                if stable_count >= 5 and label != last_emit:
                    self._on_gesture(label)
                    last_emit = label
                self._stop_event.wait(0.03)
        except Exception as exc:
            if not self._stop_event.is_set():
                LOG.exception("hand gesture recognition failed")
                self._on_error(str(exc))
        finally:
            if capture is not None:
                capture.release()
            if hands is not None:
                try:
                    hands.close()
                except Exception:
                    LOG.exception("could not close MediaPipe hands")
            self._on_gesture("OFF")
            if self._stop_event.is_set():
                self._on_status("HAND GESTURES OFF")
