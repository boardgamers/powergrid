"""Check benchmark coverage, privacy boundaries and exact semantic comparison."""
from copy import deepcopy
import unittest
import current_auction_cpu_v1 as b


def fixtures():
    cases=[]
    def add(name,group,n,v,sealed,stage):
        state={'players':[{'id':i,'bid':0} for i in range(n)],'options':{'variant':v,'fastBid':sealed,'showMoney':True},
               'seed':'secret','powerPlantsDeck':[],'hiddenLog':[]}
        cases.append({'name':name,'group':group,'players':n,'variant':v,'sealed':sealed,'stage':stage,
                      'request':{'player':0,'state':state},'player_order':list(range(n)),
                      'legal':[{'name':'Pass','data':True}]})
    for n in range(2,7):
        for v in ('original','recharged'):
            for s in (False,True):
                for stage in ('choose','bid','resources','building','bureaucracy'):
                    add(f'cpu-{n}p-{v}-{s}-{stage}','canonical',n,v,s,stage)
            for kind in ('pending-actor','wrapper-auto-pass'):
                add(f'{n}p-{v}-{kind}','wrapper',n,v,True,'bid')
    for i in range(40):add(f'discount-{i}','discount',2,'recharged',bool(i%2),'choose')
    return cases,{arm:{c['name']:'a'*64 for c in cases} for arm in b.ARMS}


class CurrentCpuTests(unittest.TestCase):
    def test_complete_case_grid_and_two_reference_policies(self):
        cases,reference=fixtures();b.validate_cases(cases,reference)

    def test_missing_duplicate_or_misclassified_cases_rejected(self):
        cases,reference=fixtures()
        variants=[cases[:-1],cases[:-1]+[cases[0]]]
        wrong=deepcopy(cases);wrong[0]['group']='discount';variants.append(wrong)
        wrong=deepcopy(cases);next(c for c in wrong if c['group']=='wrapper')['name']='2p-original-unknown';variants.append(wrong)
        for rows in variants:
            with self.assertRaises(AssertionError):b.validate_cases(rows,reference)

    def test_missing_wrong_arm_or_bad_reference_hash_rejected(self):
        cases,reference=fixtures()
        variants=[{'filter':reference['filter']},dict(reference,conservative_dual=reference['filter'])]
        wrong=deepcopy(reference);wrong['filter'].pop(cases[0]['name']);variants.append(wrong)
        wrong=deepcopy(reference);wrong['filter'][cases[0]['name']]='z'*64;variants.append(wrong)
        for refs in variants:
            with self.assertRaises(AssertionError):b.validate_cases(cases,refs)

    def test_hidden_inputs_or_hidden_money_rejected(self):
        cases,reference=fixtures()
        for key,value in [('seed','actual-seed'),('powerPlantsDeck',[3]),('hiddenLog',['private']),('powerPlantDeckAfterStep3',[]),('automation',{})]:
            wrong=deepcopy(cases);wrong[0]['request']['state'][key]=value
            with self.subTest(key=key),self.assertRaises(AssertionError):b.validate_cases(wrong,reference)
        wrong=deepcopy(cases);next(c for c in wrong if c['sealed'])['request']['state']['players'][1]['bid']=12
        with self.assertRaises(AssertionError):b.validate_cases(wrong,reference)
        wrong=deepcopy(cases);wrong[0]['request']['state']['options']['showMoney']=False
        with self.assertRaises(AssertionError):b.validate_cases(wrong,reference)

    def test_wrong_actor_order_or_empty_menu_rejected(self):
        cases,reference=fixtures()
        for order in ([1,0],[0,0],[0]):
            wrong=deepcopy(cases);wrong[0]['player_order']=order
            with self.assertRaises(AssertionError):b.validate_cases(wrong,reference)
        wrong=deepcopy(cases);wrong[0]['legal']=[]
        with self.assertRaises(AssertionError):b.validate_cases(wrong,reference)

    def test_semantic_hash_ignores_only_elapsed_time(self):
        original={'requestId':'one','modelSha256':'a'*64,'elapsedMs':1,
                  'move':{'name':'Bid','data':10},'search':{'elapsedMs':2,'worlds':[{'credit':'1/2'},{'credit':'0'}]}}
        changed=deepcopy(original);changed['elapsedMs']=999;changed['search']['elapsedMs']=300
        self.assertEqual(b.response_hash(original),b.response_hash(changed))
        variants=[]
        for key,value in [('requestId','two'),('modelSha256','b'*64)]:
            x=deepcopy(original);x[key]=value;variants.append(x)
        x=deepcopy(original);x['move']['data']=11;variants.append(x)
        x=deepcopy(original);x['search']['worlds'].reverse();variants.append(x)
        x=deepcopy(original);x['search']['worlds'][0]['credit']='1';variants.append(x)
        for x in variants:self.assertNotEqual(b.response_hash(original),b.response_hash(x))


if __name__=='__main__':unittest.main()
