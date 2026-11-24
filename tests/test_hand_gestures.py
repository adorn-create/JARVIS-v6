import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hand_gestures import classify_hand


def landmarks(index=True, middle=True, ring=True, pinky=True, thumb=True):
    points = [SimpleNamespace(x=0.5, y=0.5) for _ in range(21)]
    for tip, joint, extended in ((8, 6, index), (12, 10, middle), (16, 14, ring), (20, 18, pinky)):
        points[tip].y = 0.2 if extended else 0.8
        points[joint].y = 0.5
    points[4].x = 0.8 if thumb else 0.51
    points[2].x = 0.5
    return points


class GestureClassifierTests(unittest.TestCase):
    def test_open_palm(self):
        self.assertEqual(classify_hand(landmarks()), "OPEN PALM")

    def test_peace(self):
        self.assertEqual(classify_hand(landmarks(True, True, False, False, True)), "PEACE")

    def test_point(self):
        self.assertEqual(classify_hand(landmarks(True, False, False, False, True)), "POINT")

    def test_fist(self):
        self.assertEqual(classify_hand(landmarks(False, False, False, False, False)), "FIST")

    def test_invalid_landmarks(self):
        self.assertEqual(classify_hand([]), "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
