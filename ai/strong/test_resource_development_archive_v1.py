"""Actual terminal accounting, whole-deal uncertainty and incomplete-run refusal."""
import copy
from fractions import Fraction
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from strategic_collection import ROOT,read,write

spec=importlib.util.spec_from_file_location('resource_archive',Path(__file__).with_name('collect-resource-replanning-development-v1.py'))
collector=importlib.util.module_from_spec(spec);spec.loader.exec_module(collector)


class ResourceArchiveTest(unittest.TestCase):
    def test_all_terminal_credits_in_actual_six_player_batch(self):
        path=collector.manager.COLLECTED/'resource-replanning-development-v1-filter-6p-economic-0-4/artifacts/evaluation/evaluation.json'
        rows=read(path)['results'];self.assertEqual(len(rows),96)
        for row in rows:collector.terminal_credit(row['terminal'])
        bad=copy.deepcopy(rows[0]['terminal']);bad['win']=1-bad['win']
        with self.assertRaises(AssertionError):collector.terminal_credit(bad)

    def test_synthetic_whole_deal_bootstrap_and_equal_count_weights(self):
        spec=importlib.util.spec_from_file_location('resource_test_fixture',Path(__file__).with_name('test_resource_development_collection_v1.py'))
        fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)
        data=fixture.reports();protocol=fixture.protocol
        # One of the four 2p deals changes all its seats/rules from loss to win.
        for row in data['resource-filter']['search_geo/2p']:
            if row['gameSeed'].endswith('-3'):row['win']=1.
        expected=collector.comparison.equal_count_summary(data,'search_geo',protocol)
        differences={n:{protocol['seed_template'].format(players=n)+'-'+str(d):Fraction(int(n==2 and d==3))
                        for d in range(4)} for n in range(2,7)}
        result=collector.audit_equal_count(differences,expected,protocol)
        self.assertEqual(result['win_share_difference'],.05)
        self.assertEqual(result['paired_deal_bootstrap_95_interval'],[0.,.15])
        expected['paired_deal_bootstrap_95_interval'][1]=.5
        with self.assertRaises(AssertionError):collector.audit_equal_count(differences,expected,protocol)

    def test_partial_experiment_never_reads_comparison_or_uploads(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);write(root/'state.json',{'stage':'waiting_for_jobs'})
            with patch.object(collector,'COORDINATOR',root),patch.object(collector,'upload_evidence') as upload, \
                 patch.object(collector.comparison,'compare') as compare:
                for archive in (False,True):
                    with self.assertRaisesRegex(AssertionError,'all 54 original'):
                        collector.main(archive)
                upload.assert_not_called();compare.assert_not_called()
                self.assertEqual([p.name for p in root.iterdir()],['state.json'])


if __name__=='__main__':unittest.main()
