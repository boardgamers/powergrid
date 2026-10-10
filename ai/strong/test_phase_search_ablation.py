"""Routing contracts, not game-strength tests."""
import copy
import unittest

from phase_search_ablation import PhaseRouter


class RouterContracts(unittest.TestCase):
    def test_filters_only_the_requested_learner_phases(self):
        observations = [{'episode': 0, 'searchPhase': phase, 'roles': ['learner', 'snapshot0'], 'seat': 0}
                        for phase in ['auction', 'building', 'other']]
        observations += [{'episode': 1, 'searchPhase': 'building', 'roles': ['learner', 'snapshot0'], 'seat': 1}, None]
        request = {'op': 'step', 'actions': [{'proposal': i, 'searchSamples': 48, 'geography': True}
                                          for i in range(3)] + [7, None]}
        pristine = copy.deepcopy(request)
        for arm, searched in [('all', [True, True]), ('auction', [True, False]), ('building', [False, True])]:
            router = PhaseRouter(arm)
            router.observe({'observations': observations, 'ended': []})
            result = router.filter(request)
            for i in range(2):
                self.assertEqual(result['actions'][i], request['actions'][i] if searched[i] else i)
            self.assertEqual(result['actions'][2:], [2, 7, None])
            self.assertEqual(request, pristine)
            ended = router.observe({'observations': [None]*5, 'ended': [{'episode': 0}, {'episode': 1}]})['ended']
            for i, phase in enumerate(['auction', 'building']):
                self.assertEqual(ended[0]['phaseRouting'][phase], {'opportunities': 1, 'searched': int(searched[i])})
                self.assertEqual(ended[1]['phaseRouting'][phase], {'opportunities': 0, 'searched': 0})
            self.assertEqual(router.counts, {})

    def test_unknown_phase_and_opponent_search_cannot_silently_route(self):
        request = {'op': 'step', 'actions': [{'proposal': 0, 'searchSamples': 48}]}
        for row in [{'episode': 0, 'searchPhase': 'unknown', 'roles': ['learner'], 'seat': 0},
                    {'episode': 0, 'searchPhase': 'auction', 'roles': ['snapshot0'], 'seat': 0}]:
            router = PhaseRouter('all'); router.observe({'observations': [row], 'ended': []})
            with self.assertRaises(AssertionError): router.filter(request)


if __name__ == '__main__': unittest.main()
