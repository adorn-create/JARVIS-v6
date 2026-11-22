import sys
import threading
import types
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from face_detection import FaceDetectionMonitor


class FakeCapture:
    def __init__(self, opened=True):
        self.opened = opened
        self.released = False

    def isOpened(self):
        return self.opened

    def release(self):
        self.released = True

    def set(self, _property, _value):
        return True

    def read(self):
        return True, object()


class FakeDetector:
    def empty(self):
        return False

    def detectMultiScale(self, _frame, **_kwargs):
        return [object(), object()]


def fake_cv2(capture_factory):
    module = types.ModuleType("cv2")
    module.data = types.SimpleNamespace(haarcascades="")
    module.CascadeClassifier = lambda _path: FakeDetector()
    module.VideoCapture = capture_factory
    module.CAP_DSHOW = 700
    module.CAP_PROP_FRAME_WIDTH = 3
    module.CAP_PROP_FRAME_HEIGHT = 4
    module.COLOR_BGR2GRAY = 6
    module.cvtColor = lambda frame, _mode: frame
    return module


class FaceDetectionMonitorTests(unittest.TestCase):
    def test_detects_counts_and_releases_camera_when_stopped(self):
        capture = FakeCapture()
        counts = []
        statuses = []
        errors = []
        monitor_ref = {}
        first_count = threading.Event()

        def on_count(count):
            counts.append(count)
            if len(counts) == 1:
                first_count.set()
                monitor_ref["monitor"].stop()

        monitor = FaceDetectionMonitor(on_count, statuses.append, errors.append)
        monitor_ref["monitor"] = monitor
        cv2 = fake_cv2(lambda *_args: capture)

        with patch.dict(sys.modules, {"cv2": cv2}):
            monitor.start()
            self.assertTrue(first_count.wait(timeout=2))
            self.assertTrue(monitor.stop(wait=True, timeout=2))

        self.assertEqual(counts, [2, 0])
        self.assertEqual(errors, [])
        self.assertEqual(statuses, [
            "CAMERA ACTIVE • LOCAL FACE DETECTION ONLY",
            "CAMERA OFF",
        ])
        self.assertTrue(capture.released)

    def test_reports_camera_unavailable_and_releases_capture(self):
        captures = [FakeCapture(opened=False), FakeCapture(opened=False)]
        errors = []
        completed = threading.Event()

        def on_error(error):
            errors.append(error)
            completed.set()

        monitor = FaceDetectionMonitor(lambda _count: None, lambda _status: None, on_error)
        cv2 = fake_cv2(lambda *_args: captures.pop(0))

        with patch.dict(sys.modules, {"cv2": cv2}):
            monitor.start()
            self.assertTrue(completed.wait(timeout=2))
            self.assertTrue(monitor.stop(wait=True, timeout=2))

        self.assertEqual(len(errors), 1)
        self.assertIn("No camera is available", errors[0])
