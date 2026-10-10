import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('collector',Path(__file__).with_name('collect-discard-correction.py'))
collector=importlib.util.module_from_spec(spec);spec.loader.exec_module(collector)


class MetricsChecks(unittest.TestCase):
    def test_float_reduction_ulp_is_allowed_but_counts_and_real_changes_fail(self):
        original={'roots':452,'changed':86,'weighted_simulated_regret':.038949012756347656}
        collector.compare_metrics({**original,'weighted_simulated_regret':.038949016481637955},original)
        for wrong in [{**original,'changed':85},{**original,'roots':451},
                      {**original,'weighted_simulated_regret':.039},{**original,'weighted_simulated_regret':float('nan')}]:
            with self.assertRaises(AssertionError):collector.compare_metrics(wrong,original)


if __name__=='__main__':unittest.main()
