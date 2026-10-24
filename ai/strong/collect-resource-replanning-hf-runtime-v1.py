"""Collect existing HF calibration jobs and prove exact local/HF policy parity.

This cannot submit jobs or infer playing strength from the runtime-only deals.
"""
import argparse
import ast
import contextlib
from datetime import datetime, timezone
import hashlib
import importlib.util
import io
from itertools import zip_longest
import json
from pathlib import Path
import re

import numpy as np
from huggingface_hub import HfApi, hf_hub_download
from strategic_collection import ROOT, read, write, digest
from population_policy_verification import extract_verified, finite, integer
from resource_policy_verification_v1 import verify_evaluation

STRONG = ROOT / 'ai/strong'
spec = importlib.util.spec_from_file_location('resource_runtime_launcher',
    STRONG / 'launch-resource-replanning-runtime-v1.py')
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)
COLLECTED = ROOT / 'ai/runs/resource-replanning-hf-runtime-collected-v1'
LOCAL_EVIDENCE = ROOT / 'ai/runs/resource-replanning-runtime-evidence-v1'
LOCAL_RESULTS = LOCAL_EVIDENCE / 'ai/runs/resource-replanning-runtime-source-prepared-v1/layout/ai/runs/resource-replanning-runtime-v1'


def normalized_decision(row):
    """Exclude only the two known latency fields; retain every policy datum."""
    clean = dict(row)
    finite(clean.pop('elapsedMs'))
    if clean.get('resourcePlan') is not None:
        clean['resourcePlan'] = dict(clean['resourcePlan'])
        finite(clean['resourcePlan'].pop('elapsedMs'))
    return clean


def paired_parity(local, remote):
    """Compare two independently verified evaluations, retaining raw hashes."""
    local, remote = Path(local), Path(remote)
    left, right = read(local / 'evaluation.json'), read(remote / 'evaluation.json')
    def without(data, keys):
        return {key: value for key, value in data.items() if key not in keys}
    assert without(left['config'], {'model', 'runtime', 'output'}) == without(right['config'], {'model', 'runtime', 'output'})
    assert without(left, {'config', 'results', 'seconds'}) == without(right, {'config', 'results', 'seconds'})
    a = {row['episode']: row for row in left['results']}
    b = {row['episode']: row for row in right['results']}
    assert len(a) == len(left['results']) == len(b) == len(right['results']) and set(a) == set(b)
    games, decisions, resources, rollouts = [], 0, 0, 0
    for episode in sorted(a):
        assert without(a[episode], {'seconds', 'decision_receipt_sha256'}) == without(b[episode], {'seconds', 'decision_receipt_sha256'}), f'Game {episode} differs'
        fingerprint, rows = hashlib.sha256(), 0
        lp, rp = local / f'decisions-{episode}.jsonl', remote / f'decisions-{episode}.jsonl'
        assert digest(lp) == a[episode]['decision_receipt_sha256']
        assert digest(rp) == b[episode]['decision_receipt_sha256']
        with lp.open() as ls, rp.open() as rs:
            for lline, rline in zip_longest(ls, rs):
                assert lline is not None and rline is not None, f'Game {episode} receipt length differs'
                lrow, rrow = normalized_decision(json.loads(lline)), normalized_decision(json.loads(rline))
                assert lrow == rrow, f'Game {episode} decision {rows + 1} differs'
                fingerprint.update(json.dumps(lrow, sort_keys=True, separators=(',', ':'), allow_nan=False).encode())
                fingerprint.update(b'\n')
                rows += 1
                if lrow.get('resourcePlan') is not None:
                    resources += 1
                    rollouts += lrow['search']['evaluations']
        assert rows == a[episode]['decisions']
        decisions += rows
        games.append({'episode': episode, 'decisions': rows, 'normalized_decisions_sha256': fingerprint.hexdigest(),
                      'local_receipt_sha256': digest(lp), 'hf_receipt_sha256': digest(rp)})
    return {'exact': True, 'games': len(games), 'learner_decisions': decisions,
            'resource_decisions': resources, 'resource_rollouts': rollouts, 'per_game': games,
            'local_report_sha256': digest(local / 'evaluation.json'),
            'hf_report_sha256': digest(remote / 'evaluation.json'),
            'excluded_fields': ['config.model', 'config.runtime', 'config.output', 'report.seconds',
                                'game.seconds', 'game.decision_receipt_sha256 (checked separately)',
                                'decision.elapsedMs', 'decision.resourcePlan.elapsedMs'],
            'scope': 'Exact recorded choices, world draws, every resource continuation receipt and actual-game terminals across hosts. No new engine replay of every simulated trajectory.'}


def identity(players):
    # Reuse the complete admission validation, always in its read-only mode.
    with contextlib.redirect_stdout(io.StringIO()):
        launcher.launch(players, False)
    case = f'resource-replanning-hf-runtime-v1-{players}p-resource-filter'
    guard_path = launcher.GUARDS / (case + '.json')
    guard = read(guard_path)
    assert guard['stage'] == 'launched' and guard['case'] == case and guard['players'] == players
    assert guard['admission'] == read(launcher.ADMISSION)
    assert guard['admission_sha256'] == digest(launcher.ADMISSION)
    assert guard['source'] == read(launcher.SOURCE)
    assert guard['qualification_eligible'] is guard['reserved_final_seeds_used'] is False
    return case, guard_path, guard


def verify_artifacts(players, case, artifacts, source, evidence):
    manifest = read(artifacts / 'manifest.json')
    assert {str(path.relative_to(artifacts)) for path in artifacts.rglob('*') if path.is_file()} == set(manifest) | {'manifest.json'}
    assert all(digest(artifacts / name) == sha for name, sha in manifest.items())
    assert digest(artifacts / 'manifest.json') == evidence['manifest_sha256']
    assert len(manifest) + 1 == evidence['archived_files']
    protocol = read(launcher.PROTOCOL)
    expected = {'arm': 'resource-filter', 'players': players, 'opponent': 'search_geo', 'start': 0, 'deals': 1,
                'seed': protocol['smoke_seed_template'].format(players=players),
                'model_sha256': protocol['model_pin']['files']['inference64.onnx'],
                'opponent_model': None, 'opponent_sha256': None,
                'samples': 8, 'workers': 8, 'search_workers': 1, 'runtime': '/workspace'}
    check = read(artifacts / 'resource-check.json')
    assert check['case'] == case and check['stage'] == 'complete' and check['runtime_pilot'] is True
    assert check['source_revision'] == source['revision'] and check['source_sha256'] == source['sha256']
    assert check['protocol_sha256'] == digest(launcher.PROTOCOL) and check['model_pin'] == protocol['model_pin']
    assert check['expected_config'] == expected
    assert check['job_runner_sha256'] == source['new_files']['ai/strong/resource-replanning-development-job-v1.py']
    assert check['sampler_sha256'] == source['base']['new_files']['ai/strong/resource-replanning-runtime-pilot-v1.py']
    for key in ('automatic_retries', 'gradients', 'qualification_eligible', 'reserved_final_seeds_used'):
        assert check[key] is False
    summary = verify_evaluation(artifacts / 'evaluation', {**expected, 'output': f'/workspace/ai/runs/{case}/evaluation'})
    assert summary == read(artifacts / 'summary.json')
    assert check['games'] == summary['games'] == 4 * players
    measured = read(artifacts / 'runtime.json')
    assert measured == check['runtime']
    for key in ('seconds', 'cpu_seconds'):
        finite(measured[key])
        assert measured[key] > 0
    for key in ('sampled_peak_total_rss_bytes', 'memory_samples'):
        integer(measured[key], 1)
    assert measured['memory_sampling_period_seconds'] == .1
    finite(check['seconds'])
    assert check['seconds'] >= measured['seconds'] >= summary['wall_seconds']
    local = LOCAL_RESULTS / f'{players}p-resource-filter/evaluation'
    pilot = read(launcher.PILOT)
    assert digest(local / 'evaluation.json') == pilot['cells'][f'{players}p-resource-filter']['report_sha256']
    parity = paired_parity(local, artifacts / 'evaluation')
    assert parity['learner_decisions'] == summary['counts']['decisions']
    assert parity['resource_decisions'] == summary['counts']['resource_search_decisions']
    assert parity['resource_rollouts'] == summary['counts']['rollouts']
    latencies = []
    for path in (artifacts / 'evaluation').glob('decisions-*.jsonl'):
        with path.open() as stream:
            for line in stream:
                row = json.loads(line)
                if row.get('resourcePlan') is not None:
                    latencies.append(row['elapsedMs'])
    assert len(latencies) == parity['resource_decisions'] > 0
    latency = {'count': len(latencies), 'p50_ms': float(np.percentile(latencies, 50)),
               'p95_ms': float(np.percentile(latencies, 95)), 'max_ms': max(latencies)}
    return {'summary': summary, 'runtime': measured, 'parity': parity, 'resource_latency': latency}


def collect(players, inspect_only=False):
    code_hashes = {str(path.relative_to(ROOT)): digest(path) for path in [Path(__file__), Path(launcher.__file__),
        STRONG / 'population_policy_verification.py', STRONG / 'resource_policy_verification_v1.py']}
    case, guard_path, guard = identity(players)
    api = HfApi()
    job = api.inspect_job(job_id=guard['job_id'])
    status = {'case': case, 'job_id': guard['job_id'], 'authoritative_status': job.status.stage,
              'checked_at': datetime.now(timezone.utc).isoformat(), 'guard_sha256': digest(guard_path),
              'qualification_eligible': False, 'reserved_final_seeds_used': False}
    if inspect_only:
        return status
    base = COLLECTED / case
    base.mkdir(parents=True, exist_ok=True)
    write(base / 'status.json', status)
    failed = job.status.stage in ('ERROR', 'CANCELED', 'CANCELLED', 'DELETED')
    if job.status.stage != 'COMPLETED' and not failed:
        return status
    log = base / 'job.log'
    if not log.exists():
        log.write_text('\n'.join(str(line) for line in api.fetch_job_logs(job_id=guard['job_id'], follow=False)))
    if failed:
        return {**status, 'failed': True, 'log_sha256': digest(log)}
    receipts = []
    for line in log.read_text().splitlines():
        if not line.startswith('{'):
            continue
        try:
            value = ast.literal_eval(line)
        except (ValueError, SyntaxError):
            continue
        if isinstance(value, dict) and isinstance(value.get('status'), dict) and value['status'].get('case') == case and 'evidence' in value:
            receipts.append(value)
    assert len(receipts) == 1, 'Missing/ambiguous evidence receipt; inspect the existing job, never resubmit'
    receipt, source = receipts[0], guard['source']
    evidence = receipt['evidence']
    assert evidence['repo'] == 'coyotte508/powergrid-ai-germany-v1'
    assert evidence['archive_path'] == f'archives/{case}.tgz' and re.fullmatch('[a-f0-9]{40}', evidence['revision'])
    assert evidence['remote_archive_verified'] is True and evidence['format'] == 'tar.gz'
    archive = Path(hf_hub_download(evidence['repo'], evidence['archive_path'], revision=evidence['revision']))
    assert digest(archive) == evidence['archive_sha256']
    artifacts = base / 'artifacts'
    if not artifacts.exists():
        extract_verified(archive, artifacts)
    result = verify_artifacts(players, case, artifacts, source, evidence)
    assert receipt['status'] == read(artifacts / 'resource-check.json')
    assert all(digest(ROOT / name) == sha for name, sha in code_hashes.items()), 'Collector changed during verification'
    verified = {**status, 'verified': True, **result, 'source': source, 'evidence': evidence,
                'local_pilot_descriptor_sha256': digest(launcher.PILOT), 'admission_sha256': digest(launcher.ADMISSION),
                'code_hashes': code_hashes, 'strength_eligible': False, 'new_strength_games': 0,
                'scope': 'One complete runtime-only endpoint deal. Timings are parallel HF execution, not AMD8840U serving latency. Exact local/HF recorded behavior is required before any separate development admission.'}
    write(base / 'verified.json', verified)
    return verified


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('players', type=int, choices=[2, 6])
    parser.add_argument('--inspect', action='store_true')
    args = parser.parse_args()
    result = collect(args.players, args.inspect)
    print(json.dumps({key: value for key, value in result.items()
                     if key in ('case', 'job_id', 'authoritative_status', 'failed', 'verified', 'summary', 'runtime', 'resource_latency')}, indent=2))
