import unittest
import numpy as np
from evaluate_shift import shift_legitimate, drift_report
from lab import generate


class ShiftTests(unittest.TestCase):
    def test_shift_preserves_original_and_anomalies(self):
        x, y = generate(500, 23)
        original = x.copy()
        shifted = shift_legitimate(x, y)
        np.testing.assert_array_equal(x, original)
        np.testing.assert_array_equal(shifted[y == 1], x[y == 1])
        np.testing.assert_array_equal(shifted[y == 0, 0], x[y == 0, 0] * 3)

    def test_identical_data_has_no_drift(self):
        x, _ = generate(500, 23)
        self.assertTrue(all(v['ks_statistic'] == 0 for v in drift_report(x, x).values()))

    def test_large_distance_shift_detected(self):
        x, y = generate(500, 23)
        self.assertTrue(drift_report(x, shift_legitimate(x, y))['distance_km']['review_shift'])

