from __future__ import annotations

from pathlib import Path
import sys
import unittest

import numpy as np


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from export_reconstruction import apply_handedness, mano_model_path  # noqa: E402


class HandednessConventionTest(unittest.TestCase):
    def test_both_sides_use_the_producers_right_hand_mano_model(self) -> None:
        self.assertEqual(mano_model_path(Path("models")), Path("models/MANO_RIGHT.pkl"))

    def test_left_hand_mirrors_only_x_after_decoding(self) -> None:
        vertices = np.array([[[1.0, 2.0, 3.0], [-4.0, 5.0, -6.0]]], dtype=np.float32)

        actual = apply_handedness(vertices.copy(), "left")

        np.testing.assert_array_equal(
            actual,
            np.array([[[-1.0, 2.0, 3.0], [4.0, 5.0, -6.0]]], dtype=np.float32),
        )

    def test_right_hand_is_unchanged(self) -> None:
        vertices = np.array([[[1.0, 2.0, 3.0]]], dtype=np.float32)
        np.testing.assert_array_equal(apply_handedness(vertices.copy(), "right"), vertices)

    def test_unknown_side_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "unsupported hand side"):
            apply_handedness(np.zeros((1, 1, 3), dtype=np.float32), "unknown")


if __name__ == "__main__":
    unittest.main()
