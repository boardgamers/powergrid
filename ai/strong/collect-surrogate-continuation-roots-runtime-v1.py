"""Collect original root-calibration handles and independently recheck selected roots."""
import argparse
import ast
from datetime import datetime, timezone
import importlib.util
import json
import math
from pathlib import Path
import re

from huggingface_hub import HfApi, hf_hub_download
from strategic_collection import ROOT, read, write, digest
from population_policy_verification import extract_verified
from hybrid_search import Model
from population_hybrid_policy import PopulationPolicy
from surrogate_continuation_roots_v1 import contract, verify_game

STRONG = ROOT/'ai/strong'
spec = importlib.util.spec_from_file_location('root_runtime_launcher', STRONG/'launch-surrogate-continuation-roots-runtime-v1.py')
launcher = importlib.util.module_from_spec(spec); spec.loader.exec_module(launcher)
COLLECTED = ROOT/'ai/runs/surrogate-continuation-roots-runtime-collected-v1'
RUNTIME = ROOT/'ai/runs/surrogate-continuation-roots-source-prepared-v1/layout'
MODEL = ROOT/'ai/runs/policy-iteration-trained-8840u-prepared-v2/local-package-frozen-1/policy.onnx'


def review_artifacts(folder, evidence, source, players):
    manifest = read(folder/'manifest.json')
    assert set(manifest) | {'manifest.json'} == {str(p.relative_to(folder)) for p in folder.rglob('*') if p.is_file()}
    assert digest(folder/'manifest.json') == evidence['manifest_sha256'] and len(manifest)+1 == evidence['archived_files']
    assert all(digest(folder/name) == sha for name, sha in manifest.items())
    job = read(folder/'job.json'); state = read(folder/'games/status.json'); intent = read(folder/'games/intent.json')
    assert job['stage'] == state['stage'] == 'complete' and intent['stage'] == 'running'
    assert not state['errors'] and intent['errors'] == [] and intent['cases'] == {}
    assert job['case'] == f'surrogate-continuation-runtime-v1-{players}p-0-1'
    assert (job['players'], job['start'], job['end'], job['mode']) == (players, 0, 1, 'runtime')
    assert job['source_revision'] == source['revision'] and job['source_sha256'] == source['sha256']
    assert job['source_manifest_sha256'] == source['manifest_sha256']
    assert job['job_runner_sha256'] == source['new_files']['ai/strong/surrogate-continuation-roots-job-v1.py']
    for row in (job, state, intent):
        assert row['protocol_sha256'] == source['protocol_sha256']
        assert all(row[k] is False for k in ('gradients', 'qualification_eligible', 'reserved_final_seeds_used'))
    assert job['automatic_retries'] is False and job['caps'] == 0
    assert state['tasks'] == intent['tasks'] and len(state['tasks']) == players*4
    assert state['runner_sha256'] == intent['runner_sha256'] == source['new_files']['ai/strong/surrogate_continuation_roots_v1.py']
    expected = {str(i): contract(players, 0, i//4, i % 4, 'runtime') for i in range(players*4)}
    assert set(state['cases']) == set(expected)
    assert {(task['deal'], task['seat'], task['rule']) for task in state['tasks']} == {(0, seat, rule) for seat in range(players) for rule in range(4)}
    assert all(task['players'] == players and task['mode'] == 'runtime' and task['twin'] is True for task in state['tasks'])
    assert digest(RUNTIME/'surrogate-continuation-roots-source-manifest.json') == source['manifest_sha256']
    assert all(digest(RUNTIME/name) == sha for name, sha in read(RUNTIME/'surrogate-continuation-roots-source-manifest.json').items())
    model = Model(MODEL, threads=1); assert model.sha256 == read(launcher.PROTOCOL)['focal_model_sha256']
    policy = PopulationPolicy(model, RUNTIME/'ai/strong/population-hybrid-policy.cjs', arm='filter')
    checks = {}; counts = {'eligible_decisions': 0, 'selected_roots': 0}
    try:
        for episode, q in expected.items():
            path = folder/'games'/f'game-{episode}'; result = read(path/'verified.json')
            assert result == state['cases'][episode] and read(path/'contract.json') == q and result['twin_exact'] is True
            checks[episode] = verify_game(path, policy)
            for name in counts: counts[name] += checks[episode][name]
    finally: policy.close()
    assert read(folder/'root-audit.json') == checks
    assert job['games'] == job['twin_games'] == len(checks) == players*4
    assert job['selected_roots'] == state['selected_roots'] == counts['selected_roots']
    assert job['eligible_decisions'] == counts['eligible_decisions']
    for key in ('seconds', 'cpu_seconds', 'sampled_peak_total_rss_bytes', 'memory_samples'):
        value = job['runtime'][key]; assert type(value) in (int, float) and math.isfinite(value) and value > 0
    return {'complete': True, 'games': len(checks), 'twin_games': len(checks), **counts, 'caps': 0,
            'missing_phases': {episode: check['missing_phases'] for episode, check in checks.items() if check['missing_phases']},
            'runtime': job['runtime'], 'raw_evidence_bytes': sum(p.stat().st_size for p in folder.rglob('*') if p.is_file()),
            'local_root_checks': checks, 'training_eligible': False, 'qualification_eligible': False}


def collect(players):
    assert type(players) is int and players in (2, 6)
    source, _, _ = launcher.prerequisites(); case = f'surrogate-continuation-runtime-v1-{players}p-0-1'
    guard_path = launcher.GUARDS/(case+'.json'); guard = read(guard_path)
    assert guard['stage'] == 'launched' and guard['case'] == case and guard['players'] == players
    assert guard['source'] == source and guard['plan_sha256'] == digest(launcher.PLAN)
    assert re.fullmatch('[a-f0-9]{24}', guard['job_id'])
    code = {str(p.relative_to(ROOT)): digest(p) for p in [Path(__file__), STRONG/'surrogate_continuation_roots_v1.py',
             STRONG/'population_policy_verification.py', STRONG/'population_hybrid_policy.py']}
    api = HfApi(); info = api.inspect_job(job_id=guard['job_id'])
    status = {'case': case, 'job_id': guard['job_id'], 'authoritative_status': info.status.stage,
              'checked_at': datetime.now(timezone.utc).isoformat(), 'guard_sha256': digest(guard_path)}
    folder = COLLECTED/case; folder.mkdir(parents=True, exist_ok=True); write(folder/'status.json', status)
    if info.status.stage != 'COMPLETED': return status
    log = '\n'.join(str(line) for line in api.fetch_job_logs(job_id=guard['job_id'], follow=False))
    (folder/'job.log').write_text(log); receipts = []
    for line in log.splitlines():
        if not line.startswith('{'): continue
        try: row = ast.literal_eval(line)
        except (ValueError, SyntaxError): continue
        if isinstance(row, dict) and row.get('status', {}).get('case') == case and 'evidence' in row: receipts.append(row)
    assert len(receipts) == 1, 'Missing or ambiguous original upload receipt; inspect without resubmitting'
    receipt = receipts[0]; evidence = receipt['evidence']
    assert evidence['repo'] == 'coyotte508/powergrid-ai-germany-v1' and evidence['archive_path'] == f'archives/{case}.tgz'
    assert evidence['remote_archive_verified'] is True and evidence['format'] == 'tar.gz'
    assert re.fullmatch('[a-f0-9]{40}', evidence['revision'])
    archive = Path(hf_hub_download(evidence['repo'], evidence['archive_path'], revision=evidence['revision']))
    assert digest(archive) == evidence['archive_sha256']; artifacts = folder/'artifacts'
    if not artifacts.exists(): extract_verified(archive, artifacts)
    assert read(artifacts/'job.json') == receipt['status']
    review = review_artifacts(artifacts, evidence, source, players)
    assert all(digest(ROOT/name) == sha for name, sha in code.items())
    verified = {**status, 'verified': True, 'source': source, 'protocol_sha256': digest(launcher.PROTOCOL),
                'plan_sha256': digest(launcher.PLAN), 'evidence': evidence, 'review': review, 'collector_code_hashes': code,
                'gradients': False, 'qualification_eligible': False, 'reserved_final_seeds_used': False}
    write(folder/'verified.json', verified); return verified


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__); parser.add_argument('players', type=int, choices=[2, 6]); args = parser.parse_args()
    result = collect(args.players)
    print(json.dumps({key: result[key] for key in ('case', 'job_id', 'authoritative_status', 'verified') if key in result}))
    if result.get('verified'):
        print(json.dumps({key: value for key, value in result['review'].items() if key != 'local_root_checks'}))
