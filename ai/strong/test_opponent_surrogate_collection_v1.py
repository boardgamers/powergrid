"""Whole-deal split, seat rotation and runtime/training isolation checks."""
import copy
from collections import Counter
import unittest

from opponent_surrogate_collection_v1 import PROTOCOL, read, contract, split


class CollectionContractTest(unittest.TestCase):
    def setUp(self):
        self.protocol = read(PROTOCOL)

    def test_full_grid_and_whole_deal_splits(self):
        rows = [contract(self.protocol,n,d,s,r,'collection')
                for n in range(2,7) for d in range(32) for s in range(n) for r in range(4)]
        self.assertEqual(len(rows), 2560)
        self.assertEqual(sum(q['twin'] for q in rows), 640)
        self.assertEqual(Counter(q['split'] for q in rows), {'train':1920,'validation':320,'test':320})
        self.assertEqual(len({(q['players'],q['episode']) for q in rows}), 2560)
        for n in range(2,7):
            for deal in range(32):
                group = [q for q in rows if (q['players'],q['deal']) == (n,deal)]
                self.assertEqual(len({q['split'] for q in group}),1)
                self.assertEqual({(q['focal_seat'],q['rule']) for q in group},
                                 {(s,r) for s in range(n) for r in range(4)})
                for q in group:
                    # Independent inversion of the existing engine's episode layout.
                    self.assertEqual(q['episode']//(4*n),deal)
                    self.assertEqual((q['episode']//4)%n,q['focal_seat'])
                    self.assertEqual(q['episode']%4,q['rule'])
                    self.assertEqual(q['training_eligible'],q['split']=='train')

    def test_probe_runtime_and_collection_seeds_are_disjoint(self):
        for n in range(2,7):
            rows=[contract(self.protocol,n,0,0,0,mode) for mode in ('collection','runtime','preflight')]
            seeds={q['seed'] for q in rows}
            self.assertEqual(len(seeds),3)
            self.assertNotIn(f'opponent-surrogate-capture-runtime-v1-{n}p',seeds)
            self.assertTrue(all(q['twin'] and not q['training_eligible'] for q in rows[1:]))

    def test_invalid_or_overlapping_split_is_rejected(self):
        bad=copy.deepcopy(self.protocol)
        bad['splits']['test'].append(0)
        with self.assertRaises(AssertionError): split(bad,0,'collection')
        invalid=[(2,32,0,0,'collection'),(2,1,0,0,'runtime'),(2,0,2,0,'collection'),
                 (1,0,0,0,'collection'),(7,0,0,0,'collection'),(2,0,0,4,'collection'),
                 (2,0,0,0,'final'),(2,-1,0,0,'collection'),(2,True,0,0,'collection')]
        for values in invalid:
            with self.subTest(values=values), self.assertRaises(AssertionError):
                contract(self.protocol,*values)


if __name__=='__main__': unittest.main()
