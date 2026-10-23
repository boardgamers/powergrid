"""Check actual learned inference: scope, parent values and paired-label parity."""
import json
import hashlib
from pathlib import Path
import tarfile
import numpy as np
import torch
from huggingface_hub import hf_hub_download
from strategic_collection import ROOT, read, digest
from strategic_correction_data import arrays
from model import policy_from_checkpoint
from infer import Model, Node

FIXTURE_SHA = 'f1c97bf909e38e5df372a89d169d80f5a6f24c00dccefacd60b10b767f1fcfa0'


def serving_fixtures():
    path = ROOT/'ai/strong/fixtures/multiplayer-serving-v1.jsonl'
    if not path.exists():
        source = read(ROOT/'ai/strong/strategic-teacher-training-source-v1.json')
        archive = hf_hub_download('coyotte508/powergrid-ai-training-v1', source['archive'],
            repo_type='dataset', revision=source['revision'])
        assert digest(archive) == source['sha256']
        with tarfile.open(archive) as bundle:
            data = bundle.extractfile('ai/strong/fixtures/multiplayer-serving-v1.jsonl').read()
        assert hashlib.sha256(data).hexdigest() == FIXTURE_SHA
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(data)
    assert digest(path) == FIXTURE_SHA
    return path


def check(checkpoint, model, fixtures, rows=None):
    assert digest(fixtures) == FIXTURE_SHA
    torch.set_num_threads(1)
    cp = torch.load(checkpoint, map_location='cpu', weights_only=True)
    assert cp['inference_precision'] == 'float64' and cp['inference_only']
    assert cp['feature_revision'] == '4.3-strategic-correction'
    native = policy_from_checkpoint(cp).eval()
    candidate = Model(model, threads=1)
    p = read(ROOT/'ai/strong/strategic-teacher-training-protocol-v1.json')
    pin = p['model']
    parent = Model(hf_hub_download(p['repo'], pin['path'], revision=pin['revision']), threads=1)
    assert parent.sha256 == pin['sha256']
    worker = Node('strong/worker.cjs')
    positions = eligible = changed = 0
    value_error = outside_error = 0.
    try:
        with Path(fixtures).open() as source:
            for line in source:
                fixture = json.loads(line)
                row = worker.call({**fixture['request'], 'featureRevision': cp['feature_revision']})
                assert row['moves'] == fixture['legal']
                state = np.asarray([row['state']], np.float32)
                actions = np.asarray([row['actions']], np.float32)
                mask = np.ones(actions.shape[:2], bool)
                actual = candidate.session.run(None, {'state':state, 'actions':actions, 'mask':mask})
                original = parent.session.run(None, {'state':state[:,:1216], 'actions':actions[:,:,:100], 'mask':mask})
                assert all(np.isfinite(output).all() for output in actual)
                np.testing.assert_allclose(actual[1], original[1], atol=1e-10, rtol=1e-10)
                value_error = max(value_error, float(np.abs(actual[1]-original[1]).max()))
                proposal, chosen = int(original[0].argmax()), int(actual[0].argmax())
                if row['state'][-1]:
                    eligible += 1
                    changed += chosen != proposal
                    assert chosen == proposal or row['actions'][chosen][-1] == 1
                else:
                    assert chosen == proposal
                    np.testing.assert_allclose(actual[0], original[0], atol=1e-10, rtol=1e-10)
                    outside_error = max(outside_error, float(np.abs(actual[0]-original[0]).max()))
                positions += 1
    finally:
        worker.close()
    assert positions == 2553 and eligible == 1096
    labels = 0
    label_error = 0.
    label_metrics = {}
    if rows is not None:
        assert len(rows) == 1920
        for split, count in [('train', 1440), ('validation', 480)]:
            subset = [row for row in rows if row['split'] == split]
            assert len(subset) == count
            data = arrays(subset)
            chosen = []
            for start in range(0, count, 64):
                batch = {name:data[name][start:start+64] for name in ['state','actions','mask']}
                actual = candidate.session.run(None, batch)
                with torch.inference_mode():
                    expected = [x.numpy() for x in native(*(torch.from_numpy(batch[name]) for name in ['state','actions','mask']))]
                for a, b in zip(actual, expected):
                    np.testing.assert_allclose(a, b, atol=1e-8, rtol=1e-10)
                np.testing.assert_array_equal(actual[0].argmax(1), expected[0].argmax(1))
                label_error = max(label_error, float(np.abs(actual[0]-expected[0]).max()))
                chosen.extend(actual[0].argmax(1).tolist())
                labels += len(batch['state'])
            selected = np.asarray(chosen)
            assert data['mask'][np.arange(count), selected].all()
            achieved = data['target'][np.arange(count), selected]
            label_metrics[split] = {'roots':count,
                'mean_simulated_advantage_over_parent':float(achieved.mean()),
                'changed_fraction':float((selected != data['proposal_index']).mean())}
        assert labels == 1920
    return {'positions':positions, 'eligible':eligible, 'changed_eligible':int(changed),
        'outside_scope_actions_preserved':positions-eligible, 'parent_values_preserved':True,
        'outside_max_logit_error':outside_error, 'max_value_error':value_error,
        'labels_strict_parity':labels, 'label_max_logit_error':label_error, 'label_metrics':label_metrics,
        'checkpoint_sha256':digest(checkpoint), 'model_sha256':candidate.sha256,
        'qualification_eligible':False,
        'scope':'Actual exported actions stay within the strategic shortlist or parent; other actions/values unchanged. Simulated label metrics are not strength evidence.'}
