import unittest
import torch
from snapshot_league import SnapshotLeague


class LeagueTests(unittest.TestCase):
    def test_periodic_admission_survives_flat_selection_and_preserves_anchor(self):
        net = torch.nn.Linear(1, 1)
        league = SnapshotLeague(net, "periodic_anchor", 2)
        original = net.weight.detach().clone()
        for update in range(8):
            with torch.no_grad():
                net.weight.add_(1)
            league.admit(net, update, improved=False)
        self.assertEqual(league.updates, [-1, 5, 7])
        torch.testing.assert_close(league.actors[0].weight, original)
        torch.testing.assert_close(league.actors[1].weight, original + 6)
        torch.testing.assert_close(league.actors[2].weight, original + 8)
        self.assertFalse(league.admit(net, 7))
        self.assertTrue(all(not a.training and not a.weight.requires_grad for a in league.actors))

    def test_legacy_admission_keeps_last_three_improvements(self):
        net = torch.nn.Linear(1, 1)
        league = SnapshotLeague(net)
        self.assertFalse(league.admit(net, 0, improved=False))
        for u in [9, 19, 29]:
            self.assertTrue(league.admit(net, u, improved=True))
        self.assertEqual(league.updates, [9, 19, 29])

    def test_invalid_configuration_is_rejected(self):
        for mode, interval in [('unknown', 10), ('best', 0)]:
            with self.assertRaises(ValueError):
                SnapshotLeague(torch.nn.Linear(1, 1), mode, interval)


if __name__ == '__main__':
    unittest.main()
