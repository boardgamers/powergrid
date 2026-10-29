"""Keep the complete-grid gate and reject missing or mismatched worker audits."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch

import current_auction_parallel_audit_v1 as worker


def load(name,file):
    spec=importlib.util.spec_from_file_location(name,Path(__file__).with_name(file))
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


original=load('recovered_tests','test_current_auction_recovered_comparison_v1.py')
cli=load('parallel_comparison','compare-current-auction-confirmation-parallel-v1.py')
original.cli=cli;original.original.cli=cli
CompletionAdmissionTests=original.CompletionAdmissionTests
RecoveredIndexTests=original.RecoveredIndexTests


class ParallelReviewTests(unittest.TestCase):
    def fixture(self):
        source,report=RecoveredIndexTests().fixture();jobs=cli.completion_index(source,report)
        results=[{'name':n,'kind':'confirmation','job_id':j['job_id'],'original_hf_stage':j['stage'],
            'games':j['review']['games'],'counts':deepcopy(j['review']['audit']['counts']),
            'review_sha256':cli.object_hash(j['review'])} for n,j in jobs.items()]
        return jobs,results

    def test_exact_reviews_preserve_error_and_ignore_completion_order(self):
        jobs,results=self.fixture();before=deepcopy(jobs)
        mapped=cli.match_parallel_reviews(jobs,list(reversed(results)))
        self.assertEqual(set(mapped),set(jobs));self.assertEqual(mapped['job0']['original_hf_stage'],'ERROR')
        self.assertEqual(jobs,before)

    def test_missing_duplicate_or_extra_review_is_rejected(self):
        jobs,results=self.fixture()
        for values in (results[:1],[results[0],results[0]],results+results[:1],
                       [results[0],{**results[1],'name':'unknown'}]):
            with self.assertRaises(ValueError):cli.match_parallel_reviews(jobs,values)

    def test_changed_identity_status_counts_or_review_hash_rejected(self):
        for field,value in (('kind','runtime'),('job_id','f'*24),('original_hf_stage','COMPLETED'),
                            ('games',1),('counts',{'rollout_caps':1}),('review_sha256','e'*64)):
            jobs,results=self.fixture();results[0][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):cli.match_parallel_reviews(jobs,results)

    def test_executor_is_bounded_and_preserves_each_original_case(self):
        cases=[{'name':'a'},{'name':'b'}];pool=Mock();pool.map.return_value=iter(['a','b'])
        with patch.object(cli,'ProcessPoolExecutor',return_value=pool) as executor:
            self.assertEqual(cli.parallel_audit(cases),['a','b'])
        self.assertEqual(executor.call_args.kwargs['max_workers'],4)
        pool.map.assert_called_once_with(worker.audit_original,cases,chunksize=1)
        pool.shutdown.assert_called_once_with(wait=True)

    def test_worker_failure_cancels_pending_audits_and_propagates(self):
        pool=Mock();pool.map.side_effect=ValueError('changed raw bytes')
        with patch.object(cli,'ProcessPoolExecutor',return_value=pool):
            with self.assertRaisesRegex(ValueError,'changed raw bytes'):cli.parallel_audit([{}])
        pool.shutdown.assert_called_once_with(wait=True,cancel_futures=True)

    def test_changed_source_or_receipt_rejected_before_raw_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);folder=root/'case';folder.mkdir();source=root/'source.json'
            source.write_text('{"rows":[{"name":"case"}]}');receipt=folder/'verified.json';receipt.write_text('{}')
            manager=SimpleNamespace(OUT=root,SOURCE=source,verified_path=lambda f:receipt,verify_result=Mock())
            case={'kind':'confirmation','name':'case','source_sha256':'0'*64,'verified_sha256':'1'*64}
            with patch.object(worker,'manager',return_value=manager):
                with self.assertRaises(AssertionError):worker.audit_original(case)
                case['source_sha256']=worker.digest(source)
                with self.assertRaises(AssertionError):worker.audit_original(case)
            manager.verify_result.assert_not_called()


if __name__=='__main__':unittest.main()
