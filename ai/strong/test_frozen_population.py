import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import torch
from model_v4 import MultiplayerPolicy
from frozen_population import load_population, actor_for_role, validate_specs
from snapshot_league import SnapshotLeague


class FrozenTests(unittest.TestCase):
    def test_verified_weights_are_frozen_and_roles_cannot_alias_a_snapshot(self):
        torch.set_num_threads(1)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            net = MultiplayerPolicy(width=8, ordered_players=True)
            specs = []
            for i in range(3):
                file = root / f'checkpoint-{i}.pt'
                torch.save({'state_dict': net.state_dict(), 'architecture': 'multiplayer_ordered',
                            'model_args': {'width': 8}, 'feature_revision': '4.0-multiplayer', 'update': i}, file)
                specs.append({'role': f'frozen{i}', 'revision': str(i)*40,
                              'path': f'runs/test/checkpoint-{i}.pt',
                              'sha256': hashlib.sha256(file.read_bytes()).hexdigest(),
                              'architecture': 'multiplayer_ordered', 'feature_revision': '4.0-multiplayer', 'update': i})
            config = root / 'population.json'
            config.write_text(json.dumps(specs))
            download = lambda repo, path, revision: str(root / Path(path).name)
            with patch('frozen_population.hf_hub_download', side_effect=download):
                actors, verified = load_population(config, 'local-test', 'cpu')
                self.assertEqual(verified, specs)
                league = SnapshotLeague(net)
                self.assertIs(actor_for_role('learner', net, league, actors), net)
                self.assertIs(actor_for_role('frozen1', net, league, actors), actors['frozen1'])
                self.assertIs(actor_for_role('snapshot1', net, league, actors), league.actors[0])
                before = next(actors['frozen0'].parameters()).detach().clone()
                with torch.no_grad():
                    next(net.parameters()).add_(1)
                torch.testing.assert_close(before, next(actors['frozen0'].parameters()))
                self.assertTrue(all(not a.training and all(not p.requires_grad for p in a.parameters()) for a in actors.values()))
                with self.assertRaises(ValueError):
                    actor_for_role('frozen3', net, league, actors)
                (root / 'checkpoint-0.pt').write_bytes(b'wrong artifact')
                with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                    load_population(config, 'local-test', 'cpu')
            for key, value in [('revision', 'main'), ('feature_revision', '3.0'), ('role', 'snapshot0')]:
                bad = copy.deepcopy(specs)
                bad[0][key] = value
                with self.assertRaises(ValueError):
                    validate_specs(bad)


if __name__ == '__main__':
    unittest.main()
