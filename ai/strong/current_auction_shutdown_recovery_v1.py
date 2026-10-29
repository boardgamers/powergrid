"""Recover complete original terminal data, preserving the original HF ERROR.

No policy calls, games, retries, source edits or outcome-based acceptance.
Only the known frozen arena's post-terminal child shutdown timeout is eligible.
"""
from copy import deepcopy
import math
import os
from pathlib import Path
import subprocess

from public_policy_development_job_v1 import read, digest, write
from public_policy_final_audit_v1 import audit_shard, same, require
from public_policy_final_contract_v1 import audit_execution_binding

RULE = 'complete_original_terminals_after_policy_shutdown_timeout_v1'
ARENA_SHA = '1288ffb3d42a3c351c805c652e7c9c5f63b284f6c7061c7436f6ba06e9fc14eb'
RUNTIME_SHA = 'fc135130689140b6fd72a76e6e14c59a7fea59717b858d330bac0c7f6aad93df'


def timeout_error(config, descriptor):
    root = config['artifact']
    command = ['/usr/local/bin/python', '-u', '-B', root+'/ai/strong/public_policy_runtime_v1.py',
               root, '--descriptor', descriptor, '--diagnostics']
    return 'TimeoutExpired: '+str(subprocess.TimeoutExpired(command, 30))


def reconstruct(report, games, expected, descriptor):
    """Pure completeness/error gate; the full raw decision audit follows this."""
    n = expected['players']; wanted = set(range(expected['start']*4*n, (expected['start']+expected['deals'])*4*n))
    require(report['passed'] is False and report['all_complete'] is False, 'Original report must remain failed')
    require(report['validation_error'] == 'ValueError: Incomplete execution; preserve original receipts', 'Other original failure')
    require(report['expected_games'] == expected['games'] == len(wanted), 'Wrong expected game count')
    require(len(games) == len(wanted) and {g['episode'] for g in games} == wanted, 'Missing/duplicate original terminals')
    indexed = {g['episode']: g for g in games}; present = report['results']
    require(report['completed_games'] == len(present) < len(wanted), 'Invalid original summary count')
    require(len({g['episode'] for g in present}) == len(present), 'Duplicate original summary record')
    require(all(g['episode'] in indexed and same(g, indexed[g['episode']]) for g in present), 'Original summary/game mismatch')
    errors = report['errors']; omitted = wanted - {g['episode'] for g in present}
    require(len(errors) == len(omitted) and {e['episode'] for e in errors} == omitted, 'Errors do not match omitted terminals')
    require(all(e['error'] == timeout_error(report['config'], descriptor) for e in errors), 'Not the known shutdown timeout')
    require(report['game_caps'] == report['rollout_caps'] == 0, 'Original summary capped')
    require(all(g['terminal']['truncated'] is False and g['rollout_caps'] == 0 for g in games), 'Original terminal/search capped')
    require(not report['qualification_eligible'] and report['reserved_final_seeds_used'] is False, 'Wrong-purpose original')
    derived = deepcopy(report)
    derived.update(results=[indexed[e] for e in sorted(wanted)], completed_games=len(wanted),
                   all_complete=True, passed=True, errors=[], validation_error=None)
    derived['terminal_recovery'] = {'rule': RULE, 'original_hf_stage': 'ERROR',
        'original_errors': deepcopy(errors), 'omitted_terminal_episodes': sorted(omitted),
        'all_original_games_retained': True, 'new_games': 0, 'raw_records_changed': False}
    return derived


def original_data(folder, artifact, source, row, evidence):
    folder, artifact = Path(folder), Path(artifact)
    pins = read(folder/'manifest.json')
    require(digest(folder/'manifest.json') == evidence['manifest_sha256'], 'Original manifest changed')
    require(set(pins)|{'manifest.json'} == {str(p.relative_to(folder)) for p in folder.rglob('*') if p.is_file()}, 'Original file set changed')
    require(all(digest(folder/n) == h for n,h in pins.items()), 'Original raw file changed')
    require(digest(artifact/'manifest.json') == row['identity']['runtimeManifestSha256'] == RUNTIME_SHA, 'Wrong frozen runtime')
    require(digest(artifact/'ai/strong/public_policy_arena_v1.py') == ARENA_SHA, 'Unknown cleanup semantics')
    m, status = read(folder/'measurement.json'), read(folder/'job/job-status.json')
    expected = {k: source[k] for k in ('source_manifest_sha256','entry_sha256')}
    expected.update({k: row[k] for k in ('job_spec_sha256','candidate_sha256','contract_sha256','identity','shard')})
    expected.update(source_revision=source['revision'], source_archive_sha256=source['sha256'])
    for item in (m, status):
        require(item['stage'] == 'failed' and item['failure_type'] == 'CalledProcessError', 'Not the recorded wrapper failure')
        require(same(item['provenance'], expected), 'Original execution provenance differs')
        require(item['gradient_updates'] == 0 and item['qualified'] is False and item['reserved_final_seeds_used'] is False, 'Original side effects/purpose differ')
    require(m['case'] == row['name'] and m['scope'] == 'development', 'Wrong original scope')
    require(m['experiment_protocol_sha256'] == source['protocol_sha256'] and m['measured_entry_sha256'] == source['measured_entry_sha256'], 'Wrong measured entry')
    measure = m['measurement']
    require(all(type(measure[k]) in (int,float) and math.isfinite(measure[k]) and measure[k] > 0
                for k in ('seconds','cpu_seconds','sampled_peak_total_rss_bytes','memory_samples')), 'Invalid original costs')
    require(measure['memory_sampling_period_seconds'] == .2 and measure['includes_startup_and_validation'] is True, 'Wrong measurement scope')
    inner = folder/'job'; evaluation = inner/'evaluation'
    require(digest(inner/'source-manifest.json') == source['source_manifest_sha256'] and digest(inner/'job-spec.json') == row['job_spec_sha256'], 'Original source/job changed')
    require(not list(evaluation.glob('failure-*.json')), 'A game failed before terminal cleanup')
    report = read(evaluation/'evaluation.json')
    games = [read(p) for p in sorted(evaluation.glob('game-*.json'))]
    descriptor = 'policies/'+row['arm']+'.json'
    require(report['config']['descriptor'] == descriptor, 'Wrong original descriptor')
    derived = reconstruct(report, games, row['shard'], descriptor)
    for error in report['errors']:
        require((evaluation/f"policy-{error['episode']}.stderr.log").read_text() == '', 'Unexplained failed-child stderr')
    return evaluation, derived, measure, pins


def prepare(folder, artifact, source, row, evidence, target):
    """Create one exclusive derived view; original files are never changed."""
    target = Path(target)
    require(not target.exists(), 'Inspect existing recovery attempt; never overwrite/retry it')
    evaluation, derived, _, _ = original_data(folder, artifact, source, row, evidence)
    target.mkdir(); view = target/'evaluation'; view.mkdir()
    write(target/'intent.json', {'rule': RULE, 'original_evaluation_sha256': digest(evaluation/'evaluation.json'),
        'original_manifest_sha256': evidence['manifest_sha256'], 'source_sha256': source['sha256']})
    for p in evaluation.iterdir():
        if p.is_file() and p.name != 'evaluation.json':
            os.link(p, view/p.name)  # Only read these; never modify a linked input.
    write(view/'evaluation.json', derived)
    review = audit(folder, artifact, source, row, evidence, target)
    write(target/'review.json', review)
    return review


def audit(folder, artifact, source, row, evidence, target):
    """Independent full re-audit, without writing or admitting anything."""
    folder, target = Path(folder), Path(target)
    original, derived, measurement, pins = original_data(folder, artifact, source, row, evidence)
    view = target/'evaluation'; intent = read(target/'intent.json')
    require(intent == {'rule': RULE, 'original_evaluation_sha256': digest(original/'evaluation.json'),
        'original_manifest_sha256': evidence['manifest_sha256'], 'source_sha256': source['sha256']}, 'Recovery input binding changed')
    require(same(read(view/'evaluation.json'), derived), 'Derived report differs from all original terminals')
    require({p.name for p in view.iterdir()} == {p.name for p in original.iterdir()}, 'Derived view file set differs')
    require(all(digest(view/p.name) == digest(p) for p in original.iterdir() if p.is_file() and p.name!='evaluation.json'), 'Raw record changed in derived view')
    checked = audit_shard(view, row['shard'], row['identity'], reserved=False)
    binding = audit_execution_binding(view, row['identity'], source['runner_sha256'])
    require(all(digest(folder/n) == h for n,h in pins.items()), 'Original files changed during recovery audit')
    return {'games':row['shard']['games'], 'audit':checked, 'execution_binding':binding,
        'measurement':measurement, 'recovery':{'rule':RULE, 'original_hf_stage':'ERROR',
            'original_evaluation_sha256':digest(original/'evaluation.json'),
            'original_errors':read(original/'evaluation.json')['errors'],
            'derived_evaluation_sha256':digest(view/'evaluation.json'),
            'omitted_terminal_episodes':derived['terminal_recovery']['omitted_terminal_episodes'],
            'original_manifest_sha256':evidence['manifest_sha256'],
            'all_original_games_retained':True, 'new_games':0, 'raw_records_changed':False}}


def complete_data(job):
    if job.get('verified') is not True: return False
    if job['stage'] == 'COMPLETED': return 'recovery' not in job['review']
    if job['stage'] != 'ERROR': return False
    r = job['review'].get('recovery', {})
    return (r.get('rule') == RULE and r.get('original_hf_stage') == 'ERROR'
        and r.get('all_original_games_retained') is True and r.get('new_games') == 0
        and r.get('raw_records_changed') is False and bool(r.get('original_errors')))
