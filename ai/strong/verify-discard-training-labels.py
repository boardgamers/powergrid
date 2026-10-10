"""Recompute public features, parent scores and every teacher target before training."""
import argparse
from collections import Counter
import gzip
import importlib.util
import itertools
import json
from pathlib import Path
import re
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'ai'))
from infer import Model, Node
from huggingface_hub import hf_hub_download
spec = importlib.util.spec_from_file_location('label_audit_collector', Path(__file__).with_name('collect-public-discard-teacher.py'))
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
read, write, digest = audit.read, audit.write, audit.digest


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('players', type=int, choices=range(2, 7))
    p.add_argument('revision')
    p.add_argument('output', type=Path)
    a = p.parse_args()
    assert re.fullmatch('[a-f0-9]{40}', a.revision)
    protocol_path = ROOT / 'ai/strong/discard-training-labels-protocol-v1.json'
    protocol = read(protocol_path)
    source = read(ROOT / 'ai/strong/discard-training-labels-source-v1.json')
    out = a.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    prefix = f'runs/discard-training-labels-v1-{a.players}p'
    def fetch(name):
        assert name in ['labels-check.json', 'labels.jsonl.gz', 'inputs/verified.json']
        raw = Path(hf_hub_download(protocol['repo'], prefix + '/' + name, revision=a.revision)).read_bytes()
        (out / name).parent.mkdir(exist_ok=True)
        (out / name).write_bytes(raw)
    fetch('labels-check.json')
    status = read(out / 'labels-check.json')
    expected = {'status': 'complete', 'players': a.players, 'smoke': False,
        'protocol_sha256': digest(protocol_path), 'source_revision': source['revision'],
        'source_sha256': source['sha256'], 'model_sha256': protocol['model']['sha256'],
        'truncated': 0, 'trained': False, 'qualification_eligible': False}
    for k, v in expected.items():
        assert status[k] == v, k
    assert re.fullmatch('[a-f0-9]{40}', status['data_revision'])
    assert set(status['artifact_sha256']) == {'labels.jsonl.gz'}
    fetch('labels.jsonl.gz')
    fetch('inputs/verified.json')
    assert digest(out / 'labels.jsonl.gz') == status['artifact_sha256']['labels.jsonl.gz']
    assert digest(out / 'inputs/verified.json') == status['input_verification_sha256']
    inputs = read(out / 'inputs/verified.json')
    assert inputs['revision'] == status['data_revision'] and inputs['players'] == a.players
    assert inputs['no_deal_split_leakage'] and not inputs['truncations']
    raw_path = Path(hf_hub_download(protocol['repo'], f'runs/discard-training-collection-v1-{a.players}p/roots.jsonl.gz', revision=status['data_revision']))
    assert digest(raw_path) == inputs['sha256']['roots.jsonl.gz'] == status['input_roots_sha256']
    pin = protocol['model']
    model = Model(hf_hub_download(protocol['repo'], pin['path'], revision=pin['revision']), threads=4)
    assert model.sha256 == pin['sha256']
    worker = Node('strong/worker.cjs')
    counts, changed, all_tied, seen, evaluations = Counter(), Counter(), Counter(), set(), 0
    engine_seconds, max_logit_error = 0., 0.
    keys = ['rootId', 'rootIndex', 'players', 'mode', 'episode', 'ordinal', 'deal', 'gameSeed',
            'split', 'variant', 'sealed', 'round', 'public_root_sha256', 'model_proposal']
    guidance_protocol = {'continuations': [protocol['continuation']], 'batches': ['a'],
        'samples_per_batch': protocol['samples']}
    try:
        with gzip.open(raw_path, 'rt') as raw, gzip.open(out / 'labels.jsonl.gz', 'rt') as labels:
            for root_line, label_line in itertools.zip_longest(raw, labels):
                assert root_line is not None and label_line is not None, 'Missing/extra training label'
                root, label = json.loads(root_line), json.loads(label_line)
                assert all(root[k] == label[k] for k in keys)
                assert root['rootId'] not in seen
                seen.add(root['rootId'])
                assert label['featureRevision'] == protocol['feature_revision']
                new = worker.call({**root['request'], 'featureRevision': protocol['feature_revision']})
                old = worker.call({**root['request'], 'featureRevision': protocol['parent_feature_revision']})
                assert new['moves'] == old['moves'] == root['legal'] == label['legal']
                assert new['state'] == label['state'] and new['actions'] == label['actions']
                assert new['state'][:1149] == old['state'] and [r[:98] for r in new['actions']] == old['actions']
                assert len(new['state']) == protocol['state_dim'] and all(len(r) == protocol['action_dim'] for r in new['actions'])
                acts = np.asarray(old['actions'], dtype=np.float32)[None]
                logits, _ = model.session.run(None, {'state': np.asarray(old['state'], dtype=np.float32)[None],
                    'actions': acts, 'mask': np.ones(acts.shape[:2], dtype=bool)})
                stored = np.asarray(label['parent_logits'])
                assert stored.shape == logits[0].shape and np.isfinite(stored).all()
                assert np.allclose(logits[0], stored, rtol=1e-4, atol=1e-5)
                assert int(logits[0].argmax()) == int(stored.argmax()) == root['model_proposal']
                max_logit_error = max(max_logit_error, float(np.max(np.abs(logits[0] - stored))))
                n, caps = audit.verify_rows([label['guidance']], [root], guidance_protocol)
                assert caps == 0
                evaluations += n
                engine_seconds += label['guidance']['timing']['engine_seconds']
                key = root['mode'] + '/' + root['split']
                counts[key] += 1
                changed[key] += root['model_proposal'] not in label['guidance']['winner_set']
                all_tied[key] += len(label['guidance']['winner_set']) == len(root['legal'])
    finally:
        worker.close()
    assert len(seen) == status['roots'] == inputs['roots']
    assert dict(counts) == status['counts']
    assert evaluations == status['evaluations'] and engine_seconds == status['engine_seconds']
    for mode, splits in inputs['counts'].items():
        assert splits == {s: counts[mode + '/' + s] for s in ['train', 'validation']}
    summary = {'revision': a.revision, 'prefix': prefix, 'players': a.players,
        'data_revision': status['data_revision'], 'roots': len(seen), 'evaluations': evaluations,
        'truncated': 0, 'features_and_parent_logits_recomputed': len(seen), 'max_parent_logit_error': max_logit_error,
        'no_deal_split_leakage': True, 'counts': dict(counts), 'teacher_changes': dict(changed),
        'all_actions_tied': dict(all_tied), 'root_splits': inputs['root_splits'],
        'sha256': {name: digest(out / name) for name in ['labels-check.json', 'labels.jsonl.gz', 'inputs/verified.json']},
        'trained': False, 'qualification_eligible': False,
        'interpretation': 'Complete economic-continuation labels on fresh public roots; target validity is not teacher strength across every scope cell or learned-policy benefit. Preserve held-out whole deals and validate complete games.'}
    write(out / 'verified.json', summary)
    print({k: summary[k] for k in ['players', 'roots', 'evaluations', 'truncated', 'max_parent_logit_error']})


if __name__ == '__main__':
    main()
