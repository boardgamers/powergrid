"""No HF calls or games; enforce the finite finisher's stop boundaries."""
from copy import deepcopy
import unittest
from unittest.mock import Mock
import finish_current_auction_confirmation_v1 as runner


class FinisherTests(unittest.TestCase):
    def setUp(self):
        self.complete={'active':0,'batches':{name:{'submitted':n,'verified_jobs':n,'unsubmitted':0}
            for name,n in (('failed_recovery',10),('untouched',258))}}
        self.pending=deepcopy(self.complete); self.pending['batches']['untouched']['verified_jobs']-=1

    def test_compares_once_only_after_every_verified_job(self):
        cycle=Mock(side_effect=[self.pending,self.complete]); compare=Mock(return_value={'complete':True})
        publish=Mock(); sleep=Mock()
        runner.finish(cycle,compare,publish,lambda:False,sleep=sleep,max_cycles=3)
        self.assertEqual(cycle.call_count,2); compare.assert_called_once_with(); sleep.assert_called_once_with(60)
        self.assertEqual(publish.call_args.args[0]['stage'],'complete')
        for call in cycle.call_args_list:
            self.assertEqual(call.kwargs,{'execute':True,'launch_limit':64,'collect_limit':8})

    def test_error_stops_without_retry_or_comparison(self):
        cycle=Mock(side_effect=ValueError('ambiguous upload')); compare=Mock()
        with self.assertRaises(ValueError):
            runner.finish(cycle,compare,Mock(),lambda:False,sleep=Mock())
        cycle.assert_called_once(); compare.assert_not_called()

    def test_stop_and_time_limit_prevent_new_cycle(self):
        for stopped,clock in ((lambda:True,Mock(return_value=0)),(lambda:False,Mock(side_effect=[0,2]))):
            cycle=Mock();compare=Mock()
            runner.finish(cycle,compare,Mock(),stopped,clock=clock,max_seconds=1)
            cycle.assert_not_called();compare.assert_not_called()

    def test_stop_after_collection_prevents_comparison(self):
        compare=Mock();stopped=Mock(side_effect=[False,True])
        runner.finish(Mock(return_value=self.complete),compare,Mock(),stopped,sleep=Mock())
        compare.assert_not_called()

    def test_incomplete_queue_stops_at_bounded_cycle_count(self):
        cycle=Mock(return_value=self.pending);compare=Mock();publish=Mock()
        runner.finish(cycle,compare,publish,lambda:False,sleep=Mock(),max_cycles=2)
        self.assertEqual(cycle.call_count,2);compare.assert_not_called()
        self.assertEqual(publish.call_args.args[0]['stage'],'cycle_limit_reached')


if __name__=='__main__':unittest.main()
