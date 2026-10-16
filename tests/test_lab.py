import unittest
import numpy as np
from lab import generate, validate, fit_model, model_scores, threshold_for_budget, evaluate


class LabTests(unittest.TestCase):
    def test_reproducible_independent_streams(self):
        a, y = generate(200, 42)
        b, z = generate(200, 42)
        np.testing.assert_array_equal(a, b)
        np.testing.assert_array_equal(y, z)
        self.assertFalse(np.array_equal(a, generate(200, 43)[0]))

    def test_input_contract(self):
        for value in ([], [[1, 2]], [[1, 2, 3, float('nan')]],
                      [[1, -2, 3, 4]], [[1, 2, 3.5, 4]], [[1, 2, 3, float('inf')]]):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate(value)

    def test_budget_validation(self):
        for budget in (0, 1, -.1, float('nan')):
            with self.assertRaises(ValueError):
                threshold_for_budget(np.arange(100), budget)

    def test_calibrated_budget_and_ties(self):
        scores = np.arange(1000)
        t = threshold_for_budget(scores, .05)
        self.assertEqual(np.sum(scores >= t), 50)
        # Ties can exceed the requested budget; document rather than hide this.
        self.assertEqual(np.sum(np.ones(100) >= threshold_for_budget(np.ones(100), .05)), 100)

    def test_metrics_known_confusion_matrix(self):
        result = evaluate(np.array([0, 0, 1, 1]), np.array([.1, .8, .7, .2]), .5)
        for key in ('true_positives', 'true_negatives', 'false_positives', 'false_negatives'):
            self.assertEqual(result[key], 1)
        self.assertEqual(result['precision'], .5)
        self.assertEqual(result['recall'], .5)

    def test_no_alerts_is_defined(self):
        result = evaluate(np.array([0, 1]), np.array([.1, .2]), .9)
        self.assertEqual(result['precision'], 0)
        self.assertEqual(result['false_negatives'], 1)

    def test_model_scores_repeatable_and_extreme_event_ranks_high(self):
        x, _ = generate(500, 9)
        model = fit_model(x, 9)
        samples = np.array([[40, 20, 2, 600], [10000, 10000, 100, 0]])
        scores = model_scores(model, samples)
        self.assertGreater(scores[1], scores[0])
        np.testing.assert_allclose(scores, model_scores(fit_model(x, 9), samples))


if __name__ == '__main__':
    unittest.main()
