"""Prepare corrected-runtime pilots; preserve original failed jobs and source.

Only the two diagnosed runtime files differ; model/selection/seed design stays
unchanged. Validate the transport and original saved decisions before HF launch.
"""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys

from public_policy_final_audit_v1 import artifact_identity, digest, read, PROTOCOL_SHA
from public_policy_arena_v1 import PublicPolicyProcess, semantic
from opponent_auction_verification_v1 import verify_decision

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'ai/runs/conservative-auction-runtime-prepared-v2'
OLD = ROOT/'ai/runs/conservative-auction-runtime-prepared-v1'
FIX = ROOT/'ai/runs/conservative-auction-forced-prior-v1'
PROTOCOL = ROOT/'ai/strong/conservative-auction-development-protocol-v2.json'
RECOVERY = ROOT/'ai/strong/conservative-auction-forced-prior-evidence-v1.json'


def write(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False); stream.write('\n')


def prepare():
    assert not OUT.exists() and not PROTOCOL.exists(), 'Preserve any existing preparation'
    recovery, fix = read(RECOVERY), read(FIX/'derivation.json')
    assert recovery['complete'] and recovery['archive']['remote_archive_verified']
    assert recovery['derivation'] == fix and read(FIX/'audit.json')['complete']
    assert recovery['audit_counts']['rollouts'] == 96 and recovery['audit_counts']['rollout_caps'] == 0
    old = read(OLD/'prepared.json'); pins = read(OLD/'source/source-manifest.json')
    assert digest(OLD/'source/source-manifest.json') == old['source_manifest_sha256']
    assert all(digest(OLD/'source'/name) == sha for name, sha in pins.items())
    old_manifest = read(OLD/'source/artifact/manifest.json'); new_manifest = read(FIX/'artifact/manifest.json')
    assert len(new_manifest) == len(old_manifest) == 1502
    assert set(old_manifest) == set(new_manifest)
    assert {name for name in old_manifest if old_manifest[name] != new_manifest[name]} == set(fix['changed_runtime_files'])
    assert digest(FIX/'artifact/manifest.json') == fix['manifest_sha256']
    assert all(digest(FIX/'artifact'/name) == sha for name, sha in new_manifest.items())
    protocol = read(ROOT/'ai/strong/conservative-auction-development-protocol-v1.json')
    assert digest(OLD/'source/experiment-protocol.json') == digest(ROOT/'ai/strong/conservative-auction-development-protocol-v1.json')
    now = datetime.now(timezone.utc).isoformat()
    protocol.update(version=2, created_at=now,
        previous_protocol_sha256=digest(OLD/'source/experiment-protocol.json'),
        recovery_evidence=recovery['archive'], base_runtime_manifest_sha256=fix['manifest_sha256'],
        execution='Use the corrected standalone runtime: only the two forced-prior fixes differ from v1. Preserve weights, settings, seeds, comparisons and final gate.',
        runtime_interpretation='Repeat the same 64 engineering games under new identities; the failed v1 run remains incomplete. Exclude all pilots from strength.')
    for arm in protocol['arms']:
        descriptor = read(FIX/f'artifact/policies/{arm}.json')
        previous = deepcopy(protocol['arms'][arm]); previous['runtime_manifest']['sha256'] = fix['manifest_sha256']
        assert descriptor == previous
        protocol['arms'][arm] = descriptor
    write(PROTOCOL, protocol)
    source = OUT/'source'; source.mkdir(parents=True)
    shutil.copytree(FIX/'artifact', source/'artifact')
    for name in ('public_policy_development_job_v1.py', 'public_policy_measured_job_v1.py'):
        shutil.copyfile(OLD/'source'/name, source/name)
    shutil.copyfile(PROTOCOL, source/'experiment-protocol.json')
    (source/'runtime-controls').mkdir()
    identities = {}
    for arm in protocol['arms']:
        identities[arm] = artifact_identity(source/'artifact', f'policies/{arm}.json')
        write(source/f'runtime-controls/{arm}.candidate.json', {'status': 'engineering', 'frozen_at': now,
            'identity': identities[arm], 'protocol_sha256': PROTOCOL_SHA, 'selection_evidence': None})
    rows = []
    for pilot in [*protocol['runtime_pilots'], {'arm': 'filter', 'players': 2}]:
        arm, n = pilot['arm'], pilot['players']
        name = f'conservative-auction-runtime-v2-{arm}-{n}p'
        shard = {'name': name, 'group': f'search_geo/{n}p', 'players': n, 'start': 0, 'deals': 1,
                 'seed': protocol['runtime_seed_template'].format(players=n), 'opponent': 'search_geo',
                 'opponent_sha256': None, 'games': 4*n}
        filename = name+'.job.json'
        if arm == 'filter':
            # Preserve the existing eight-game portability control, including
            # its already inspected seed/offset; only the artifact identity changes.
            shard = read(OLD/'source/controls/filter-offset-2p.contract.json')['shard']
            filename = 'filter-offset-2p.job.json'
        candidate = f'runtime-controls/{arm}.candidate.json'; contract = f'runtime-controls/{name}.contract.json'
        write(source/contract, {'version': 1, 'purpose': 'engineering', 'created_at': now,
            'candidate_sha256': digest(source/candidate), 'protocol_sha256': PROTOCOL_SHA,
            'identity': identities[arm], 'shard': shard, 'launch_authorization': None})
        write(source/filename, {'version': 1, 'artifact': 'artifact', 'descriptor': f'policies/{arm}.json',
            'candidate': candidate, 'contract': contract, 'workers': 4, 'opponent_model': None})
        rows.append({'name': name, 'arm': arm, 'players': n, 'job': filename, 'shard': shard,
            'execute_pilot': arm != 'filter', 'identity': identities[arm],
            'candidate_sha256': digest(source/candidate), 'contract_sha256': digest(source/contract),
            'job_spec_sha256': digest(source/filename)})
    assert sum(r['shard']['games'] for r in rows if r['execute_pilot']) == 64
    source_pins = {str(p.relative_to(source)): digest(p) for p in sorted(source.rglob('*')) if p.is_file()}
    write(source/'source-manifest.json', source_pins)
    old_check = read(OLD/'verified.json')
    assert old_check['complete'] and old_check['fixtures'] == 72
    assert digest(OLD/'decisions.jsonl') == old_check['decisions_sha256']
    prepared = {'created_at': now, 'rows': rows, 'identities': identities, 'source_files': len(source_pins),
        'source_manifest_sha256': digest(source/'source-manifest.json'), 'protocol_sha256': digest(PROTOCOL),
        'checker_sha256': digest(__file__), 'recovery_evidence_sha256': digest(RECOVERY),
        'recovered_response_sha256': digest(FIX/'response-5-21.json'),
        'original_decisions_sha256': digest(OLD/'decisions.jsonl'),
        'runtime_manifest_sha256': fix['manifest_sha256'], 'changed_runtime_files': fix['changed_runtime_files'],
        'new_hf_jobs': 0, 'grid_admitted': False, 'reserved_final_seeds_used': False}
    write(OUT/'prepared.json', prepared)
    print(json.dumps({'prepared': True, 'source_files': len(source_pins), 'games': 64}), flush=True)


def pinned():
    p = read(OUT/'prepared.json'); source = OUT/'source'
    assert digest(__file__) == p['checker_sha256'] and digest(PROTOCOL) == p['protocol_sha256']
    assert digest(RECOVERY) == p['recovery_evidence_sha256']
    assert digest(source/'source-manifest.json') == p['source_manifest_sha256']
    pins = read(source/'source-manifest.json')
    assert set(pins)|{'source-manifest.json'} == {str(f.relative_to(source)) for f in source.rglob('*') if f.is_file()}
    assert all(digest(source/name) == sha for name, sha in pins.items())
    assert digest(OLD/'decisions.jsonl') == p['original_decisions_sha256']
    assert digest(FIX/'response-5-21.json') == p['recovered_response_sha256']
    return p


def verify():
    prep = pinned(); source = OUT/'source'; artifact = source/'artifact'
    write(OUT/'verification-intent.json', {'started_at': datetime.now(timezone.utc).isoformat(),
        'prepared_sha256': digest(OUT/'prepared.json')})
    for row in prep['rows']:
        command = [sys.executable, '-u', '-B', str(source/'public_policy_development_job_v1.py'),
            '--source', str(source), '--manifest-sha256', prep['source_manifest_sha256'],
            '--job', row['job'], '--output', str(OUT/'dry-output'/row['name'])]
        with (OUT/(row['name']+'.validation.log')).open('x') as log:
            subprocess.run(command, cwd='/tmp', stdout=log, stderr=subprocess.STDOUT, check=True)
        assert not (OUT/'dry-output'/row['name']).exists()
    old_rows = [json.loads(line) for line in (OLD/'decisions.jsonl').read_text().splitlines()]
    assert len(old_rows) == 72
    worker_sha = digest(artifact/'ai/strong/surrogate-opponent-continuations-v1.cjs')
    counts = fixtures = 0
    with (OUT/'decisions.jsonl').open('x') as receipts:
        for arm in prep['identities']:
            with (OUT/(arm+'.stderr.log')).open('x') as stderr:
                process = PublicPolicyProcess(artifact, f'policies/{arm}.json', stderr)
                try:
                    for saved in [r for r in old_rows if r['arm'] == arm]:
                        request = saved['request']; response = process.call(request)
                        assert 'error' not in response and all(response[k] == v for k, v in prep['identities'][arm].items())
                        expected = deepcopy(saved['response']['decision'])
                        if expected['search']:
                            for component in expected['search']['components']: component['worker_sha256'] = worker_sha
                        assert semantic(response['decision']) == semantic(expected), (arm, saved['name'])
                        counts += response['decision']['search']['evaluations'] if response['decision']['search'] else 0
                        receipts.write(json.dumps({'arm': arm, 'name': saved['name'], 'request': request, 'response': response})+'\n')
                        receipts.flush(); fixtures += 1
                        print(json.dumps({'arm': arm, 'fixtures': fixtures}), flush=True)
                finally: process.close()
        request = read(ROOT/'ai/runs/conservative-auction-failure-diagnosis-v1/request-5-21.json')
        with (OUT/'recovered.stderr.log').open('x') as stderr:
            process = PublicPolicyProcess(artifact, 'policies/conservative_dual.json', stderr)
            try: response = process.call(request)
            finally: process.close()
        original = read(FIX/'response-5-21.json')
        assert semantic(response) == semantic(original)
        row = {**response['decision'], 'arenaMoves': read(ROOT/'ai/runs/conservative-auction-failure-diagnosis-v1/observation-5-21.json')['moves']}
        checked = verify_decision(row, {'players': 6, 'arm': 'opponent-auction-v1', 'samples': 8,
            'model_sha256': response['modelSha256'], 'identity': response}, request['player'])
        assert checked['rollouts'] == 96 and checked['rollout_caps'] == 0
        write(OUT/'recovered-response.json', response)
    assert fixtures == 72 and counts == 1992
    pinned()
    result = {'complete': True, 'fixtures': fixtures, 'continuations_exact_to_archived_components': counts,
        'recovered_request_continuations': 96, 'caps': 0, 'prepared_sha256': digest(OUT/'prepared.json'),
        'source_manifest_sha256': prep['source_manifest_sha256'], 'decisions_sha256': digest(OUT/'decisions.jsonl'),
        'new_hf_jobs': 0, 'grid_admitted': False, 'reserved_final_seeds_used': False}
    write(OUT/'verified.json', result); print(json.dumps(result), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__); parser.add_argument('operation', choices=['prepare', 'verify'])
    globals()[parser.parse_args().operation]()
