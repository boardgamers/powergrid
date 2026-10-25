"""Synthetic contract tests only: no game execution, inference or final seed use."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from public_policy_final_audit_v1 import (artifact_identity, assess_final_games,
    audit_public_decision, audit_terminal, protocol, schedule, validate_identity)


def identity(auction=False):
    result = {'policySha256': 'a'*64, 'runtimeManifestSha256': 'b'*64,
              'modelSha256': 'c'*64, 'featureRevision': '4.3-strategic-correction',
              'backend': 'opponent-auction-v1' if auction else 'population-v1',
              'settings': {'arm': 'auction' if auction else 'filter', 'samples': 8,
                           'workers': 4, 'threads': 1, 'max_steps': 2400}}
    if auction:
        result['opponentPolicySha256'] = 'd'*64
        result['settings'].update(population_modes=['neural_population', 'surrogate_opponent_v1'], minimum_advantage='1/8')
    return result


def record(shard, episode, *, tied=False):
    n = shard['players']; seat = episode//4 % n
    role = 'snapshot0' if shard['opponent'] == 'a260' else shard['opponent']
    players = [{'powered': 20 if tied or i == seat else 19, 'money': 0,
                'cities': 20, 'capacity': 20, 'plants': [30, 40, 50]} for i in range(n)]
    values = [1/n if tied else int(i == seat) for i in range(n)]
    terminal = {'episode': episode, 'env': 0, 'seat': seat, 'playerCount': n,
                'gameSeed': shard['seed']+'-'+str(episode//(4*n)),
                'variant': 'recharged' if episode % 2 else 'original', 'sealed': episode % 4 < 2,
                'truncated': False, 'steps': 100, 'roles': ['learner' if i == seat else role for i in range(n)],
                'value': values, 'win': values[seat], 'final': {'round': 10, 'players': players},
                'searchStats': {'search_geo': {'decisions': 1, 'evaluations': 16, 'truncated': 0}}
                               if role == 'search_geo' else {}}
    return {'episode': episode, 'terminal': terminal, 'rollout_caps': 0}


def synthetic_audits(selected):
    # Deliberately fabricated inputs to test only aggregate gate mathematics;
    # these are never written as real evidence or submitted to the engine.
    result = []
    for shard in schedule():
        n = shard['players']
        rows = [record(shard, e)['terminal'] for e in range(shard['start']*4*n, (shard['start']+4)*4*n)]
        result.append({'audit_version': 1, 'all_receipts_verified': True,
                       'reserved_final_seeds_used': True, 'qualification_eligible': False,
                       'identity': selected, 'expected': shard, 'terminals': rows,
                       'counts': {'rollout_caps': 0, 'search_decisions': 0, 'rollouts': 0}})
    return result


class FinalAuditContracts(unittest.TestCase):
    def test_full_existing_schedule_has_exact_disjoint_deals(self):
        planned = schedule()
        self.assertEqual(len(planned), 320)
        self.assertEqual(sum(s['games'] for s in planned), 20160)
        groups = {}
        for shard in planned:
            seen = groups.setdefault(shard['group'], set())
            new = set(range(shard['start'], shard['start']+shard['deals']))
            self.assertFalse(seen & new); seen.update(new)
        self.assertEqual(len(groups), 26)
        self.assertEqual({len(v) for v in groups.values()}, {40, 80})

    def test_protocol_threshold_change_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/'protocol.json'
            changed = protocol(); changed['opponents'][0]['counts']['2']['minimum_win_rate'] = .5
            p.write_text(json.dumps(changed))
            with self.assertRaisesRegex(ValueError, 'protocol changed'):
                protocol(p)

    def test_complete_identity_includes_opponent_and_override_rule(self):
        selected = identity(True); validate_identity(selected)
        bad = copy.deepcopy(selected); del bad['opponentPolicySha256']
        with self.assertRaises(ValueError): validate_identity(bad)
        for change in [{'search_scope': 'auction'}, {'minimum_advantage': 0.125}, {'minimum_advantage': '2/16'},
                       {'samples': 16}, {'max_steps': 1}, {'threads': True}, {'population_modes': []}]:
            bad = copy.deepcopy(selected); bad['settings'].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError): validate_identity(bad)

    def test_artifact_identity_checks_real_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); manifest = {}
            for name in ['model.onnx', 'ai/strong/public_policy_arena_v1.py', 'ai/strong/public_policy_runtime_v1.py']:
                p = root/name; p.parent.mkdir(parents=True, exist_ok=True); p.write_text('synthetic bytes; never executed')
                manifest[name] = hashlib.sha256(p.read_bytes()).hexdigest()
            (root/'manifest.json').write_text(json.dumps(manifest))
            spec = {'version': 1, 'backend': 'population-v1', 'feature_revision': '4.3-strategic-correction',
                    'model': {'path': 'model.onnx', 'sha256': manifest['model.onnx']},
                    'runtime_manifest': {'path': 'manifest.json', 'sha256': hashlib.sha256((root/'manifest.json').read_bytes()).hexdigest()},
                    'settings': identity()['settings']}
            (root/'policy.json').write_text(json.dumps(spec))
            self.assertEqual(artifact_identity(root)['modelSha256'], manifest['model.onnx'])
            (root/'model.onnx').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'Changed runtime file'):
                artifact_identity(root)

    def test_terminal_ties_are_recomputed_and_pairing_is_exact(self):
        shard = next(s for s in schedule() if s['players'] == 3 and s['opponent'] == 'economic')
        good = record(shard, 0, tied=True)
        self.assertEqual(audit_terminal(good, shard)['win'], 1/3)
        for field, value in [('win', 1), ('sealed', False), ('seat', True), ('truncated', True),
                             ('gameSeed', 'different'), ('value', [True, 0, 0])]:
            bad = copy.deepcopy(good); bad['terminal'][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError): audit_terminal(bad, shard)

    def test_missing_independent_search_cannot_pass(self):
        shard = next(s for s in schedule() if s['opponent'] == 'search_geo')
        bad = record(shard, 0); bad['terminal']['searchStats'] = {}
        with self.assertRaisesRegex(ValueError, 'independent-search'):
            audit_terminal(bad, shard)

    def public_row(self):
        selected = identity(); move = {'name': 'Pass', 'data': True}
        decision = {'index': 0, 'move': move}
        request = {'requestId': '0:1', 'revision': 1, 'player': 0,
                   'state': {'seed': 'secret', 'powerPlantsDeck': [], 'options': {'fastBid': True},
                             'players': [{'bid': 0}, {'bid': 0}]}}
        response = {**selected, 'requestId': '0:1', 'revision': 1, 'playerOrder': [0, 1],
                    'move': move, 'decision': decision, 'qualification_eligible': False}
        return {'decision': 1, **decision, 'publicRequest': request, 'publicResponse': response,
                'arenaMoves': [move], 'arenaPlayerOrder': [0, 1]}

    def test_public_metadata_identity_and_legal_move_are_bound(self):
        good = self.public_row(); audit_public_decision(good, identity(), 0, 0, 1)
        for field, value in [('requestId', '0:0'), ('revision', True), ('policySha256', 'e'*64),
                             ('playerOrder', [1, 0]), ('move', {'name': 'Bid', 'data': 300})]:
            bad = copy.deepcopy(good); bad['publicResponse'][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                audit_public_decision(bad, identity(), 0, 0, 1)

    def test_hidden_state_and_prior_sealed_bids_are_rejected(self):
        good = self.public_row()
        for change in [{'seed': 'private'}, {'powerPlantsDeck': [50]}, {'hiddenLog': ['private']},
                       {'powerPlantDeckAfterStep3': []}, {'players': [{'bid': 0}, {'bid': 12}]}]:
            bad = copy.deepcopy(good); bad['publicRequest']['state'].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                audit_public_decision(bad, identity(), 0, 0, 1)

    def test_complete_strength_pass_never_implies_full_qualification(self):
        result = assess_final_games(synthetic_audits(identity()), identity())
        self.assertTrue(result['strength_passed']); self.assertEqual(result['games'], 20160)
        self.assertFalse(result['qualified']); self.assertTrue(result['remaining_qualification_requirements'])

    def test_missing_duplicated_and_crossed_policy_shards_are_rejected(self):
        rows = synthetic_audits(identity())
        for bad in [rows[:-1], [rows[0], *rows]]:
            with self.assertRaises(ValueError): assess_final_games(bad, identity())
        rows[0]['identity'] = identity(True)
        with self.assertRaisesRegex(ValueError, 'Mixed final policies'): assess_final_games(rows, identity())

    def test_bad_rule_cannot_hide_in_good_overall_average(self):
        rows = synthetic_audits(identity())
        for shard in rows:
            if shard['expected']['group'] == 'search_geo/4p':
                for row in shard['terminals']:
                    if row['variant'] == 'recharged' and row['sealed']:
                        row['value'] = [int(i == (row['seat']+1) % 4) for i in range(4)]; row['win'] = 0
        result = assess_final_games(rows, identity())
        self.assertEqual(result['evaluations']['search_geo/4p']['overall']['win_rate'], .75)
        self.assertIn('search_geo/4p/recharged/sealed: lower bound does not exceed chance', result['errors'])
        self.assertFalse(result['strength_passed'])

    def test_default_bot_ninety_percent_floor_is_not_relaxed(self):
        rows = synthetic_audits(identity())
        for shard in rows:
            if shard['expected']['group'] == 'legacy/2p':
                for row in shard['terminals']:
                    if row['episode']//8 < 5:
                        row['value'] = [int(i != row['seat']) for i in range(2)]; row['win'] = 0
        result = assess_final_games(rows, identity())
        self.assertEqual(result['evaluations']['legacy/2p']['overall']['win_rate'], .875)
        self.assertIn('legacy/2p: minimum win rate failed', result['errors'])

    def test_search_identity_requires_actual_candidate_search(self):
        with self.assertRaisesRegex(ValueError, 'search never executed'):
            assess_final_games(synthetic_audits(identity(True)), identity(True))

    def test_job_completion_order_cannot_change_bootstrap_gate(self):
        rows = synthetic_audits(identity())
        for shard in rows:
            if shard['expected']['group'] == 'search_geo/6p':
                for row in shard['terminals']:
                    deal = row['episode']//24
                    if deal % 7 in (0, 2, 3):
                        ties = 2 + deal % 5
                        winners = {(row['seat']+i) % 6 for i in range(ties)}
                        row['value'] = [1/ties if i in winners else 0 for i in range(6)]
                        row['win'] = row['value'][row['seat']]
        expected = assess_final_games(rows, identity())
        shuffled = [*rows[1::2], *rows[::2]][::-1]
        for shard in shuffled:
            shard['terminals'] = list(reversed(shard['terminals']))
        self.assertEqual(assess_final_games(shuffled, identity()), expected)


if __name__ == '__main__':
    unittest.main()
