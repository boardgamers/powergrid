"""Offline policy tests. Synthetic tensors are not training/evaluation evidence."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import torch
from torch import nn

import expert_policy as policy
from model import DIMS, GraphPolicy, SCHEMA as BASE_SCHEMA


def fixture(nodes=3, actions=2):
    rng = torch.Generator().manual_seed(19 + nodes + actions)
    return policy.row(dict(schema=BASE_SCHEMA,
        **{k: torch.rand((DIMS[k],) if k == 'global' else
             (nodes if k == 'nodes' else actions if k == 'actions' else 2, DIMS[k]), generator=rng).tolist()
           for k in DIMS},
        relations=torch.zeros(4, nodes, nodes).tolist(), actionCity=[i % nodes for i in range(actions)],
        prior=[0., -20.] + [-3.] * (actions - 2)))


class ExpertPolicyTests(unittest.TestCase):
    def test_zero_head_is_exact_prior_and_input_is_not_mutated(self):
        model = policy.ExpertPolicy(8)
        b = policy.batch([fixture(), fixture(5, 4)])
        before = {k: v.clone() for k, v in b.items()}
        logits, values = model(b)
        self.assertTrue(torch.equal(logits, b['prior']))
        self.assertTrue(torch.isfinite(values).all())
        self.assertTrue(all(torch.equal(v, before[k]) for k, v in b.items()))

    def test_floor_action_reachable_and_prior_feature_is_masked(self):
        model = policy.ExpertPolicy(8)
        class Scores(nn.Module):
            def forward(self, b):
                self.seen = b['actions'].detach().clone()
                return torch.tensor([[-100., 100., 0.]]), torch.zeros(1)
        scorer = Scores(); model.network = scorer
        b = dict(actions=torch.zeros(1, 3, 34), prior=torch.tensor([[0., -20., -1e9]]),
                 actionMask=torch.tensor([[True, True, False]]))
        logits, _ = model(b)
        self.assertEqual(int(logits.argmax(-1)), 1)
        self.assertEqual(scorer.seen.shape[-1], 35)
        self.assertTrue(torch.equal(scorer.seen[0, :, -1], torch.tensor([0., -1., 0.])))
        self.assertEqual(float(logits[0, 2]), -1e9)
        # Under the old +/-8 bound even its most favorable endpoints cannot win.
        self.assertLess(-20 + 8, 0 - 8)

    def test_padding_and_action_permutation(self):
        torch.manual_seed(919)
        model = policy.ExpertPolicy(8)
        nn.init.normal_(model.network.action[-1].weight, std=.1)
        a, b = fixture(), fixture(5, 4)
        with torch.no_grad():
            one = model(policy.batch([a]))
            together = model(policy.batch([a, b]))
            self.assertTrue(torch.allclose(one[0][0], together[0][0, :2], atol=1e-6))
            self.assertTrue(torch.allclose(one[1][0], together[1][0], atol=1e-6))
            permuted = copy.deepcopy(b)
            order = torch.tensor([3, 0, 2, 1])
            for name in ('actions', 'actionCity', 'targets', 'prior'):
                permuted[name] = permuted[name][order]
            original_logits, original_value = model(policy.batch([b]))
            permuted_logits, permuted_value = model(policy.batch([permuted]))
            self.assertTrue(torch.allclose(original_logits[:, order], permuted_logits, atol=1e-6))
            self.assertTrue(torch.equal(original_value, permuted_value))

    def test_warm_start_preserves_representation_and_inserts_zero_column(self):
        torch.manual_seed(4)
        base = GraphPolicy(64)
        state = base.state_dict()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'base.pt'
            torch.save(dict(schema=BASE_SCHEMA, width=64, state_dict=state), path)
            with self.assertRaisesRegex(ValueError, 'Wrong frozen'):
                policy.warm_start(path)
            with mock.patch.object(policy, 'digest', return_value=policy.PROTOCOL['warmStart']['sha256']):
                model = policy.warm_start(path)
            updated = model.network.state_dict()
            for name, original in state.items():
                actual = updated[name]
                if name == 'action.0.weight':
                    self.assertTrue(torch.equal(actual[:, :34], original[:, :34]))
                    self.assertTrue(torch.equal(actual[:, 35:], original[:, 34:]))
                    self.assertEqual(float(actual[:, 34].abs().sum()), 0)
                elif name.startswith('action.2.'):
                    self.assertEqual(float(actual.abs().sum()), 0)
                else:
                    self.assertTrue(torch.equal(actual, original), name)

    def test_checkpoint_identity_roundtrip_and_nonfinite_rejection(self):
        model = policy.ExpertPolicy(8)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'policy.pt'
            policy.save(path, model, update=0)
            recovered, saved = policy.load(path)
            self.assertEqual(saved['schema'], 'multimap-expert-ppo-v2')
            self.assertTrue(all(torch.equal(v, recovered.state_dict()[k]) for k, v in model.state_dict().items()))
            with self.assertRaises(ValueError):
                policy.save(path, model, schema='legacy')
            saved['bound'] = 8; torch.save(saved, path)
            with self.assertRaisesRegex(ValueError, 'identity'):
                policy.load(path)
            saved['bound'] = 16
            saved['state_dict']['network.city.0.weight'][0, 0] = float('nan')
            torch.save(saved, path)
            with self.assertRaisesRegex(ValueError, 'Nonfinite'):
                policy.load(path)


if __name__ == '__main__':
    unittest.main()
