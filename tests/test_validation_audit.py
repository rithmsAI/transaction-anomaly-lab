import unittest
from unittest.mock import patch
from pathlib import Path
import tempfile
import numpy as np
import lab
from validation_audit import paired_ap_interval
class ValidationAuditTests(unittest.TestCase):
    def test_rejects_bad_evaluation_inputs(self):
        for labels,scores,t in [([0,1],[.1],.5),([0,2],[.1,.2],.5),([0,1],[.1,np.nan],.5),([0,1],[.1,.2],np.inf),([0,0],[.1,.2],.5)]:
            with self.assertRaises(ValueError): lab.evaluate(labels,np.array(scores),t)
    def test_identical_rankings_have_zero_paired_difference(self):
        y=np.array([0,1,0,1]); scores=np.array([.1,.8,.2,.9])
        self.assertEqual(paired_ap_interval(y,scores,scores,repeats=20),[0.,0.])
    def test_test_label_changes_cannot_change_thresholds(self):
        original=lab.generate
        def altered(n,seed):
            x,y=original(n,seed)
            return x,1-y if seed==44 else y
        with tempfile.TemporaryDirectory() as tmp, patch.object(lab,'plot_results'):
            first=lab.run(Path(tmp)/'a')
            with patch.object(lab,'generate',side_effect=altered): second=lab.run(Path(tmp)/'b')
        for name in first['models']:
            self.assertEqual(first['models'][name]['threshold'],second['models'][name]['threshold'])
        self.assertNotEqual(first['test_prevalence'],second['test_prevalence'])
    def test_fit_receives_training_only(self):
        real_fit=lab.fit_model; seen=[]
        def spy(x,seed): seen.append(x.copy()); return real_fit(x,seed)
        with tempfile.TemporaryDirectory() as tmp, patch.object(lab,'plot_results'),patch.object(lab,'fit_model',side_effect=spy):
            lab.run(Path(tmp))
        self.assertEqual(len(seen),1); np.testing.assert_array_equal(seen[0],lab.generate(6000,42)[0])
if __name__=='__main__': unittest.main()
