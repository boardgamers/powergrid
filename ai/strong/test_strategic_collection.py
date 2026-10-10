"""Reject contaminated game/split contracts; synthetic cases are not evidence."""
import copy
import unittest
from strategic_collection import PROTOCOL, read, phase, seed_for, verify_games


class CollectionContracts(unittest.TestCase):
    def setUp(self):
        self.p = read(PROTOCOL)
        self.rows = []
        for episode in range(8):
            seat = episode//4; value = [0,0]; value[seat] = 1
            self.rows.append({'episode':episode,'seat':seat,'playerCount':2,
                'gameSeed':seed_for(self.p,2,'economic',True)+'-0',
                'variant':'recharged' if episode % 2 else 'original', 'sealed':episode % 4 < 2,
                'roles':['learner' if i == seat else 'economic' for i in range(2)],
                'win':1,'value':value,'truncated':False,'searchStats':{}})

    def test_complete_grid_and_disjoint_smoke_prefix(self):
        verify_games(self.rows,self.p,2,'economic',True)
        self.assertNotEqual(seed_for(self.p,2,'economic',True),seed_for(self.p,2,'economic',False))
        for deal in range(self.p['deals_per_shard']):
            splits = {'validation' if (episode//8) in self.p['validation_deal_indices'] else 'train'
                      for episode in range(deal*8,(deal+1)*8)}
            self.assertEqual(len(splits),1)

    def test_bad_games_cannot_be_used_as_training_coverage(self):
        for fault in ['missing','duplicate','seed','rules','roles','cap','wrong_win','search']:
            rows=copy.deepcopy(self.rows)
            if fault=='missing':rows.pop()
            elif fault=='duplicate':rows[-1]=rows[0]
            elif fault=='seed':rows[0]['gameSeed']='reserved-final-seed'
            elif fault=='rules':rows[0]['sealed']=False
            elif fault=='roles':rows[0]['roles']=['learner','snapshot0']
            elif fault=='cap':rows[0]['truncated']=True
            elif fault=='wrong_win':rows[0]['win']=0
            else:rows[0]['searchStats']={'learner':{'decisions':1,'evaluations':48,'truncated':0}}
            with self.subTest(fault=fault),self.assertRaises((AssertionError,ValueError)):
                verify_games(rows,self.p,2,'economic',True)

    def test_scope_excludes_automatic_fuel_and_discard_choices(self):
        self.assertEqual(phase([{'name':'ChoosePowerPlant'},{'name':'Pass'}]),'auction')
        self.assertEqual(phase([{'name':'Bid'},{'name':'Pass'}]),'auction')
        self.assertEqual(phase([{'name':'Build'},{'name':'Pass'}]),'building')
        for moves in [[{'name':'Build'}],[{'name':'DiscardPowerPlant'}]*2,[{'name':'BuyResource'},{'name':'Pass'}]]:
            self.assertIsNone(phase(moves))


if __name__=='__main__':unittest.main()
