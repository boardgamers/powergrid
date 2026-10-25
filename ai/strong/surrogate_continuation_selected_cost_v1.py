"""Measure the frozen learned opponent on the 24 separate runtime roots."""
import argparse
import math
import os
from pathlib import Path
import time

from huggingface_hub import hf_hub_download
from strategic_collection import ROOT, read, write, digest
from hybrid_search import Model
from opponent_surrogate_policy_v1 import SurrogatePolicy
from surrogate_continuation_runtime_v1 import INPUTS as RUNTIME_INPUTS, validate_inputs as validate_runtime
from surrogate_continuation_job_v1 import (source_check, validate_inputs, INPUTS, MEMBERS, MANIFEST, resources,
                                          check_root, SurrogateContinuationProbe)
from surrogate_continuation_study_v1 import PROTOCOL, run_chunk, verify_chunk, policy_digest
from surrogate_continuation_roots_v1 import object_hash
from policy_iteration_evidence_archive import upload_evidence

CASE = 'surrogate-continuation-selected-cost-v1'
MODE = 'surrogate_opponent_v1'


def runtime_roots():
    inputs = read(RUNTIME_INPUTS); validate_runtime(inputs)
    assert str(RUNTIME_INPUTS.relative_to(ROOT)) in read(MANIFEST)
    return inputs['roots']


def verify(folder, roots, policy_sha):
    folder = Path(folder); state = read(folder/'job.json')
    assert state['stage'] in ('complete', 'capped') and state['case'] == CASE
    assert state['scope'] in ('selected_runtime_calibration', 'local_engineering_fixture')
    assert state['root_hashes'] == {key: object_hash(root) for key, root in roots.items()}
    assert state['surrogate_policy_sha256'] == policy_sha and state['runner_sha256'] == digest(__file__)
    assert state['protocol_sha256'] == digest(PROTOCOL) and state['workers'] == 8
    assert state['continuations'] == 16*len(roots) and set(state['measurements']) == set(roots)
    assert all(state[k] is False for k in ('gradients', 'qualification_eligible', 'reserved_final_seeds_used', 'automatic_retries'))
    caps = 0
    for key, root in roots.items():
        result = verify_chunk(folder/key, root, surrogate_sha256=policy_sha)
        assert result['mode'] == MODE and result['begin'] == 0 and result['count'] == result['samples'] == 8
        caps += result['caps']; measurement = state['measurements'][key]
        assert measurement['rows'] == 16 and measurement['status_sha256'] == digest(folder/key/'status.json')
        assert measurement['memory_sampling_period_seconds'] == .2
        for name in ('seconds', 'cpu_seconds', 'sampled_peak_total_rss_bytes', 'memory_samples'):
            assert type(measurement[name]) in (int, float) and math.isfinite(measurement[name]) and measurement[name] > 0
    assert state['caps'] == caps and state['stage'] == ('complete' if caps == 0 else 'capped')
    return {'complete': caps == 0, 'case': CASE, 'scope': state['scope'], 'roots': len(roots),
            'continuations': 16*len(roots), 'caps': caps, 'measurements': state['measurements'],
            'full_study_admitted': False, 'qualification_eligible': False}


def execute(roots, focal, surrogate, out, *, scope, provenance):
    assert scope in ('selected_runtime_calibration', 'local_engineering_fixture')
    assert roots and all(root['identity']['mode'] == 'runtime' for root in roots.values())
    if scope == 'selected_runtime_calibration':
        assert set(roots) == {f'{n}p-{r}-{phase}' for n in (2, 6) for r in range(4) for phase in ('plant', 'bid', 'building')}
    assert focal.sha256 == read(PROTOCOL)['focal_model_sha256'] and surrogate.policy['members']
    out = Path(out); out.mkdir(parents=True, exist_ok=False); policy_sha = policy_digest(surrogate.policy)
    state = {'case': CASE, 'stage': 'running', 'scope': scope, 'workers': 8,
             'root_hashes': {key: object_hash(root) for key, root in roots.items()},
             'surrogate_policy_sha256': policy_sha, 'protocol_sha256': digest(PROTOCOL),
             'runner_sha256': digest(__file__), 'provenance': provenance, 'measurements': {},
             'gradients': False, 'qualification_eligible': False, 'reserved_final_seeds_used': False, 'automatic_retries': False}
    write(out/'job.json', state); began_job = time.perf_counter(); caps = 0
    try:
        for key, root in sorted(roots.items()):
            sampler = resources.MemorySampler(); began = time.perf_counter(); cpu0 = os.times(); sampler.thread.start()
            try:
                run_chunk(root, MODE, 0, 8, focal, surrogate, out/key, workers=8, surrogate_sha256=policy_sha)
                result = verify_chunk(out/key, root, surrogate_sha256=policy_sha); caps += result['caps']
            finally:
                sampler.stop.set(); sampler.thread.join(); cpu1 = os.times()
                measurement = {'seconds': time.perf_counter()-began, 'cpu_seconds': sum(cpu1[:4])-sum(cpu0[:4]),
                               'sampled_peak_total_rss_bytes': sampler.peak, 'memory_samples': sampler.samples,
                               'memory_sampling_period_seconds': .2}
                if (out/key/'status.json').exists(): measurement['status_sha256'] = digest(out/key/'status.json')
                if (out/key/'result.json').exists(): measurement['rows'] = len(read(out/key/'result.json')['rows'])
                state['measurements'][key] = measurement; write(out/'job.json', state)
            print({'root': key, 'seconds': measurement['seconds'], 'caps': result['caps']}, flush=True)
        state.update(stage='complete' if caps == 0 else 'capped', caps=caps, continuations=16*len(roots))
        write(out/'job.json', state); write(out/'audit.json', verify(out, roots, policy_sha))
    except BaseException as error:
        state.update(stage='failed', failure_type=type(error).__name__, error=str(error)); raise
    finally:
        state['wall_seconds'] = time.perf_counter()-began_job; write(out/'job.json', state)
        write(out/'manifest.json', {str(p.relative_to(out)): digest(p) for p in sorted(out.rglob('*')) if p.is_file()})
    return state


def check_layout(model_path):
    hashes = source_check(); roots = runtime_roots(); _, _, _, policy = validate_inputs()
    assert not os.environ.get('NODE_OPTIONS'); os.environ['PG_REFERENCE_RUNTIME'] = str(ROOT)
    focal = Model(model_path, threads=1); surrogate = SurrogatePolicy(policy, MEMBERS)
    probe = SurrogateContinuationProbe(focal, surrogate); choices = {}
    try:
        for key, root in roots.items():
            prepared = check_root(root, probe); choice = surrogate.predict_batch([prepared['observation']])[0]
            assert choice in prepared['options']; choices[key] = choice
    finally: probe.close()
    assert hashes == source_check()
    return {'complete': True, 'package_import_root': str(ROOT), 'runtime_roots_checked': 24,
            'surrogate_choices_sha256': object_hash(choices), 'runtime_inputs_sha256': digest(RUNTIME_INPUTS),
            'surrogate_policy_sha256': policy_digest(policy), 'new_continuations': 0}


def run():
    hashes = source_check(); roots = runtime_roots(); frozen, _, _, policy = validate_inputs()
    assert str(Path(__file__).relative_to(ROOT)) in hashes
    for field, path in (('SOURCE_MANIFEST_SHA256', MANIFEST), ('STUDY_INPUTS_SHA256', INPUTS/'frozen.json'),
                        ('RUNTIME_INPUTS_SHA256', RUNTIME_INPUTS), ('SURROGATE_POLICY_SHA256', INPUTS/'policy.json')):
        assert os.environ[field] == digest(path)
    assert not os.environ.get('NODE_OPTIONS'); os.environ['PG_REFERENCE_RUNTIME'] = str(ROOT)
    pin = resources.MODEL_PIN
    focal = Model(hf_hub_download(pin['repo'], pin['path'], revision=pin['revision']), threads=1)
    surrogate = SurrogatePolicy(policy, MEMBERS); out = ROOT/'ai/runs'/CASE; assert not out.exists()
    provenance = {'source_revision': os.environ['SOURCE_REVISION'], 'source_sha256': os.environ['SOURCE_SHA256'],
                  'source_manifest_sha256': digest(MANIFEST), 'study_inputs_sha256': digest(INPUTS/'frozen.json'),
                  'runtime_inputs_sha256': digest(RUNTIME_INPUTS), 'selection_freeze_sha256': frozen['selection_freeze_sha256']}
    try:
        execute(roots, focal, surrogate, out, scope='selected_runtime_calibration', provenance=provenance)
        assert hashes == source_check()
    except BaseException as error:
        if (out/'job.json').exists():
            state = read(out/'job.json'); state.update(stage='failed', wrapper_failure_type=type(error).__name__, wrapper_error=str(error))
            write(out/'job.json', state)
            write(out/'manifest.json', {str(p.relative_to(out)): digest(p) for p in sorted(out.rglob('*'))
                                        if p.is_file() and p != out/'manifest.json'})
        raise
    finally:
        if (out/'job.json').exists(): print({'status': read(out/'job.json'), 'evidence': upload_evidence(out)}, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__); parser.add_argument('--check-layout', action='store_true'); parser.add_argument('--model')
    args = parser.parse_args()
    if args.check_layout:
        assert args.model; print(check_layout(args.model))
    else:
        assert not args.model; run()
