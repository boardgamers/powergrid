"""Label all fresh public late-discard roots; preserve sample outcomes and splits."""
import argparse
from collections import Counter
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'ai'))
from infer import Model, Node
from pool import EnginePool
from huggingface_hub import HfApi, hf_hub_download
spec = importlib.util.spec_from_file_location('training_discard_audit', Path(__file__).with_name('audit-public-discard-teacher.py'))
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
def read(path):
    return json.loads(Path(path).read_text())
def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + '\n')


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('players', type=int, choices=range(2, 7))
    p.add_argument('revision')
    p.add_argument('output', type=Path)
    p.add_argument('--smoke-roots', type=Path, help='Local smoke only: first root per family, two scenarios')
    p.add_argument('--upload', action='store_true')
    a = p.parse_args()
    assert not os.environ.get('NODE_OPTIONS')
    assert not (a.smoke_roots and a.upload)
    assert a.revision == 'smoke' if a.smoke_roots else re.fullmatch('[a-f0-9]{40}', a.revision)
    protocol_path = ROOT / 'ai/strong/discard-training-labels-protocol-v1.json'
    protocol = read(protocol_path)
    assert digest(ROOT / 'ai/strong/discard-training-collection-protocol-v1.json') == protocol['collection_protocol_sha256']
    source = read(ROOT / 'ai/strong/discard-training-collection-source-v1.json')
    assert {k: source[k] for k in ['archive', 'revision', 'sha256']} == protocol['collection_source']
    out = a.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    status = {'status': 'running', 'players': a.players, 'smoke': bool(a.smoke_roots),
        'data_revision': a.revision, 'protocol_sha256': digest(protocol_path),
        'source_revision': os.environ.get('SOURCE_REVISION'), 'source_sha256': os.environ.get('SOURCE_SHA256'),
        'trained': False, 'qualification_eligible': False}
    model, worker, pool = None, None, None
    counts, caps, evaluations, decisions, engine_seconds = Counter(), 0, 0, 0, 0.
    begin = time.monotonic()
    try:
        if a.smoke_roots:
            fixtures = a.smoke_roots.resolve()
        else:
            subprocess.run([sys.executable, str(ROOT / 'ai/strong/verify-discard-training-collection.py'),
                str(a.players), a.revision, str(out / 'inputs')], cwd=ROOT, check=True)
            verified = read(out / 'inputs/verified.json')
            fixtures = out / 'inputs/roots.jsonl.gz'
            assert verified['players'] == a.players and verified['no_deal_split_leakage'] and not verified['truncations']
            status['input_verification_sha256'] = digest(out / 'inputs/verified.json')
        status['input_roots_sha256'] = digest(fixtures)
        pin = protocol['model']
        model = Model(hf_hub_download(protocol['repo'], pin['path'], revision=pin['revision']), threads=protocol['ort_threads'])
        assert model.sha256 == pin['sha256']
        status['model_sha256'] = model.sha256
        worker = Node('strong/worker.cjs')
        samples = 2 if a.smoke_roots else protocol['samples']
        pool = EnginePool(min(protocol['workers'], samples * (4 if a.players == 2 else 3)),
                          script='ai/strong/continuation-rollouts.cjs')
        seen, smoke_modes = set(), set()
        with gzip.open(fixtures, 'rt') as file, gzip.open(out / 'labels.jsonl.gz', 'wt') as output:
            for line in file:
                root = json.loads(line)
                if a.smoke_roots and root['mode'] in smoke_modes:
                    continue
                smoke_modes.add(root['mode'])
                assert root['players'] == a.players and root['rootId'] not in seen
                seen.add(root['rootId'])
                old = worker.call({**root['request'], 'featureRevision': protocol['parent_feature_revision']})
                new = worker.call({**root['request'], 'featureRevision': protocol['feature_revision']})
                assert old['moves'] == new['moves'] == root['legal']
                assert new['state'][:1149] == old['state']
                assert [r[:98] for r in new['actions']] == old['actions']
                assert len(new['state']) == protocol['state_dim'] and all(len(r) == protocol['action_dim'] for r in new['actions'])
                features = np.asarray(old['actions'], dtype=np.float32)[None]
                logits, _ = model.session.run(None, {'state': np.asarray(old['state'], dtype=np.float32)[None],
                    'actions': features, 'mask': np.ones(features.shape[:2], dtype=bool)})
                assert np.isfinite(logits).all() and int(logits[0].argmax()) == root['model_proposal']
                search_protocol = {**protocol, 'model': {**pin, 'feature_revision': protocol['parent_feature_revision']},
                    'seed_template': protocol['seed_prefix'] + ('-smoke-' if a.smoke_roots else '-') + root['rootId'] + '-{batch}'}
                guidance = audit.search(pool, model, root, protocol['continuation'], 'a', samples, search_protocol)
                caps += guidance['truncated']
                evaluations += guidance['evaluations']
                engine_seconds += guidance['timing']['engine_seconds']
                decisions += 1
                counts[root['mode'], root['split']] += 1
                record = {k: root[k] for k in ['rootId', 'rootIndex', 'players', 'mode', 'episode', 'ordinal',
                    'deal', 'gameSeed', 'split', 'variant', 'sealed', 'round', 'public_root_sha256', 'model_proposal']}
                record.update(featureRevision=protocol['feature_revision'], state=new['state'], actions=new['actions'],
                    legal=root['legal'], parent_logits=logits[0].tolist(), guidance=guidance)
                output.write(json.dumps(record) + '\n')
                if decisions % 100 == 0:
                    output.flush()
                    print({'roots': decisions, 'evaluations': evaluations, 'caps': caps, 'seconds': time.monotonic() - begin}, flush=True)
        if not a.smoke_roots:
            assert decisions == verified['roots']
            assert {m: {s: counts[m, s] for s in ['train', 'validation']} for m in verified['counts']} == verified['counts']
        status.update(roots=decisions, evaluations=evaluations, truncated=caps, engine_seconds=engine_seconds,
            seconds=time.monotonic() - begin, counts={m + '/' + s: n for (m, s), n in sorted(counts.items())})
        assert caps == 0, 'Capped labels preserved but not admitted'
        status['status'] = 'complete'
    except BaseException as error:
        status.update(status='failed', error=type(error).__name__ + ': ' + str(error))
        raise
    finally:
        if worker:
            worker.close()
        if pool:
            pool.close()
        status['artifact_sha256'] = {p.name: digest(p) for p in out.iterdir() if p.is_file()}
        write(out / 'labels-check.json', status)
        if a.upload:
            # Input raw data already has an immutable revision; do not duplicate it.
            HfApi().upload_folder(repo_id=protocol['repo'], folder_path=out,
                path_in_repo=f'runs/discard-training-labels-v1-{a.players}p',
                allow_patterns=['labels.jsonl.gz', 'labels-check.json', 'inputs/verified.json'])
        print(status, flush=True)


if __name__ == '__main__':
    main()
