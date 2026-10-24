import copy
import unittest

from strategic_collection import read
from resource_development_v1 import PROTOCOL, ARMS, validate, verify_pins, case_rows


class ResourceDevelopmentTests(unittest.TestCase):
    def test_protocol_source_evidence_and_current_screen_pins(self):
        verify_pins(read(PROTOCOL))

    def test_every_allowed_partition_preserves_all_deals_seats_and_rules(self):
        protocol = read(PROTOCOL)
        expected = {(arm, s['players'], s['opponent'], deal)
                    for arm in ARMS for s in protocol['screens'] for deal in range(4)}
        for size in (1, 2, 4):
            rows = case_rows(protocol, size)
            self.assertEqual(len(rows), 216 // size)
            observed = set()
            for row in rows:
                self.assertEqual(row['games'], (row['end'] - row['start']) * 4 * row['players'])
                for deal in range(row['start'], row['end']):
                    item = (row['arm'], row['players'], row['opponent'], deal)
                    self.assertNotIn(item, observed)
                    observed.add(item)
            self.assertEqual(observed, expected)
            self.assertEqual(sum(r['games'] for r in rows), 3360)
        for invalid in (0, 3, 5, -1, True, 1.0):
            with self.subTest(size=invalid), self.assertRaises(AssertionError):
                case_rows(protocol, invalid)

    def test_weakened_or_reused_design_rejected(self):
        original = read(PROTOCOL)
        def change(path, value):
            protocol = copy.deepcopy(original)
            pointer = protocol
            for part in path[:-1]:
                pointer = pointer[part]
            pointer[path[-1]] = value
            return protocol
        cases = [
            (['seed_template'], 'population-hybrid-development-v1-{players}p'),
            (['smoke_seed_template'], original['seed_template']),
            (['deal_offsets'], [0, 1, 2]),
            (['search', 'samples'], 4),
            (['search', 'horizon'], 1200),
            (['search', 'nested_search'], True),
            (['game_max_steps'], 800),
            (['screens', 0, 'games'], 1),
            (['screens', 0, 'deals'], 1),
            (['screens', 0, 'players'], 7),
            (['screens', 0, 'opponent'], 'unknown'),
            (['planned_games_total'], 1680),
            (['model_pin', 'files', 'inference64.onnx'], '0' * 64),
            (['prerequisites', 'current_comparison_required'], False),
            (['prerequisites', 'new_resource_runtime_pilots_required'], False),
            (['prerequisites', 'automatic_launch'], True),
            (['qualification_eligible'], True),
            (['reserved_final_seeds_used'], True),
            (['hf_jobs_submitted'], 1),
            (['gradients'], True),
        ]
        for path, value in cases:
            with self.subTest(path=path), self.assertRaises(AssertionError):
                validate(change(path, value))
        self.assertEqual(len(cases), 20)
        for field in ['source_overlays', 'evidence_hashes']:
            protocol = copy.deepcopy(original)
            protocol[field][next(iter(protocol[field]))] = '0' * 64
            with self.subTest(pin=field), self.assertRaises(AssertionError):
                verify_pins(protocol)


if __name__ == '__main__':
    unittest.main()
