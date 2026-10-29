"""Retain complete-grid admission tests and explicit original ERROR reporting."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import unittest
import current_auction_shutdown_recovery_v1 as recovery


def load(name,file):
    s=importlib.util.spec_from_file_location(name,Path(__file__).with_name(file));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

original=load('original_comparison_tests','test_current_auction_comparison_v1.py')
cli=load('recovered_comparison','compare-current-auction-confirmation-recovered-v1.py')
original.cli=cli
CompletionAdmissionTests=original.CompletionAdmissionTests


class RecoveredIndexTests(unittest.TestCase):
    def fixture(self):
        source,report=CompletionAdmissionTests().fixture()
        job=report['jobs'][0];job['stage']='ERROR'
        job['review']['recovery']={'rule':recovery.RULE,'original_hf_stage':'ERROR',
            'all_original_games_retained':True,'new_games':0,'raw_records_changed':False,
            'original_errors':[{'episode':7,'error':'synthetic shutdown diagnostic'}]}
        return source,report

    def test_complete_index_preserves_original_error(self):
        source,report=self.fixture();before=deepcopy(report);jobs=cli.completion_index(source,report)
        self.assertEqual(jobs['job0']['stage'],'ERROR');self.assertEqual(report,before)

    def test_incomplete_or_reexecuted_recovery_rejected(self):
        for key,value in [('all_original_games_retained',False),('new_games',1),('raw_records_changed',True),('rule','unknown')]:
            source,report=self.fixture();report['jobs'][0]['review']['recovery'][key]=value
            with self.assertRaises(ValueError):cli.completion_index(source,report)

    def test_error_recovery_cannot_bypass_full_game_count(self):
        source,report=self.fixture();report['jobs'][0]['review']['games']-=1
        with self.assertRaises(ValueError):cli.completion_index(source,report)


if __name__=='__main__':unittest.main()
