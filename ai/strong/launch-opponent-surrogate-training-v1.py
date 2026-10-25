"""Submit original HF calibration/training handles with measured runtime admission."""
import argparse
import ast
from datetime import datetime, timezone
import fcntl
import hashlib
import math
from pathlib import Path
import re

from huggingface_hub import HfApi, get_token, hf_hub_download
from strategic_collection import ROOT, read, write, digest
from opponent_surrogate_hf_v1 import SOURCE, DATA_PIN, DESIGN, SOURCE_FILES, BOOTSTRAP
from population_policy_verification import extract_verified

GUARDS = ROOT/'ai/runs/opponent-surrogate-training-launches-v1'
CALIBRATION = ROOT/'ai/runs/opponent-surrogate-training-runtime-collected-v1'


def prerequisites():
    assert SOURCE.exists() and DATA_PIN.exists(), 'Verified source and complete fresh training data must be packaged first'
    source, pin, design = map(read, (SOURCE, DATA_PIN, DESIGN))
    assert source['stage'] == 'uploaded' and source['remote_archive_verified'] and pin['complete'] and pin['remote_archive_verified']
    assert source['data_pin'] == pin and source['data_pin_sha256'] == digest(DATA_PIN)
    assert source['design_sha256'] == pin['design_sha256'] == digest(DESIGN)
    assert source['data_check_sha256'] == pin['data_check_sha256'] and pin['test_records_included'] is False
    assert pin['split_games'] == {'train': 1920, 'validation': 320}
    assert set(source['files']) == set(SOURCE_FILES) | {str(DATA_PIN.relative_to(ROOT))}
    assert all(digest(ROOT/name) == sha for name, sha in source['files'].items())
    return source, pin, design


def measured_timeout(report, pin):
    assert report['stage'] == 'complete' and report['runtime_calibration_only'] is True
    assert report['warmup_updates'] == 16 and report['measured_updates'] == 128
    assert report['exact_export_positions'] == sum(pin['split_rows'].values())
    for field in ('full_four_seed_estimated_seconds', 'recovery_seconds', 'peak_host_rss_bytes',
                  'peak_gpu_allocated_bytes', 'gpu_total_bytes', 'mean_update_seconds'):
        assert type(report[field]) in (int, float) and math.isfinite(report[field]) and report[field] > 0
    assert 2 * report['peak_host_rss_bytes'] + 4e9 <= 30e9, 'Use a larger measured host; keep the complete dataset'
    assert 1.3 * report['peak_gpu_allocated_bytes'] <= report['gpu_total_bytes'], 'GPU memory reserve insufficient'
    design = read(DESIGN)
    assert type(report['train_nonforced_rows']) is int and 0 < report['train_nonforced_rows'] <= pin['split_rows']['train']
    for value in [report['initialization_seconds'], report['export_seconds'], *report['evaluation_seconds'].values()]:
        assert type(value) in (int, float) and math.isfinite(value) and value > 0
    expected = len(design['seeds']) * (report['initialization_seconds'] +
        math.ceil(report['train_nonforced_rows'] / design['batch_size']) * design['epochs'] * report['mean_update_seconds'] +
        (design['epochs'] + 1) * report['evaluation_seconds']['validation'] +
        2 * report['evaluation_seconds']['train'] + report['export_seconds'])
    assert math.isclose(expected, report['full_four_seed_estimated_seconds'], rel_tol=1e-12, abs_tol=1e-9)
    seconds = 900 + 2 * (report['recovery_seconds'] + report['full_four_seed_estimated_seconds'])
    hours = max(1, math.ceil(seconds / (3600 * .75)))
    assert hours <= 12, 'Split the four fixed seeds across measured jobs; never shorten training to fit'
    return {'flavor': 'l4x1', 'timeout_hours': hours, 'estimated_seconds_with_margin': seconds,
            'margin': '15 min setup, twice measured full-run/recovery cost, 25% timeout reserve; 2x host RSS plus 4 GB and 30% GPU allocation reserve.'}


def collect_calibration():
    source, pin, _ = prerequisites()
    path = GUARDS/'calibration.json'; guard = read(path)
    assert guard['stage'] == 'launched' and guard['mode'] == 'calibration'
    assert guard['source_sha256'] == digest(SOURCE) and guard['data_pin_sha256'] == digest(DATA_PIN)
    assert re.fullmatch('[a-f0-9]{24}', guard['job_id'])
    api = HfApi(); status = api.inspect_job(job_id=guard['job_id']).status.stage
    CALIBRATION.mkdir(parents=True, exist_ok=True)
    check = {'job_id': guard['job_id'], 'authoritative_status': status,
             'checked_at': datetime.now(timezone.utc).isoformat(), 'guard_sha256': digest(path)}
    write(CALIBRATION/'status.json', check)
    if status != 'COMPLETED': return check
    log = '\n'.join(str(x) for x in api.fetch_job_logs(job_id=guard['job_id'], follow=False))
    (CALIBRATION/'job.log').write_text(log); receipts = []
    for line in log.splitlines():
        if not line.startswith('{'): continue
        try: r = ast.literal_eval(line)
        except (SyntaxError, ValueError): continue
        if isinstance(r, dict) and isinstance(r.get('status'), dict) and r['status'].get('case') == 'opponent-surrogate-training-calibration-v1' and 'evidence' in r:
            receipts.append(r)
    assert len(receipts) == 1, 'Inspect the original upload; never resubmit an uncertain calibration'
    receipt = receipts[0]; evidence = receipt['evidence']
    assert evidence['repo'] == 'coyotte508/powergrid-ai-germany-v1'
    assert evidence['archive_path'] == 'archives/opponent-surrogate-training-calibration-v1.tgz'
    assert evidence['remote_archive_verified'] and re.fullmatch('[a-f0-9]{40}', evidence['revision'])
    archive = Path(hf_hub_download(evidence['repo'], evidence['archive_path'], revision=evidence['revision']))
    assert digest(archive) == evidence['archive_sha256']
    out = CALIBRATION/'artifacts'
    if not out.exists(): extract_verified(archive, out)
    assert digest(out/'manifest.json') == evidence['manifest_sha256']
    assert all(digest(out/name) == sha for name, sha in read(out/'manifest.json').items())
    report = read(out/'job.json'); assert report == receipt['status']
    assert report['source_revision'] == source['revision'] and report['source_sha256'] == source['sha256']
    assert report['design_sha256'] == digest(DESIGN) and report['data_check_sha256'] == pin['data_check_sha256']
    assert report['training_location'] == 'HF Jobs' and report['gradients'] is True
    assert report['training_eligible'] is False and report['test_labels_used'] is False
    assert digest(out/'derivative/parity.json') == report['parity_sha256']
    parity = read(out/'derivative/parity.json')
    assert parity['complete'] and parity['positions'] == parity['exact_choices'] == report['exact_export_positions']
    admission = measured_timeout(report, pin)
    verified = {**check, 'verified': True, 'report': report, 'evidence': evidence, 'admission': admission,
                'source_descriptor_sha256': digest(SOURCE), 'data_pin_sha256': digest(DATA_PIN),
                'collector_sha256': digest(__file__), 'qualification_eligible': False}
    write(CALIBRATION/'verified.json', verified); return verified


def launch(mode, execute=False):
    source, pin, _ = prerequisites()
    assert mode in ('calibration', 'full')
    assert 2 * pin['unpacked_bytes'] + 4e9 <= 30e9 and 4 * pin['unpacked_bytes'] <= 400e9
    admission = {'flavor': 'l4x1', 'timeout_hours': 2, 'scope': 'Bounded runtime/gradient calibration only'}
    calibration_sha = None
    if mode == 'full':
        assert (CALIBRATION/'verified.json').exists(), 'The original HF GPU calibration must verify before full training'
        proof = read(CALIBRATION/'verified.json')
        assert proof['verified'] and proof['authoritative_status'] == 'COMPLETED'
        assert proof['source_descriptor_sha256'] == digest(SOURCE) and proof['data_pin_sha256'] == digest(DATA_PIN)
        assert proof['collector_sha256'] == digest(__file__)
        assert proof['guard_sha256'] == digest(GUARDS/'calibration.json')
        assert proof['report'] == read(CALIBRATION/'artifacts/job.json')
        assert digest(CALIBRATION/'artifacts/manifest.json') == proof['evidence']['manifest_sha256']
        assert all(digest(CALIBRATION/'artifacts'/name) == sha for name, sha in read(CALIBRATION/'artifacts/manifest.json').items())
        admission = measured_timeout(proof['report'], pin); assert admission == proof['admission']
        calibration_sha = digest(CALIBRATION/'verified.json')
    if not execute:
        return {'admitted': True, 'mode': mode, 'execute': False, 'admission': admission}
    token = get_token(); assert token
    hardware = next(h for h in HfApi().list_jobs_hardware() if h.name == 'l4x1')
    assert hardware.cpu == '8 vCPU' and hardware.ram == '30 GB' and hardware.ephemeral_storage == '400 GB'
    assert hardware.accelerator.model == 'L4' and hardware.accelerator.vram == '24 GB'
    GUARDS.mkdir(parents=True, exist_ok=True)
    with (GUARDS/'.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        path = GUARDS/(mode+'.json')
        if path.exists():
            prior = read(path)
            assert prior['stage'] == 'launched' and prior['source_sha256'] == digest(SOURCE)
            return {'existing_job_id': prior['job_id'], 'authoritative_status': HfApi().inspect_job(job_id=prior['job_id']).status.stage}
        record = {'mode': mode, 'stage': 'launch_intent', 'source_sha256': digest(SOURCE),
                  'data_pin_sha256': digest(DATA_PIN), 'created_at': datetime.now(timezone.utc).isoformat(),
                  'admission': admission, 'calibration_verified_sha256': calibration_sha,
                  'bootstrap_sha256': hashlib.sha256(BOOTSTRAP.encode()).hexdigest(),
                  'launcher_sha256': digest(__file__), 'qualification_eligible': False}
        with path.open('x') as stream:
            import json
            json.dump(record, stream, indent=2)
        try:
            env = {'SOURCE_ARCHIVE': source['archive'], 'SOURCE_REVISION': source['revision'], 'SOURCE_SHA256': source['sha256'],
                   'SOURCE_MANIFEST_SHA256': source['manifest_sha256'], 'DATA_CHECK_SHA256': pin['data_check_sha256'],
                   'DESIGN_SHA256': digest(DESIGN), 'POWERGRID_HF_TRAINING': '1', 'CUBLAS_WORKSPACE_CONFIG': ':4096:8',
                   'MODE': mode, 'HF_HUB_DISABLE_PROGRESS_BARS': '1'}
            job = HfApi().run_job(image='pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime', command=['bash', '-lc', BOOTSTRAP],
                flavor=admission['flavor'], timeout=f"{admission['timeout_hours']}h", secrets={'HF_TOKEN': token}, env=env,
                name=f'opponent-surrogate-training-{mode}-v1', labels={'project': 'powergrid-ai', 'stage': 'opponent-surrogate-training-v1', 'mode': mode})
            record.update(stage='launched', job_id=job.id)
        except BaseException as error:
            record.update(stage='launch_unknown', error=type(error).__name__ + ': ' + str(error)); raise
        finally: write(path, record)
    return {'mode': mode, 'job_id': record['job_id'], 'admission': admission}


if __name__ == '__main__':
    p = argparse.ArgumentParser(__doc__); p.add_argument('operation', choices=['calibration', 'full', 'collect-calibration'])
    p.add_argument('--execute', action='store_true'); a = p.parse_args()
    r = collect_calibration() if a.operation == 'collect-calibration' else launch(a.operation, a.execute)
    print({k: v for k, v in r.items() if k not in ('report', 'evidence')})
