"""One fixed fresh root, all three opponent modes, all eight paired worlds.

HF entry requires the complete frozen corpus and a bundled selected learned
policy. execute_root also supports explicitly labelled local engineering fixtures.
"""
import argparse
from datetime import datetime, timezone
import importlib.util
import math
import os
from pathlib import Path
import re
import time

from huggingface_hub import hf_hub_download
from strategic_collection import ROOT, read, write, digest
from hybrid_search import Model
from opponent_surrogate_policy_v1 import SurrogatePolicy, make_policy
from surrogate_continuation_study_v1 import (PROTOCOL, MODES, SAMPLES, MAX_STEPS, check_root,
    run_chunk, verify_chunk, code_hashes, policy_digest)
from surrogate_continuation_roots_v1 import object_hash
from surrogate_continuation_analysis_v1 import manifest_roots, paired_record, check_record
from surrogate_opponent_continuations_v1 import SurrogateContinuationProbe
from policy_iteration_evidence_archive import upload_evidence

STRONG = ROOT/'ai/strong'
INPUTS = STRONG/'fixtures/surrogate-continuation-study-inputs-v1'
MEMBERS = STRONG/'fixtures/surrogate-continuation-selected-members-v1'
MANIFEST = ROOT/'surrogate-continuation-study-source-manifest.json'
spec = importlib.util.spec_from_file_location('study_resource_sampler', STRONG/'surrogate-continuation-roots-job-v1.py')
resources = importlib.util.module_from_spec(spec); spec.loader.exec_module(resources)


def job_name(root):
    q = root['identity']
    return f'surrogate-continuation-study-v1-{q["players"]}p-{q["episode"]}-{root["phase"]}'


def validate_inputs(directory=INPUTS):
    directory = Path(directory); frozen = read(directory/'frozen.json')
    manifest = read(directory/'roots.json'); policy = read(directory/'policy.json')
    assert frozen['complete'] is True and frozen['code_hashes'] == code_hashes()
    assert frozen['root_manifest_sha256'] == digest(directory/'roots.json')
    assert frozen['surrogate_policy_sha256'] == digest(directory/'policy.json') == policy_digest(policy)
    assert frozen['protocol_sha256'] == digest(PROTOCOL) and frozen['samples'] == SAMPLES == 8
    assert frozen['actions_per_root'] == 2 and frozen['max_steps'] == MAX_STEPS == 2400
    assert all(frozen[k] is False for k in ('gradients', 'qualification_eligible', 'reserved_final_seeds_used'))
    for key in ('root_index_sha256', 'selection_freeze_sha256', 'training_result_sha256', 'preparer_sha256'):
        assert re.fullmatch('[a-f0-9]{64}', frozen[key])
    assert policy == make_policy(policy['members']) and len(policy['members']) in (1, 4), 'An actual selected learned policy is required'
    roots = manifest_roots(manifest)
    assert frozen['roots'] == len(roots)
    expected = [{'root_id': root['root_id'], 'mode': mode, 'begin': 0, 'count': 8}
                for root in manifest['roots'] for mode in MODES]
    assert frozen['tasks'] == expected and frozen['continuations'] == len(expected)*16 <= 23040
    return frozen, manifest, roots, policy


def source_check():
    hashes = read(MANIFEST)
    assert all(digest(ROOT/name) == sha for name, sha in hashes.items())
    for path in (Path(__file__), INPUTS/'roots.json', INPUTS/'policy.json', INPUTS/'frozen.json'):
        assert str(path.relative_to(ROOT)) in hashes
    _, _, _, policy = validate_inputs()
    for member in policy['members']:
        path = MEMBERS/member['path']
        assert digest(path) == member['sha256'] == hashes[str(path.relative_to(ROOT))]
    return hashes


def search_work(result, workers):
    assert workers == 8 and result['begin'] == 0 and result['count'] == result['samples'] == 8
    rows = result['rows']; assert len(rows) == 16
    names = ('decisions', 'evaluations', 'truncated')
    forward = {k: sum(r['searchStats'][k] for r in rows) for k in names}
    prior = {k: 0 for k in names}
    for sample in range(8):
        a, b = rows[sample*2:sample*2+2]
        assert a['sample'] == b['sample'] == sample and a['actionIndex'] != b['actionIndex']
        assert a['diagnostic']['priorSearchStats'] == b['diagnostic']['priorSearchStats']
        assert a['initialBelief'] == b['initialBelief']
        for k in names: prior[k] += a['diagnostic']['priorSearchStats'][k]
    return {'forward': forward, 'prior_once_per_worker_world': prior,
            'physical_total': {k: forward[k]+prior[k] for k in names},
            'row_attributed_total': {k: forward[k]+2*prior[k] for k in names}}


def verify_root_job(folder, root, surrogate_sha256):
    folder = Path(folder); state = read(folder/'job.json')
    assert state['stage'] in ('complete', 'capped') and state['case'] == job_name(root)
    assert state['root_sha256'] == object_hash(root) and state['public_root_sha256'] == root['public_root_sha256']
    assert state['surrogate_policy_sha256'] == surrogate_sha256 and state['protocol_sha256'] == digest(PROTOCOL)
    assert state['runner_sha256'] == digest(__file__) and state['workers'] == 8 and state['continuations'] == 48
    assert state['scope'] in ('fresh_fidelity', 'local_engineering_fixture')
    assert all(state[k] is False for k in ('gradients', 'qualification_eligible', 'reserved_final_seeds_used', 'automatic_retries'))
    assert set(state['modes']) == set(MODES)
    results = {}
    for mode in MODES:
        result = verify_chunk(folder/mode, root, surrogate_sha256=surrogate_sha256 if mode == 'surrogate_opponent_v1' else None)
        results[mode] = [result]; measurement = state['modes'][mode]
        assert measurement['rows'] == 16 and measurement['status_sha256'] == digest(folder/mode/'status.json')
        assert measurement['search_work'] == search_work(result, 8)
        assert measurement['memory_sampling_period_seconds'] == .2
        for key in ('seconds', 'cpu_seconds', 'sampled_peak_total_rss_bytes', 'memory_samples'):
            assert type(measurement[key]) in (int, float) and math.isfinite(measurement[key]) and measurement[key] > 0
    report = paired_record(root, results); check_record(root, report)
    saved = read(folder/'paired.json')
    # JSON normalizes numeric world keys to strings.
    normalized = {**report, 'world_sha256': {str(k): v for k, v in report['world_sha256'].items()}}
    assert saved == normalized
    assert state['caps'] == report['caps'] and state['stage'] == ('complete' if report['complete'] else 'capped')
    assert state['paired_sha256'] == digest(folder/'paired.json')
    return {'complete': report['complete'], 'scope': state['scope'], 'case': state['case'],
            'continuations': 48, 'caps': report['caps'], 'paired_worlds_exact': True,
            'all_modes_retained': True, 'qualification_eligible': False}


def execute_root(root, focal, surrogate, out, *, scope, provenance):
    """No remote submission/upload. An incomplete execution is never rerun here."""
    assert scope in ('fresh_fidelity', 'local_engineering_fixture')
    assert surrogate.policy['members'] and focal.sha256 == read(PROTOCOL)['focal_model_sha256']
    if scope == 'fresh_fidelity': assert root['identity']['mode'] == 'root' and 'root_id' in root
    else: assert root['identity']['mode'] in ('runtime', 'preflight')
    out = Path(out); out.mkdir(parents=True, exist_ok=False); policy_sha = policy_digest(surrogate.policy)
    state = {'stage': 'running', 'case': job_name(root), 'scope': scope, 'started_at': datetime.now(timezone.utc).isoformat(),
             'root_sha256': object_hash(root), 'public_root_sha256': root['public_root_sha256'],
             'surrogate_policy_sha256': policy_sha, 'protocol_sha256': digest(PROTOCOL),
             'runner_sha256': digest(__file__), 'provenance': provenance, 'workers': 8, 'modes': {},
             'gradients': False, 'qualification_eligible': False, 'reserved_final_seeds_used': False, 'automatic_retries': False}
    write(out/'job.json', state); began_job = time.perf_counter(); results = {}
    try:
        for mode in MODES:
            sampler = resources.MemorySampler(); began = time.perf_counter(); cpu0 = os.times(); sampler.thread.start()
            try:
                run_chunk(root, mode, 0, 8, focal, surrogate if mode == 'surrogate_opponent_v1' else None,
                          out/mode, workers=8, surrogate_sha256=policy_sha if mode == 'surrogate_opponent_v1' else None)
                result = verify_chunk(out/mode, root, surrogate_sha256=policy_sha if mode == 'surrogate_opponent_v1' else None)
                results[mode] = [result]
            finally:
                sampler.stop.set(); sampler.thread.join(); cpu1 = os.times()
                measured = {'seconds': time.perf_counter()-began, 'cpu_seconds': sum(cpu1[:4])-sum(cpu0[:4]),
                            'sampled_peak_total_rss_bytes': sampler.peak, 'memory_samples': sampler.samples,
                            'memory_sampling_period_seconds': .2}
                if (out/mode/'status.json').exists(): measured['status_sha256'] = digest(out/mode/'status.json')
                if (out/mode/'result.json').exists():
                    raw = read(out/mode/'result.json'); measured['rows'] = len(raw['rows']); measured['search_work'] = search_work(raw, 8)
                state['modes'][mode] = measured; write(out/'job.json', state)
            print({'case': state['case'], 'mode': mode, 'seconds': measured['seconds'], 'caps': result['caps']}, flush=True)
        report = paired_record(root, results); write(out/'paired.json', report)
        state.update(stage='complete' if report['complete'] else 'capped', caps=report['caps'], continuations=48,
                     paired_sha256=digest(out/'paired.json'))
        write(out/'job.json', state); write(out/'audit.json', verify_root_job(out, root, policy_sha))
    except BaseException as error:
        state.update(stage='failed', failure_type=type(error).__name__, error=str(error)); raise
    finally:
        state['wall_seconds'] = time.perf_counter()-began_job; write(out/'job.json', state)
        write(out/'manifest.json', {str(p.relative_to(out)): digest(p) for p in sorted(out.rglob('*')) if p.is_file()})
    return state


def check_layout(model_path):
    hashes = source_check(); _, _, roots, policy = validate_inputs()
    assert not os.environ.get('NODE_OPTIONS'); os.environ['PG_REFERENCE_RUNTIME'] = str(ROOT)
    focal = Model(model_path, threads=1); surrogate = SurrogatePolicy(policy, MEMBERS)
    probe = SurrogateContinuationProbe(focal, surrogate); choices = {}
    try:
        for rid, root in roots.items():
            prepared = check_root(root, probe)
            choice = surrogate.predict_batch([prepared['observation']])[0]
            assert choice in prepared['options']; choices[rid] = choice
    finally: probe.close()
    assert hashes == source_check()
    return {'complete': True, 'package_import_root': str(ROOT), 'public_roots_checked': len(roots),
            'surrogate_choices_sha256': object_hash(choices), 'source_manifest_sha256': digest(MANIFEST),
            'focal_model_sha256': focal.sha256, 'surrogate_policy_sha256': policy_digest(policy), 'new_continuations': 0}


def run(root_id):
    hashes = source_check(); frozen, _, roots, policy = validate_inputs(); assert root_id in roots
    assert not os.environ.get('NODE_OPTIONS'); os.environ['PG_REFERENCE_RUNTIME'] = str(ROOT)
    for field, path in (('SOURCE_MANIFEST_SHA256', MANIFEST), ('STUDY_INPUTS_SHA256', INPUTS/'frozen.json'),
                        ('PROTOCOL_SHA256', PROTOCOL), ('SURROGATE_POLICY_SHA256', INPUTS/'policy.json')):
        assert os.environ[field] == digest(path)
    pin = resources.MODEL_PIN
    focal = Model(hf_hub_download(pin['repo'], pin['path'], revision=pin['revision']), threads=1)
    surrogate = SurrogatePolicy(policy, MEMBERS); root = roots[root_id]; out = ROOT/'ai/runs'/job_name(root)
    # Models/source are verified before starting, and unknown/partial outputs are immutable.
    assert not out.exists()
    provenance = {'source_revision': os.environ['SOURCE_REVISION'], 'source_sha256': os.environ['SOURCE_SHA256'],
                  'source_manifest_sha256': digest(MANIFEST), 'study_inputs_sha256': digest(INPUTS/'frozen.json'),
                  'root_manifest_sha256': frozen['root_manifest_sha256'], 'selection_freeze_sha256': frozen['selection_freeze_sha256']}
    try:
        execute_root(root, focal, surrogate, out, scope='fresh_fidelity', provenance=provenance)
        assert hashes == source_check()
    except BaseException as error:
        if (out/'job.json').exists():
            state = read(out/'job.json')
            state.update(stage='failed', wrapper_failure_type=type(error).__name__, wrapper_error=str(error))
            write(out/'job.json', state)
            write(out/'manifest.json', {str(p.relative_to(out)): digest(p) for p in sorted(out.rglob('*'))
                                        if p.is_file() and p != out/'manifest.json'})
        raise
    finally:
        if (out/'job.json').exists():
            print({'status': read(out/'job.json'), 'evidence': upload_evidence(out)}, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__); parser.add_argument('root_id', nargs='?')
    parser.add_argument('--check-layout', action='store_true'); parser.add_argument('--model')
    args = parser.parse_args()
    if args.check_layout:
        assert args.model and not args.root_id; print(check_layout(args.model))
    else:
        assert args.root_id and not args.model; run(args.root_id)
