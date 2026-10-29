"""Reconstruction boundaries; synthetic records are not playing-strength data."""
from copy import deepcopy
import unittest
import current_auction_shutdown_recovery_v1 as r


def fixture():
    expected={'players':2,'start':0,'deals':1,'games':8}
    games=[{'episode':i,'terminal':{'truncated':False},'rollout_caps':0,'marker':i} for i in range(8)]
    report={'config':{'artifact':'/workspace/source/artifact'},'passed':False,'all_complete':False,
        'validation_error':'ValueError: Incomplete execution; preserve original receipts',
        'expected_games':8,'completed_games':7,'results':deepcopy(games[:7]),
        'game_caps':0,'rollout_caps':0,'qualification_eligible':False,'reserved_final_seeds_used':False}
    descriptor='policies/filter.json'
    report['errors']=[{'episode':7,'error':r.timeout_error(report['config'],descriptor)}]
    return report,games,expected,descriptor


class RecoveryTests(unittest.TestCase):
    def test_complete_original_records_retained_without_mutating_inputs(self):
        args=fixture();before=deepcopy(args);derived=r.reconstruct(*args)
        self.assertEqual(args,before);self.assertEqual(derived['results'],args[1])
        self.assertEqual(derived['completed_games'],8)
        self.assertEqual(derived['terminal_recovery']['original_hf_stage'],'ERROR')
        self.assertEqual(derived['terminal_recovery']['original_errors'],args[0]['errors'])

    def test_missing_duplicate_or_extra_terminals_rejected(self):
        report,games,expected,descriptor=fixture()
        for broken in (games[:-1],games[:-1]+[games[0]],games+[dict(games[0],episode=8)]):
            with self.assertRaises(ValueError):r.reconstruct(report,broken,expected,descriptor)

    def test_changed_or_duplicate_original_summary_record_rejected(self):
        for mutate in (lambda x:x['results'][0].update(marker=999),lambda x:x['results'].__setitem__(0,x['results'][1]),lambda x:x.update(completed_games=6)):
            report,games,expected,descriptor=fixture();mutate(report)
            with self.assertRaises(ValueError):r.reconstruct(report,games,expected,descriptor)

    def test_wrong_or_duplicate_error_episode_rejected(self):
        for errors in ([{'episode':0}],[],[{'episode':7},{'episode':7}]):
            report,games,expected,descriptor=fixture()
            report['errors']=[{**e,'error':report['errors'][0]['error']} for e in errors]
            with self.assertRaises(ValueError):r.reconstruct(report,games,expected,descriptor)

    def test_other_timeout_command_duration_or_failure_rejected(self):
        for mutate in (lambda x:'ValueError: illegal move',lambda x:x.replace('30 seconds','60 seconds'),
                       lambda x:x.replace('public_policy_runtime_v1.py','another.py'),lambda x:x.replace('policies/filter.json','policies/other.json')):
            report,games,expected,descriptor=fixture();report['errors'][0]['error']=mutate(report['errors'][0]['error'])
            with self.assertRaises(ValueError):r.reconstruct(report,games,expected,descriptor)

    def test_summary_or_omitted_game_caps_rejected(self):
        for where in ('game_caps','rollout_caps','omitted_game','omitted_rollout'):
            report,games,expected,descriptor=fixture()
            if where=='omitted_game':games[7]['terminal']['truncated']=True
            elif where=='omitted_rollout':games[7]['rollout_caps']=1
            else:report[where]=1
            with self.assertRaises(ValueError):r.reconstruct(report,games,expected,descriptor)

    def test_wrong_purpose_or_nonfailed_original_rejected(self):
        for key,value in [('passed',True),('all_complete',True),('reserved_final_seeds_used',True),('qualification_eligible',True),('validation_error','other')]:
            report,games,expected,descriptor=fixture();report[key]=value
            with self.assertRaises(ValueError):r.reconstruct(report,games,expected,descriptor)

    def test_wrong_expected_pairing_rejected(self):
        report,games,expected,descriptor=fixture()
        for changed in (dict(expected,players=3),dict(expected,start=1),dict(expected,games=7)):
            with self.assertRaises(ValueError):r.reconstruct(report,games,changed,descriptor)

    def test_original_error_requires_explicit_complete_data_metadata(self):
        job={'stage':'ERROR','verified':True,'review':{}}
        self.assertFalse(r.complete_data(job))
        metadata=r.reconstruct(*fixture())['terminal_recovery'];job['review']['recovery']=metadata
        self.assertTrue(r.complete_data(job));self.assertEqual(job['stage'],'ERROR')
        for key,value in [('new_games',1),('raw_records_changed',True),('all_original_games_retained',False),('rule','unknown'),('original_errors',[])]:
            broken=deepcopy(job);broken['review']['recovery'][key]=value;self.assertFalse(r.complete_data(broken))
        job['stage']='TIMEOUT';self.assertFalse(r.complete_data(job))


if __name__=='__main__':unittest.main()
