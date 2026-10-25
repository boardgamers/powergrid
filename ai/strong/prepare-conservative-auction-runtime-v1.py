"""Prepare immutable descriptors and validate saved-continuation equivalence."""
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
from opponent_auction_policy_v1 import select_action
from opponent_auction_verification_v1 import verify_decision

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = ROOT/'ai/strong/conservative-auction-development-protocol-v1.json'
OUT = ROOT/'ai/runs/conservative-auction-runtime-prepared-v1'
BASE = ROOT/'ai/runs/public-policy-development-job-preflight-v1/source'
GOLD = ROOT/'ai/runs/opponent-auction-runtime-preflight-v1'


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')


def prepare():
    assert not OUT.exists(), 'Preserve original source and any partial verification'
    protocol = read(PROTOCOL); design = read(ROOT/'ai/strong/conservative-auction-design-evidence-v1.json')
    assert design['complete'] and design['protocol_sha256'] == digest(PROTOCOL) and design['archive']['remote_archive_verified']
    assert protocol['planned_games_total'] == 10080 and protocol['runtime_pilot_games'] == 64 and not protocol['grid_admitted']
    assert digest(BASE/'source-manifest.json') == protocol['portable_source']['source_manifest_sha256']
    base_pins = read(BASE/'source-manifest.json')
    assert all(digest(BASE/name) == sha for name, sha in base_pins.items())
    source = OUT/'source'; source.parent.mkdir(); shutil.copytree(BASE, source)
    artifact = source/'artifact'; assert digest(artifact/'manifest.json') == protocol['base_runtime_manifest_sha256']
    shutil.copyfile(PROTOCOL, source/'experiment-protocol.json')
    shutil.copyfile(ROOT/'ai/strong/public_policy_measured_job_v1.py', source/'public_policy_measured_job_v1.py')
    (artifact/'policies').mkdir(); (source/'runtime-controls').mkdir()
    identities = {}; now = datetime.now(timezone.utc).isoformat()
    for arm, descriptor in protocol['arms'].items():
        filename = f'policies/{arm}.json'; write(artifact/filename, descriptor)
        identities[arm] = artifact_identity(artifact, filename)
        write(source/f'runtime-controls/{arm}.candidate.json', {'status': 'engineering', 'frozen_at': now,
              'identity': identities[arm], 'protocol_sha256': PROTOCOL_SHA, 'selection_evidence': None})
    rows = []
    pilots = [*protocol['runtime_pilots'], {'arm': 'filter', 'players': 2, 'opponent': 'search_geo', 'games': 8, 'deals': 1}]
    for i, pilot in enumerate(pilots):
        arm, n = pilot['arm'], pilot['players']; name = f'conservative-auction-runtime-v1-{arm}-{n}p'
        shard = {'name': name, 'group': f'search_geo/{n}p', 'players': n, 'start': 0, 'deals': 1,
                 'seed': protocol['runtime_seed_template'].format(players=n), 'opponent': 'search_geo',
                 'opponent_sha256': None, 'games': 4*n}
        candidate = f'runtime-controls/{arm}.candidate.json'; contract = f'runtime-controls/{name}.contract.json'
        write(source/contract, {'version': 1, 'purpose': 'engineering', 'created_at': now,
              'candidate_sha256': digest(source/candidate), 'protocol_sha256': PROTOCOL_SHA,
              'identity': identities[arm], 'shard': shard, 'launch_authorization': None})
        filename = name+'.job.json'
        write(source/filename, {'version': 1, 'artifact': 'artifact', 'descriptor': f'policies/{arm}.json',
              'candidate': candidate, 'contract': contract, 'workers': 4, 'opponent_model': None})
        rows.append({'name': name, 'arm': arm, 'players': n, 'job': filename, 'shard': shard,
                     'execute_pilot': i < len(protocol['runtime_pilots']), 'identity': identities[arm],
                     'candidate_sha256': digest(source/candidate), 'contract_sha256': digest(source/contract),
                     'job_spec_sha256': digest(source/filename)})
    assert sum(r['shard']['games'] for r in rows if r['execute_pilot']) == 64
    for name, sha in base_pins.items(): assert digest(source/name) == sha
    pins = {str(p.relative_to(source)): digest(p) for p in sorted(source.rglob('*'))
            if p.is_file() and p != source/'source-manifest.json'}
    write(source/'source-manifest.json', pins)
    gold_manifest = ROOT/'ai/runs/opponent-auction-runtime-evidence-v1/manifest.json'
    gold_proof = read(ROOT/'ai/strong/opponent-auction-runtime-preflight-v1.json')
    assert digest(gold_manifest) == gold_proof['archive']['manifest_sha256']
    gold_hash = read(gold_manifest)[str((GOLD/'decisions.jsonl').relative_to(ROOT))]
    assert digest(GOLD/'decisions.jsonl') == gold_hash
    write(OUT/'prepared.json', {'prepared_at': now, 'protocol_sha256': digest(PROTOCOL), 'rows': rows,
          'identities': identities, 'unchanged_base_files': len(base_pins),
          'base_source': protocol['portable_source'], 'runtime_manifest_sha256': digest(artifact/'manifest.json'),
          'source_manifest_sha256': digest(source/'source-manifest.json'), 'source_files': len(pins),
          'gold_decisions_sha256': gold_hash, 'gold_archive': gold_proof['archive'],
          'checker_sha256': digest(__file__), 'measured_entry_sha256': digest(source/'public_policy_measured_job_v1.py'),
          'new_hf_jobs': 0, 'reserved_final_seeds_used': False})
    print(json.dumps({'prepared': True, 'source_files': len(pins), 'runtime_pilot_games': 64}), flush=True)


def pinned():
    prepared = read(OUT/'prepared.json'); source = OUT/'source'
    assert prepared['protocol_sha256'] == digest(PROTOCOL) and prepared['checker_sha256'] == digest(__file__)
    assert prepared['measured_entry_sha256'] == digest(ROOT/'ai/strong/public_policy_measured_job_v1.py')
    assert digest(source/'source-manifest.json') == prepared['source_manifest_sha256']
    assert all(digest(source/name) == sha for name, sha in read(source/'source-manifest.json').items())
    assert digest(GOLD/'decisions.jsonl') == prepared['gold_decisions_sha256']
    return prepared


def expected_single(old, seat):
    result = deepcopy(old); search = result['search']
    if search is None: return result
    components = [c for c in search['components'] if c['mode'] == 'neural_population']
    selection = select_action(components, search['options'], result['modelProposal'], seat,
                              modes=['neural_population'], minimum_advantage='1/8')
    search.update(components=components, selection=selection,
                  evaluations=sum(len(c['rows']) for c in components),
                  neuralDecisions=sum(c['inference_decisions']['neural'] for c in components),
                  surrogateDecisions=0)
    result['index'] = selection['selected']
    return result


def verify():
    prep = pinned(); source = OUT/'source'; artifact = source/'artifact'
    assert not (OUT/'verification-state.json').exists(), 'Inspect the original verifier before any retry'
    write(OUT/'verification-state.json', {'stage': 'running', 'started_at': datetime.now(timezone.utc).isoformat()})
    completed = []; continuations = fixtures = 0
    try:
        for row in prep['rows']:
            command = [sys.executable, '-u', '-B', str(source/'public_policy_development_job_v1.py'),
                       '--source', str(source), '--manifest-sha256', prep['source_manifest_sha256'],
                       '--job', row['job'], '--output', str(OUT/'dry-output'/row['name'])]
            with (OUT/(row['name']+'.validation.log')).open('x') as log:
                subprocess.run(command, cwd='/tmp', stdout=log, stderr=subprocess.STDOUT, check=True)
            assert not (OUT/'dry-output'/row['name']).exists(); completed.append(row['name'])
        old_rows = [json.loads(line) for line in (GOLD/'decisions.jsonl').read_text().splitlines()]
        assert len(old_rows) == 24
        with (OUT/'decisions.jsonl').open('x') as receipts:
            for arm in ('filter', 'conservative_population', 'conservative_dual'):
                identity = prep['identities'][arm]
                with (OUT/(arm+'.stderr.log')).open('x') as stderr:
                    process = PublicPolicyProcess(artifact, f'policies/{arm}.json', stderr)
                    try:
                        for saved in old_rows:
                            q = saved['request']; response = process.call(q); assert 'error' not in response
                            assert all(response[k] == v for k, v in identity.items())
                            old = saved['response']['decision']; row = response['decision']
                            assert response['requestId'] == q['requestId'] and response['revision'] == q['revision']
                            if arm == 'filter':
                                index = old['search']['selection']['baseline'] if old['search'] else old['index']
                                assert row['index'] == index and row['search'] is None and row['arm'] == 'filter'
                                assert row['modelProposal'] == old['modelProposal']
                            else:
                                expected = expected_single(old, q['player']) if arm == 'conservative_population' else deepcopy(old)
                                moves = read(artifact/'ai/strong/fixtures/surrogate-continuation-runtime-roots-v1.json')['roots'][saved['name']]['moves']
                                expected['move'] = moves[expected['index']]
                                assert semantic(row) == semantic(expected), (arm, saved['name'])
                                checked = verify_decision({**row, 'arenaMoves': moves},
                                    {'players': len(q['state']['players']), 'arm': 'opponent-auction-v1', 'samples': 8,
                                     'model_sha256': identity['modelSha256'], 'identity': identity}, q['player'])
                                assert checked['rollout_caps'] == 0; continuations += checked['rollouts']
                            receipts.write(json.dumps({'arm': arm, 'name': saved['name'], 'request': q, 'response': response})+'\n')
                            receipts.flush(); fixtures += 1
                            print(json.dumps({'arm': arm, 'fixture': saved['name'], 'complete': fixtures}), flush=True)
                    finally: process.close()
        assert fixtures == 72 and continuations == 1992
        pinned()
        result = {'complete': True, 'dry_validations': completed, 'fixtures': fixtures,
                  'continuations_exact_to_archived_components': continuations, 'caps': 0,
                  'source_manifest_sha256': prep['source_manifest_sha256'], 'protocol_sha256': prep['protocol_sha256'],
                  'prepared_sha256': digest(OUT/'prepared.json'), 'decisions_sha256': digest(OUT/'decisions.jsonl'),
                  'unchanged_base_files': prep['unchanged_base_files'], 'new_hf_jobs': 0,
                  'reserved_final_seeds_used': False}
        write(OUT/'verified.json', result); write(OUT/'verification-state.json', {'stage': 'complete', **result})
        print(json.dumps(result), flush=True)
    except BaseException as error:
        write(OUT/'verification-state.json', {'stage': 'stopped_for_inspection', 'failure_type': type(error).__name__})
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__); parser.add_argument('operation', choices=['prepare', 'verify'])
    globals()[parser.parse_args().operation]()
