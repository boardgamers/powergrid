"""Check portable development execution using unchanged existing artifacts."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys

from public_policy_development_job_v1 import digest, read, write, ENTRY, MANIFEST
from public_policy_final_audit_v1 import audit_shard
from public_policy_final_contract_v1 import audit_execution_binding
from public_policy_arena_v1 import semantic, arena_semantic

ROOT = Path(__file__).resolve().parents[2]
GOLD = ROOT/'ai/runs/public-policy-final-runner-preflight-v1'
OUT = ROOT/'ai/runs/public-policy-development-job-preflight-v1'


def prepare():
    assert not OUT.exists(), 'Preserve existing preflight and original execution'
    source = OUT/'source'; source.mkdir(parents=True)
    prepared = read(GOLD/'prepared.json'); proof = read(GOLD/'result.json')
    assert proof['complete'] and proof['prepared_sha256'] == digest(GOLD/'prepared.json')
    package = source/'artifact'; shutil.copytree(GOLD/'package', package)
    assert digest(package/'manifest.json') == prepared['runtime_manifest_sha256']
    assert all(digest(package/name) == sha for name, sha in read(package/'manifest.json').items())
    shutil.copytree(GOLD/'controls', source/'controls')
    shutil.copyfile(ROOT/'ai/strong'/ENTRY, source/ENTRY)
    cases = []
    for case in prepared['cases']:
        name = case['name']; filename = name+'.job.json'
        write(source/filename, {'version': 1, 'artifact': 'artifact', 'descriptor': case['descriptor'],
              'candidate': 'controls/'+case['descriptor']+'.candidate.json',
              'contract': 'controls/'+name+'.contract.json', 'workers': 4,
              'opponent_model': 'artifact/final-opponent-a260.onnx' if case['opponent'] == 'a260' else None})
        cases.append({'name': name, 'file': filename, 'shard': case['shard'], 'descriptor': case['descriptor']})
    pins = {str(p.relative_to(source)): digest(p) for p in source.rglob('*') if p.is_file()}
    write(source/MANIFEST, pins)
    write(OUT/'prepared.json', {'prepared_at': datetime.now(timezone.utc).isoformat(),
          'source_manifest_sha256': digest(source/MANIFEST), 'cases': cases,
          'original_prepared_sha256': digest(GOLD/'prepared.json'),
          'original_proof_sha256': digest(GOLD/'result.json'),
          'original_runtime_manifest_sha256': prepared['runtime_manifest_sha256'],
          'identities': prepared['identities'], 'source_files': len(pins),
          'entry_sha256': digest(source/ENTRY), 'new_hf_jobs': 0, 'reserved_final_seeds_used': False})
    print(json.dumps({'prepared': True, 'source_files': len(pins), 'runtime_unchanged': True}), flush=True)


def pinned():
    prep = read(OUT/'prepared.json'); source = OUT/'source'
    assert digest(source/MANIFEST) == prep['source_manifest_sha256']
    assert all(digest(source/name) == sha for name, sha in read(source/MANIFEST).items())
    assert digest(ROOT/'ai/strong'/ENTRY) == prep['entry_sha256']
    assert digest(GOLD/'prepared.json') == prep['original_prepared_sha256']
    assert digest(GOLD/'result.json') == prep['original_proof_sha256']
    return prep


def run():
    prep = pinned(); source = OUT/'source'
    assert not (OUT/'state.json').exists(), 'Inspect the original execution, never replace it'
    state = {'stage': 'validating', 'started_at': datetime.now(timezone.utc).isoformat(), 'validated': []}
    write(OUT/'state.json', state)
    try:
        for case in prep['cases']:
            command = [sys.executable, '-u', '-B', str(source/ENTRY), '--source', str(source),
                       '--manifest-sha256', prep['source_manifest_sha256'], '--job', case['file'],
                       '--output', str(OUT/case['name'])]
            with (OUT/(case['name']+'.validation.log')).open('x') as log:
                subprocess.run(command, cwd='/tmp', stdout=log, stderr=subprocess.STDOUT, check=True)
            assert not (OUT/case['name']).exists()
            state['validated'].append(case['name']); write(OUT/'state.json', state)
            if case['name'] == 'filter-offset-2p': execution_command = command
        state.update(stage='executing-filter-offset-2p'); write(OUT/'state.json', state)
        with (OUT/'execution.log').open('x') as log:
            subprocess.run([*execution_command, '--execute'], cwd='/tmp', stdout=log, stderr=subprocess.STDOUT, check=True)
        pinned(); state.update(stage='complete', finished_at=datetime.now(timezone.utc).isoformat())
        write(OUT/'state.json', state)
    except BaseException as error:
        state.update(stage='stopped_for_inspection', failure_type=type(error).__name__)
        write(OUT/'state.json', state); raise
    print(json.dumps(state), flush=True)


def verify():
    prep = pinned(); assert read(OUT/'state.json')['stage'] == 'complete'
    assert not (OUT/'result.json').exists(), 'Preserve original verification'
    case = next(c for c in prep['cases'] if c['name'] == 'filter-offset-2p')
    directory = OUT/case['name']; target = directory/'evaluation'; gold = GOLD/case['name']
    status = read(directory/'job-status.json'); identity = prep['identities'][case['descriptor']]
    assert status['stage'] == 'complete' and status['games'] == 8
    assert status['provenance']['identity'] == identity
    assert status['provenance']['source_manifest_sha256'] == prep['source_manifest_sha256']
    assert status['provenance']['entry_sha256'] == prep['entry_sha256']
    assert all(digest(directory/name) == sha for name, sha in read(directory/'manifest.json').items())
    audit = audit_shard(target, case['shard'], identity, reserved=False)
    binding = audit_execution_binding(target, identity, digest(OUT/'source/artifact/ai/strong/public_policy_final_runner_v1.py'))
    assert read(target/'audit.json') == {**audit, 'execution_binding': binding}
    current, original = read(target/'evaluation.json'), read(gold/'evaluation.json')
    decisions = 0
    for a, b in zip(current['results'], original['results'], strict=True):
        assert a['episode'] == b['episode'] and a['terminal'] == b['terminal']
        episode = a['episode']; count = 0
        with (target/f'decisions-{episode}.jsonl').open() as left, (gold/f'decisions-{episode}.jsonl').open() as right:
            for x, y in zip(left, right, strict=True):
                x, y = json.loads(x), json.loads(y)
                request = lambda row: arena_semantic({'observations': [{'request': row['publicRequest']}], 'ended': []})
                assert request(x) == request(y)
                assert semantic(x['publicResponse']['decision']) == semantic(y['publicResponse']['decision'])
                assert x['arenaMoves'] == y['arenaMoves'] and x['arenaPlayerOrder'] == y['arenaPlayerOrder']
                count += 1
        assert count == a['decisions'] == b['decisions']; decisions += count
    result = {'complete': True, 'games': 8, 'decisions': decisions, 'all_public_decisions_and_terminals_exact': True,
              'runtime_manifest_unchanged': True, 'source_manifest_sha256': prep['source_manifest_sha256'],
              'validated_cases': read(OUT/'state.json')['validated'], 'prepared_sha256': digest(OUT/'prepared.json'),
              'audit': audit, 'new_hf_jobs': 0, 'gradient_updates': 0, 'reserved_final_seeds_used': False,
              'qualification_eligible': False,
              'scope': 'Local clean-source development wrapper execution; not HF portability, new strength or target latency.'}
    write(OUT/'result.json', result)
    print(json.dumps({k: result[k] for k in ('complete', 'games', 'decisions', 'runtime_manifest_unchanged')}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__); parser.add_argument('operation', choices=['prepare', 'run', 'verify'])
    globals()[parser.parse_args().operation]()
