import copy
import unittest

from public_policy_arena_v1 import validate_response, arena_semantic


class PublicArenaContracts(unittest.TestCase):
    def setUp(self):
        self.request = {'requestId': '3:5', 'revision': 5}
        self.moves = [{'name': 'Pass', 'data': True}, {'name': 'Bid', 'data': 4}]
        self.identity = {'policySha256': 'a'*64, 'settings': {'arm': 'filter'}}
        self.response = {**self.request, **self.identity, 'playerOrder': [1, 0],
                         'move': self.moves[1], 'decision': {'index': 1, 'move': self.moves[1]},
                         'qualification_eligible': False}

    def check(self, response):
        return validate_response(response, self.request, self.moves, [1, 0], self.identity)

    def test_valid_move_comes_from_independent_menu(self):
        self.assertEqual(self.check(self.response), 1)

    def test_stale_metadata_order_identity_and_backend_errors_are_rejected(self):
        for field, value in [('requestId', '3:4'), ('revision', 4), ('playerOrder', [0, 1]),
                             ('policySha256', 'b'*64), ('settings', {'arm': 'auction'}),
                             ('qualification_eligible', True), ('error', 'backend failed')]:
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.check({**self.response, field: value})

    def test_illegal_move_or_diagnostic_index_cannot_drive_engine(self):
        for move in [{'name': 'Bid', 'data': 5}, {'name': 'Pass', 'data': 1}]:
            with self.assertRaises(ValueError):
                self.check({**self.response, 'move': move})
        for index in [0, True, -1, 20]:
            response = copy.deepcopy(self.response); response['decision']['index'] = index
            with self.assertRaises(ValueError):
                self.check(response)
        response = copy.deepcopy(self.response); response['decision']['move'] = self.moves[0]
        with self.assertRaises(ValueError):
            self.check(response)

    def test_ambiguous_legal_menu_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_response(self.response, self.request, [self.moves[1], self.moves[1]], [1, 0], self.identity)

    def test_only_wall_clock_bookkeeping_is_ignored_in_reference_trajectory(self):
        original = {'observations': [{'request': {'state': {'players': [{'money': 30, 'totalTimeUsed': 3}],
                    'log': [{'move': {'name': 'Bid', 'data': 3, 'time': 100}}]}}}], 'ended': []}
        twin = copy.deepcopy(original)
        twin['observations'][0]['request']['state']['players'][0].update(totalTimeUsed=8, clockStartedAt=200)
        twin['observations'][0]['request']['state']['log'][0]['move']['time'] = 200
        self.assertEqual(arena_semantic(original), arena_semantic(twin))
        twin['observations'][0]['request']['state']['players'][0]['money'] = 29
        self.assertNotEqual(arena_semantic(original), arena_semantic(twin))


if __name__ == '__main__':
    unittest.main()
