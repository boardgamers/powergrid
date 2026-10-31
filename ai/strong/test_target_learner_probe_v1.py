import copy
import unittest
import numpy as np

from target_learner_probe_v1 import inputs, json_predict, route


class LearnerProbeTests(unittest.TestCase):
    def data(self):
        data = {'state': np.zeros((3, 1218), np.float32), 'actions': np.zeros((3, 2, 103), np.float32),
            'mask': np.ones((3, 2), bool), 'proposal_index': np.zeros(3, np.int64),
            'precision': np.ones((3, 2)), 'train': np.array([True, True, False]),
            'target': np.zeros((3, 2))}
        meta = [{'split': s, 'deal': d, 'source_game_seed': str(i), 'public_root_sha256': str(i)}
            for i, (s, d) in enumerate((('train', 1), ('train', 11), ('validation', 0)))]
        return data, meta

    def test_public_features_ignore_labels_and_policy_flags(self):
        data, meta = self.data(); before = inputs(data, meta)[0]
        data['target'][:] = 1; data['state'][:, 1215:1217] = 42; data['actions'][:, :, 100] = 42
        np.testing.assert_array_equal(before, inputs(data, meta)[0])
        data['state'][:, 1217] = 1
        self.assertFalse(np.array_equal(before, inputs(data, meta)[0]))

    def test_group_isolation_and_equal_root_weight(self):
        data, meta = self.data(); _, rows, _, weight, groups = inputs(data, meta)
        self.assertEqual({k: v.tolist() for k, v in groups.items()}, {'fit': [0], 'tune': [1], 'legacy_validation': [2]})
        np.testing.assert_allclose(np.bincount(rows, weights=weight), [1, 1, 1])
        meta[1]['source_game_seed'] = meta[0]['source_game_seed']
        with self.assertRaises(AssertionError): inputs(data, meta)

    def test_routing_baseline_zero_legal_mask_and_margin(self):
        scores = np.array([[99, .025, 2], [99, .03, 0]])
        mask = np.array([[True, True, False], [True, True, True]])
        np.testing.assert_array_equal(route(scores, mask, np.zeros(2, np.int64)), [0, 1])

    def test_numeric_tree_boundaries_and_leaf_sum(self):
        tree = {'categories': [], 'split_type': [0, 0, 0], 'left_children': [1, -1, -1],
            'right_children': [2, -1, -1], 'split_indices': [0, 0, 0], 'split_conditions': [.5, -.2, .3]}
        model = {'learner': {'objective': {'name': 'reg:squarederror'},
            'learner_model_param': {'num_target': '1', 'num_class': '0', 'num_feature': '1', 'base_score': '0.1'},
            'gradient_booster': {'name': 'gbtree', 'model': {'tree_info': [0, 0],
                'gbtree_model_param': {'num_parallel_tree': '1', 'num_trees': '2'}, 'trees': [tree, copy.deepcopy(tree)]}}}}
        np.testing.assert_allclose(json_predict(model, np.array([[.49], [.5]], np.float32)), [-.3, .7], atol=1e-7)


if __name__ == '__main__': unittest.main()
