import unittest
from collections import defaultdict
from distill_data import source_count_weights, validate_initial_checkpoint


class ReplayTests(unittest.TestCase):
    def test_each_source_and_count_has_equal_total_mass(self):
        rows = [
            dict(dataset_source=s, player_count=n)
            for s in range(2)
            for n in range(2, 7)
            for _ in range((s + 1) * n)
        ]
        weights = source_count_weights(rows, range(2, 7))
        mass = defaultdict(float)
        for row in rows:
            key = row["dataset_source"], row["player_count"]
            mass[key] += weights[key]
        for value in mass.values():
            self.assertAlmostEqual(value, len(rows) / 10)

    def test_single_source_retains_original_count_balance(self):
        rows = [dict(player_count=n) for n in range(2, 7) for _ in range(n)]
        weights = source_count_weights(rows, range(2, 7))
        for n in range(2, 7):
            self.assertEqual(weights[0, n], len(rows) / (5 * n))

    def test_missing_count_cannot_hide_in_other_source(self):
        rows = [dict(dataset_source=0, player_count=n) for n in range(2, 7)]
        rows.append(dict(dataset_source=1, player_count=3))
        with self.assertRaises(ValueError):
            source_count_weights(rows, range(2, 7))

    def test_warm_start_rejects_feature_or_architecture_transfer(self):
        good = dict(
            architecture="multiplayer_ordered",
            feature_revision="4.0-multiplayer",
            state_dim=1149,
            action_dim=98,
        )
        args = ("multiplayer_ordered", "4.0-multiplayer", 1149, 98)
        validate_initial_checkpoint(good, *args)
        for key, wrong in [
            ("architecture", "multiplayer"),
            ("feature_revision", "3.0"),
            ("state_dim", 738),
            ("action_dim", 96),
        ]:
            with self.assertRaises(ValueError):
                validate_initial_checkpoint({**good, key: wrong}, *args)


if __name__ == "__main__":
    unittest.main()
