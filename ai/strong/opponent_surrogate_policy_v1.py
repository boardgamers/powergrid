"""Deterministic public-feature inference for a frozen opponent surrogate."""
from pathlib import Path
import hashlib

import numpy as np
import onnxruntime as ort
from opponent_surrogate_training_v1 import inputs

SEEDS = (14101, 14102, 14103, 14104)
FEATURE_REVISION = '4.3-strategic-correction'


def log_probabilities(scores, mask):
    scores = np.asarray(scores, np.float64)
    assert scores.shape == mask.shape and np.isfinite(scores).all()
    assert mask.dtype == np.bool_ and mask.any(1).all()
    shifted = np.where(mask, scores, -np.inf)
    shifted -= shifted.max(1, keepdims=True)
    normalized = shifted - np.log(np.exp(shifted).sum(1, keepdims=True))
    return np.where(mask, normalized, -1e9)


def ensemble_scores(scores, mask):
    assert len(scores) == 4
    logp = np.stack([log_probabilities(s, mask) for s in scores])
    mean = np.logaddexp.reduce(logp, axis=0) - np.log(4.)
    return np.where(mask, mean, -1e9)


def make_policy(member_pins):
    assert [m['seed'] for m in member_pins] in [[], *[[s] for s in SEEDS], list(SEEDS)]
    return {'version': 1, 'role': 'opponent_surrogate_v1', 'feature_revision': FEATURE_REVISION,
            'state_dim': 1217, 'action_dim': 101, 'max_candidates': 6,
            'members': member_pins,
            'scoring': 'economic-prior' if not member_pins else 'single-logits' if len(member_pins) == 1 else 'mean-probability',
            'action_selection': 'argmax-first-legal-index', 'qualification_eligible': False}


class SurrogatePolicy:
    def __init__(self, policy, artifacts, threads=1):
        assert type(threads) is int and 1 <= threads <= 8
        expected = make_policy(policy['members'])
        assert all(policy[k] == value for k, value in expected.items())
        self.policy, self.sessions = policy, []
        for member in policy['members']:
            assert member['path'] == f"{member['seed']}/derivative/inference64.onnx"
            path = Path(artifacts)/member['path']
            assert hashlib.sha256(path.read_bytes()).hexdigest() == member['sha256']
            options = ort.SessionOptions(); options.intra_op_num_threads = threads; options.inter_op_num_threads = 1
            session = ort.InferenceSession(str(path), sess_options=options, providers=['CPUExecutionProvider'])
            meta = session.get_modelmeta().custom_metadata_map
            assert meta['powergrid.role'] == 'opponent_surrogate_v1'
            assert meta['powergrid.feature_revision'] == FEATURE_REVISION
            assert meta['powergrid.inference_precision'] == 'float64'
            assert meta['powergrid.inference_transform'] == 'float64-exp-div-silu-v1'
            assert meta['powergrid.source_checkpoint_sha256'] == member['checkpoint_sha256']
            assert [i.name for i in session.get_inputs()] == ['state', 'actions', 'mask']
            assert [(o.name, o.type) for o in session.get_outputs()] == [('logits', 'tensor(double)')]
            self.sessions.append(session)

    def scores(self, data, batch_size=256):
        assert type(batch_size) is int and batch_size > 0
        n = len(data['state']); assert n > 0
        assert data['state'].shape == (n, 1217) and data['state'].dtype == np.float32
        assert data['actions'].shape == (n, 6, 101) and data['actions'].dtype == np.float32
        assert data['mask'].shape == (n, 6) and data['mask'].dtype == np.bool_
        assert np.isfinite(data['state']).all() and np.isfinite(data['actions']).all()
        counts = data['mask'].sum(1); assert ((1 <= counts) & (counts <= 6)).all()
        assert np.array_equal(data['mask'], np.arange(6)[None] < counts[:, None])
        result = []
        for start in range(0, n, batch_size):
            feed = {k: np.array(data[k][start:start+batch_size], copy=True) for k in ('state', 'actions', 'mask')}
            if not self.sessions:
                values = 2 * feed['actions'][:, :, 74].astype(np.float64)
            else:
                scores = [s.run(['logits'], feed)[0] for s in self.sessions]
                assert all(s.shape == feed['mask'].shape and s.dtype == np.float64 and np.isfinite(s).all() for s in scores)
                values = scores[0] if len(scores) == 1 else ensemble_scores(scores, feed['mask'])
            result.append(np.where(feed['mask'], values, -1e9))
        return np.concatenate(result)

    def predict_batch(self, observations):
        if not observations: return []
        packed = [inputs(o) for o in observations]
        data = {k: np.stack([row[k] for row in packed]) for k in ('state', 'actions', 'mask')}
        choices = np.where(data['mask'], self.scores(data), -np.inf).argmax(1)
        return [int(row['legal_indices'][choice]) for row, choice in zip(packed, choices)]
