"""Serving coverage and independent receipt checks; never calls a real policy."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock,patch

import current_auction_full_serving_v1 as b


def fixture(index=0,n=2):
    return {'index':index,'players':n,'stage':'Resources','variant':'original','sealed':False,
        'request':{'requestId':str(index),'revision':index,'player':0,'state':{
            'players':[{'lastMove':None,'bid':0,'money':50} for _ in range(n)],'currentPlayers':[0],
            'map':{'name':'Germany'},'options':{'showMoney':True,'variant':'original','fastBid':False},
            'phase':'Resources','seed':'secret','powerPlantsDeck':[],'hiddenLog':[]}},
        'legal':[{'name':'Pass','data':True}],'player_order':list(range(n)),
        'original_line_sha256':'a'*64}


def all_cases():
    result=[]
    for n,count in b.COUNTS.items():
        for _ in range(count):result.append(fixture(len(result),int(n)))
    return result


class FullServingTests(unittest.TestCase):
    def test_full_original_count_distribution_required(self):
        values=all_cases()
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);f=p/'cases.jsonl'
            f.write_text(''.join(b.wire(c)+'\n' for c in values))
            self.assertEqual(len(list(b.cases(p))),2553)
            for changed in (values[:-1],values+[fixture(2553)],values[:1]+values[:1]+values[2:]):
                f.write_text(''.join(b.wire(c)+'\n' for c in changed))
                with self.assertRaises(AssertionError):list(b.cases(p))

    def test_public_projection_and_actor_are_required(self):
        mutations=[lambda c:c['request']['state'].update(seed='private'),
            lambda c:c['request']['state'].update(powerPlantsDeck=[{'number':50}]),
            lambda c:c['request']['state'].update(hiddenLog=[{'secret':True}]),
            lambda c:c['request']['state'].update(automation={}),
            lambda c:c['request']['state'].update(currentPlayers=[]),
            lambda c:c['request']['state']['options'].update(showMoney=False),
            lambda c:c.update(player_order=[1,0]),lambda c:c.update(sealed=True)]
        for mutate in mutations:
            c=fixture();mutate(c)
            with self.subTest(case=c),self.assertRaises(AssertionError):b.validate_case(c,0)
        c=fixture();c['sealed']=True;c['request']['state']['options']['fastBid']=True
        c['request']['state']['players'][1]['bid']=42
        with self.assertRaises(AssertionError):b.validate_case(c,0)

    def test_wrong_machine_rejected_before_policy_creation(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)
            with patch.object(b,'checked_package',return_value={}),patch.object(Path,'read_text',return_value='model name : other CPU\n'),patch.object(b,'dependencies') as dep:
                with self.assertRaises(AssertionError):b.run(p,p/'out')
                dep.assert_not_called();self.assertFalse((p/'out').exists())

    def test_failed_original_is_not_audited_as_complete(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);(p/'status.json').write_text('{"stage":"failed"}')
            with patch.object(b,'checked_package',return_value={}),patch.object(b,'dependencies') as dep:
                with self.assertRaises(AssertionError):b.audit(p,p)
                dep.assert_not_called()

    def fake_run(self,p):
        values=all_cases();manifest={'identities':{a:{'arm':a} for a in b.ARMS}}
        (p/'benchmark-manifest.json').write_text(b.wire(manifest));rows=[]
        for a in b.ARMS:
            (p/(a+'.stderr.log')).touch()
            for c in values:
                rows.append({'arm':a,'index':c['index'],'players':c['players'],'stage':c['stage'],
                    'request_sha256':b.object_hash(c['request']),'response':{'requestId':c['request']['requestId']},
                    'round_trip_ms':1,'cold_process_plus_request_ms':2 if c['index']==0 else None})
        state={'stage':'completed','passed':True,'processor':'AMD 8840U','completed_requests':5106,
            'manifest_sha256':b.digest(p/'benchmark-manifest.json'),
            'counts':{a:{'decisions':2553} for a in b.ARMS},'scope':'synthetic test only'}
        def save():
            (p/'receipts.jsonl').write_text(''.join(b.wire(r)+'\n' for r in rows))
            state['output_hashes']={n:b.digest(p/n) for n in ('receipts.jsonl',*(a+'.stderr.log' for a in b.ARMS))}
            (p/'status.json').write_text(b.wire(state))
        def verify(c,a,r,identity):
            assert r['requestId']==c['request']['requestId'] and identity=={'arm':a}
            return {'decisions':1}
        identity=lambda root,desc:{'arm':Path(desc).stem}
        return values,manifest,rows,save,identity,verify

    def test_complete_stream_preserves_all_5106_bindings(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);values,m,rows,save,identity,verify=self.fake_run(p);save()
            with patch.object(b,'checked_package',return_value=m),patch.object(b,'cases',side_effect=lambda p:iter(values)),patch.object(b,'dependencies',return_value=(Mock(),identity,verify)):
                result=b.audit(p,p)
            self.assertTrue(result['complete']);self.assertEqual(result['requests'],5106)
            self.assertEqual(set(result['warm_timings_by_count_rule_phase']),set(b.ARMS))
            self.assertFalse(result['qualified'])

    def test_duplicate_stale_wrong_arm_or_missing_receipts_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);values,m,rows,save,identity,verify=self.fake_run(p);original=deepcopy(rows)
            mutations=[lambda:rows[1].update(index=0),lambda:rows[0].update(arm=b.ARMS[1]),
                lambda:rows[0].update(request_sha256='0'*64),lambda:rows[0]['response'].update(requestId='stale'),
                lambda:rows.pop()]
            for mutate in mutations:
                rows[:]=deepcopy(original);mutate();save()
                with patch.object(b,'checked_package',return_value=m),patch.object(b,'cases',side_effect=lambda p:iter(values)),patch.object(b,'dependencies',return_value=(Mock(),identity,verify)):
                    with self.assertRaises((AssertionError,StopIteration)):b.audit(p,p)


if __name__=='__main__':unittest.main()
