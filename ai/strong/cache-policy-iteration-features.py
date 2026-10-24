"""Cache all selected public inputs before labels finish; no gradient training."""
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile
import time

import numpy as np
from huggingface_hub import hf_hub_download
from strategic_collection import ROOT, read, write, digest, request_hash, get_model


def main():
    p = read(ROOT/'ai/strong/policy-iteration-labels-protocol-v2.json')
    source = read(ROOT/'ai/strong/policy-iteration-labels-source-v2.json')
    assert source['protocol_sha256'] == digest(ROOT/'ai/strong/policy-iteration-labels-protocol-v2.json')
    runtime = ROOT/'ai/runs/policy-iteration-labels-source-v2'
    archive = hf_hub_download('coyotte508/powergrid-ai-training-v1', source['archive'], repo_type='dataset', revision=source['revision'])
    assert digest(archive) == source['sha256']
    with tarfile.open(archive) as bundle:
        for member in bundle.getmembers():
            if member.isfile():
                assert digest(runtime/member.name) == hashlib.sha256(bundle.extractfile(member).read()).hexdigest()
    selected = ROOT/'ai/runs/policy-iteration-selected-v2'
    pin = read(ROOT/'ai/strong/policy-iteration-selected-roots-v2.json')
    assert digest(selected/'selected-index.json') == pin['files']['selected-index.json']
    index = read(selected/'selected-index.json')
    assert len(index) == 17280 and len({r['rootId'] for r in index}) == 17280
    assert Counter(r['split'] for r in index) == {'train': 12960, 'validation': 4320}
    slots = {r['rootId']: i for i, r in enumerate(index)}
    assert len({r['policy_input_sha256'] for r in index}) == len({r['public_root_sha256'] for r in index}) == len(index)
    pilot = read(ROOT/'ai/strong/policy-iteration-teacher-pilot-results-v2.json')
    assert digest(ROOT/'ai/strong/policy-iteration-teacher-pilot-results-v2.json') == p['pilot_results_sha256']
    pilot_options = {}
    for case in pilot['cases'].values():
        for rid, options in case['options_by_root'].items():
            if rid in pilot_options:
                assert pilot_options[rid] == options
            else:
                pilot_options[rid] = options
    assert len(pilot_options) == 360
    inputs = {'state': np.zeros((17280, 1217), np.float32),
              'actions': np.zeros((17280, 7, 101), np.float32),
              'mask': np.zeros((17280, 7), bool),
              'proposal_index': np.zeros(17280, np.int64),
              'legal_indices': np.full((17280, 7), -1, np.int64)}
    metadata = [None]*17280
    model = get_model(p)
    worker = ROOT/'ai/strong/policy-iteration-feature-cache.cjs'
    proc = subprocess.Popen(['node', str(worker), str(runtime)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    roots_file = runtime/p['roots']['file']
    assert digest(roots_file) == p['roots']['sha256']
    out = ROOT/'ai/runs/policy-iteration-features-v2'
    out.mkdir(exist_ok=False)
    count = 0
    started = time.monotonic()
    try:
        with gzip.open(roots_file, 'rt') as f:
            while True:
                batch = []
                for _ in range(32):
                    line = f.readline()
                    if not line:
                        break
                    batch.append(json.loads(line))
                if not batch:
                    break
                proc.stdin.write(json.dumps([{k: r[k] for k in ['rootId', 'request', 'legal']} for r in batch]) + '\n')
                proc.stdin.flush()
                answers = json.loads(proc.stdout.readline())
                assert len(answers) == len(batch)
                for root, answer in zip(batch, answers):
                    rid = root['rootId']
                    i = slots[rid]
                    assert metadata[i] is None and answer['rootId'] == rid
                    assert answer['policy_input_sha256'] == index[i]['policy_input_sha256']
                    assert request_hash(root['request']) == root['public_root_sha256'] == index[i]['public_root_sha256']
                    assert all(root[k] == v for k, v in index[i].items() if k in root)
                    row = answer['row']
                    assert row['moves'] == root['legal']
                    proposal = model.predict(row['state'][:1216], [a[:100] for a in row['actions']])[0]
                    assert proposal == root['model_proposal']
                    options = sorted({j for j, a in enumerate(row['actions']) if a[100] == 1} | {proposal})
                    assert 2 <= len(options) <= 7
                    if rid in pilot_options:
                        assert options == sorted(pilot_options[rid])
                    n = len(options)
                    inputs['state'][i] = row['state']
                    inputs['actions'][i, :n] = [row['actions'][j] for j in options]
                    inputs['mask'][i, :n] = True
                    inputs['proposal_index'][i] = options.index(proposal)
                    inputs['legal_indices'][i, :n] = options
                    metadata[i] = {**index[i], 'model_proposal': proposal, 'options': options,
                                   'full_legal_count': len(root['legal'])}
                    count += 1
                if count % 1024 == 0:
                    print({'encoded': count, 'seconds': time.monotonic() - started}, flush=True)
    finally:
        proc.stdin.close()
        proc.wait(timeout=10)
        proc.stdout.close()
        assert proc.returncode == 0
    assert count == 17280 and all(r is not None for r in metadata)
    assert np.isfinite(inputs['state']).all() and np.isfinite(inputs['actions']).all()
    assert inputs['mask'][np.arange(count), inputs['proposal_index']].all()
    assert (inputs['state'][:, -1] == 1).all()
    np.savez_compressed(out/'features.npz', **inputs)
    write(out/'metadata.json', metadata)
    report = {'complete': True, 'positions': count, 'split_counts': dict(Counter(r['split'] for r in index)),
              'runtime_source': source, 'selected_roots': pin, 'label_protocol_sha256': digest(ROOT/'ai/strong/policy-iteration-labels-protocol-v2.json'),
              'feature_revision': '4.3-strategic-correction', 'state_dim': 1217, 'action_dim': 101,
              'parent_proposals_reproduced': count, 'full_menu_input_hashes_matched': count,
              'old_prefixes_equal': count, 'pilot_option_sets_matched': 360,
              'global_public_and_input_duplicates': 0, 'seconds': time.monotonic() - started,
              'code': {str(file.relative_to(ROOT)): digest(file) for file in [Path(__file__), worker, ROOT/'ai/strong/policy-iteration-input-hashes.cjs']},
              'artifacts': {file.name: digest(file) for file in out.iterdir()}, 'gradients': False, 'qualification_eligible': False}
    write(out/'feature-check.json', report)
    write(ROOT/'ai/strong/policy-iteration-feature-cache-results-v2.json', report)
    print({'complete': True, 'positions': count, 'seconds': report['seconds']}, flush=True)


if __name__ == '__main__':
    main()
