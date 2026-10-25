"""Bounded reference/mixture runtime measurement on separate calibration roots."""
import argparse
import importlib.util
import os
from pathlib import Path
import time

from huggingface_hub import hf_hub_download
from strategic_collection import ROOT, read, write, digest
from hybrid_search import Model
from surrogate_continuation_roots_v1 import contract, object_hash
from surrogate_continuation_study_v1 import (PROTOCOL, check_root, run_chunk, verify_chunk,
                                            verify_result, SAMPLES, MAX_STEPS)
from surrogate_opponent_continuations_v1 import SurrogateContinuationProbe
from policy_iteration_evidence_archive import upload_evidence

STRONG = ROOT/'ai/strong'
INPUTS = STRONG/'fixtures/surrogate-continuation-runtime-roots-v1.json'
MANIFEST = ROOT/'surrogate-continuation-runtime-source-manifest.json'
MODES = ('reference_opponent_v1', 'neural_population')
spec = importlib.util.spec_from_file_location('root_resource_measurement', STRONG/'surrogate-continuation-roots-job-v1.py')
resources = importlib.util.module_from_spec(spec); spec.loader.exec_module(resources)


def select_roots(games):
    """One minimum-hash root per endpoint/rule/phase; no outcome inputs."""
    expected = {(n, seat, rule) for n in (2, 6) for seat in range(n) for rule in range(4)}
    assert set(games) == expected
    grouped = {}
    for (n, seat, rule), selected in games.items():
        assert set(selected['roots']) | set(selected['missing_phases']) == {'plant', 'bid', 'building'}
        assert not set(selected['roots']) & set(selected['missing_phases'])
        for phase, root in selected['roots'].items():
            assert root['identity'] == contract(n, 0, seat, rule, 'runtime') and root['phase'] == phase
            assert root['public_root_sha256'] == object_hash(root['request'])
            eligible = [row for row in selected['eligible'] if row['phase'] == phase]
            winner = min(eligible, key=lambda row: (row['rank'], row['decision']))
            assert all(root[k] == v for k, v in winner.items())
            key = f'{n}p-{rule}-{phase}'
            grouped.setdefault(key, []).append(root)
    assert set(grouped) == {f'{n}p-{r}-{phase}' for n in (2, 6) for r in range(4) for phase in ('plant', 'bid', 'building')}
    return {key: min(rows, key=lambda r: (r['rank'], r['identity']['episode'], r['decision']))
            for key, rows in sorted(grouped.items())}


def validate_inputs(inputs):
    p = read(PROTOCOL)
    assert inputs['protocol_sha256'] == digest(PROTOCOL) and inputs['focal_model_sha256'] == p['focal_model_sha256']
    assert inputs['modes'] == list(MODES) and inputs['samples'] == SAMPLES and inputs['max_steps'] == MAX_STEPS
    assert inputs['workers'] == 8 and inputs['continuations'] == 24*2*8*2 == 768
    assert inputs['training_eligible'] is inputs['qualification_eligible'] is inputs['reserved_final_seeds_used'] is False
    assert set(inputs['roots']) == {f'{n}p-{r}-{phase}' for n in (2, 6) for r in range(4) for phase in ('plant', 'bid', 'building')}
    for key, root in inputs['roots'].items():
        q = root['identity']; assert q == contract(q['players'], 0, q['seat'], q['rule'], 'runtime')
        assert key == f'{q["players"]}p-{q["rule"]}-{root["phase"]}'
        assert root['public_root_sha256'] == object_hash(root['request'])


def check_layout(model_path):
    inputs = read(INPUTS); validate_inputs(inputs)
    hashes = read(MANIFEST); assert all(digest(ROOT/name) == sha for name, sha in hashes.items())
    assert not os.environ.get('NODE_OPTIONS')
    os.environ['PG_REFERENCE_RUNTIME'] = str(ROOT)
    focal = Model(model_path, threads=1); assert focal.sha256 == inputs['focal_model_sha256']
    probe = SurrogateContinuationProbe(focal, None)
    try:
        for root in inputs['roots'].values(): check_root(root, probe)
    finally: probe.close()
    assert all(digest(ROOT/name) == sha for name, sha in hashes.items())
    return {'complete': True, 'package_import_root': str(ROOT), 'public_roots_checked': 24,
            'source_manifest_sha256': digest(MANIFEST), 'inputs_sha256': digest(INPUTS),
            'focal_model_sha256': focal.sha256, 'new_continuations': 0}


def verify(folder, inputs, key):
    """Recheck saved terminals, paired deck worlds and per-mode resource records."""
    validate_inputs(inputs); folder = Path(folder); state = read(folder/'job.json')
    assert key in inputs['roots'] and state['key'] == key and state['case'] == 'surrogate-continuation-cost-v1-'+key
    assert state['stage'] == 'complete' and state['caps'] == 0 and state['continuations'] == 32
    assert state['inputs_sha256'] == digest(INPUTS) and state['protocol_sha256'] == digest(PROTOCOL)
    assert state['job_runner_sha256'] == digest(__file__)
    assert all(state[k] is False for k in ('gradients', 'qualification_eligible', 'reserved_final_seeds_used', 'automatic_retries'))
    assert set(state['modes']) == set(MODES)
    root = inputs['roots'][key]; worlds = None
    for mode in MODES:
        result = verify_chunk(folder/mode, root)
        check = verify_result(root, result, mode, 0, SAMPLES); assert check['caps'] == 0
        same = {k: v['sha256'] for k, v in check['worlds'].items()}
        if worlds is None: worlds = same
        else: assert worlds == same
        measured = state['modes'][mode]
        assert measured['status_sha256'] == digest(folder/mode/'status.json')
        assert measured['rows'] == len(result['rows']) == 16
        for name in ('seconds', 'cpu_seconds', 'sampled_peak_total_rss_bytes', 'memory_samples'):
            assert type(measured[name]) in (int, float) and measured[name] > 0
        assert measured['memory_sampling_period_seconds'] == .2
    return {'complete': True, 'key': key, 'continuations': 32, 'caps': 0,
            'modes': state['modes'], 'paired_worlds_exact': True,
            'training_eligible': False, 'qualification_eligible': False}


def run(key, model_path=None, upload=True):
    inputs = read(INPUTS); validate_inputs(inputs); assert key in inputs['roots']
    assert not os.environ.get('NODE_OPTIONS')
    manifest = read(MANIFEST); assert all(digest(ROOT/name) == sha for name, sha in manifest.items())
    if upload:
        assert digest(MANIFEST) == os.environ['SOURCE_MANIFEST_SHA256']
        assert digest(INPUTS) == os.environ['INPUTS_SHA256'] and digest(PROTOCOL) == os.environ['PROTOCOL_SHA256']
    os.environ['PG_REFERENCE_RUNTIME'] = str(ROOT)
    case = 'surrogate-continuation-cost-v1-'+key
    out = ROOT/'ai/runs'/case; out.mkdir(parents=True, exist_ok=False)
    state = {'case': case, 'key': key, 'stage': 'running', 'inputs_sha256': digest(INPUTS),
             'protocol_sha256': digest(PROTOCOL), 'source_manifest_sha256': digest(MANIFEST),
             'source_revision': os.environ.get('SOURCE_REVISION'), 'source_sha256': os.environ.get('SOURCE_SHA256'),
             'job_runner_sha256': digest(__file__), 'automatic_retries': False, 'modes': {},
             'gradients': False, 'qualification_eligible': False, 'reserved_final_seeds_used': False}
    write(out/'job.json', state); start = time.perf_counter()
    try:
        if model_path is None:
            pin = resources.MODEL_PIN
            model_path = hf_hub_download(pin['repo'], pin['path'], revision=pin['revision'])
        focal = Model(model_path, threads=1); assert focal.sha256 == inputs['focal_model_sha256']
        for mode in MODES:
            sampler = resources.MemorySampler(); began, cpu0 = time.perf_counter(), os.times(); sampler.thread.start()
            try:
                status = run_chunk(inputs['roots'][key], mode, 0, SAMPLES, focal, None, out/mode, workers=inputs['workers'])
                assert status['stage'] == 'complete' and status['caps'] == 0
            finally:
                sampler.stop.set(); sampler.thread.join(); cpu1 = os.times()
                measured = {'seconds': time.perf_counter()-began, 'cpu_seconds': sum(cpu1[:4])-sum(cpu0[:4]),
                            'sampled_peak_total_rss_bytes': sampler.peak, 'memory_samples': sampler.samples,
                            'memory_sampling_period_seconds': .2}
                if (out/mode/'status.json').exists(): measured['status_sha256'] = digest(out/mode/'status.json')
                if (out/mode/'result.json').exists(): measured['rows'] = len(read(out/mode/'result.json')['rows'])
                state['modes'][mode] = measured; write(out/'job.json', state)
            print({'key': key, 'mode': mode, **measured}, flush=True)
        assert all(digest(ROOT/name) == sha for name, sha in manifest.items())
        state.update(stage='complete', caps=0, continuations=32)
        write(out/'job.json', state); write(out/'audit.json', verify(out, inputs, key))
    except BaseException as error:
        state.update(stage='failed', error=type(error).__name__+': '+str(error)); raise
    finally:
        state['wall_seconds'] = time.perf_counter()-start; write(out/'job.json', state)
        write(out/'manifest.json', {str(p.relative_to(out)): digest(p) for p in sorted(out.rglob('*')) if p.is_file()})
        if upload: print({'status': state, 'evidence': upload_evidence(out)}, flush=True)
    return state


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__); parser.add_argument('key', nargs='?')
    parser.add_argument('--model'); parser.add_argument('--check-layout', action='store_true')
    parser.add_argument('--local', action='store_true'); args = parser.parse_args()
    if args.check_layout:
        assert args.model and not args.key; print(check_layout(args.model), flush=True)
    else: run(args.key, args.model, not args.local)
