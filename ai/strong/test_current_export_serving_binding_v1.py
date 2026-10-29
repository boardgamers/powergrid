"""Bind the native model proposal while permitting audited search overrides."""
from copy import deepcopy
import unittest
from audit_current_engine_export_v1 import bind_proposal
import current_engine_export_parity_v1 as p


class ServingBindingTests(unittest.TestCase):
    def fixture(self):
        case={'index':0,'players':2,'player_order':[0,1],'request':{'requestId':'a','revision':1},
              'legal':[{'name':'Bid','data':10},{'name':'Pass','data':True}]}
        identity={'modelSha256':p.MODEL_SHA,'settings':{'samples':8},'backend':'opponent-auction-v1'}
        base={'index':0,'request_sha256':p.object_hash(case['request']),'model_sha256':p.MODEL_SHA,
              'selected_index':0,'selected_move':case['legal'][0]}
        served={'index':0,'players':2,'request_sha256':base['request_sha256'],
            'response':{**identity,'requestId':'a','revision':1,'playerOrder':[0,1],
                'decision':{'modelProposal':0},'move':case['legal'][1]}}
        return case,base,served,identity

    def test_legal_final_override_does_not_change_model_proposal(self):
        bind_proposal(*self.fixture())

    def test_changed_proposal_identity_or_request_is_rejected(self):
        mutations=[lambda s:s['response']['decision'].update(modelProposal=1),
            lambda s:s['response'].update(modelSha256='0'*64),lambda s:s['response'].update(revision=2),
            lambda s:s.update(index=1),lambda s:s.update(request_sha256='0'*64),
            lambda s:s['response'].update(playerOrder=[1,0]),lambda s:s['response'].update(settings={'samples':4})]
        for mutate in mutations:
            c,b,s,i=self.fixture();s=deepcopy(s);mutate(s)
            with self.assertRaises(AssertionError):bind_proposal(c,b,s,i)


if __name__=='__main__':unittest.main()
