"""Audit and optionally archive the completed fixed-root component profile."""
import argparse
import importlib.util
from pathlib import Path
import shutil

from strategic_collection import ROOT, read, write, digest
from policy_iteration_evidence_archive import upload_evidence

STRONG = ROOT / 'ai/strong'
PACKAGE = ROOT / 'ai/runs/resource-replanning-8840u-prepared-v1/package'
FAILED = ROOT / 'ai/runs/resource-components-profile-v1'
COMPLETE = ROOT / 'ai/runs/resource-components-profile-v2'
OUT = ROOT / 'ai/runs/resource-components-profile-evidence-v2'
DESCRIPTOR = STRONG / 'resource-components-profile-evidence-v2.json'


def audit():
    spec = importlib.util.spec_from_file_location('component_profile_v2', STRONG / 'profile-resource-components-v2.py')
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    status = read(COMPLETE / 'status.json')
    manifest = read(PACKAGE / 'manifest.json')
    assert status['stage'] == 'complete' and status['exact_recorded_result']
    assert status['runner_sha256'] == digest(runner.__file__)
    assert status['manifest_sha256'] == digest(PACKAGE / 'manifest.json')
    assert all(digest(PACKAGE / name) == sha for name, sha in manifest['files'].items())
    assert all(digest(COMPLETE / name) == sha for name, sha in status['output_hashes'].items())
    result = read(COMPLETE / 'result.json')
    reference = read(PACKAGE / 'slow-roots.json')[status['case']]['reference']
    assert runner.semantic(result) == runner.semantic(reference)
    assert result['search']['evaluations'] == status['rollouts'] == 128
    assert result['search']['truncated'] == 0 and result['search']['usable']
    assert status['samples'] == 4 and status['threads'] == status['workers'] == 1
    profiles = read(COMPLETE / 'v8-summary.json')
    assert len(profiles) == status['v8_profiles'] == 3
    for profile in profiles:
        assert runner.summarize_v8(COMPLETE / profile['file']) == profile
    failed = read(FAILED / 'status.json')
    diagnosis = read(FAILED / 'diagnosis.json')
    assert failed['stage'] == 'failed'
    assert digest(FAILED / 'failed-runner.py') == digest(STRONG / 'profile-resource-components-v1.py') == failed['runner_sha256'] == diagnosis['old_runner_sha256']
    assert diagnosis['new_runner_sha256'] == status['runner_sha256']
    wall = status['wall_seconds']
    timing = status['outer_call_timing']
    return {
        'complete': True, 'status': status, 'failed_harness_diagnosis': diagnosis,
        'onnx_run_wall_fraction': status['onnx_run_seconds'] / wall,
        'engine_pool_wall_fraction': timing['engine_pool_seconds'] / wall,
        'prediction_excluding_onnx_seconds': timing['prediction_seconds'] - status['onnx_run_seconds'],
        'interpretation': 'Native ONNX inference dominates this fixed profiled root; the next largest measured interval is waiting for the JS engine pool. Python feature packing is smaller. This does not justify a full engine rewrite or establish representative latency. Node idle intervals overlap Python/inference work and must not be added to wall time.',
        'scope': status['limitations'], 'new_arena_games': 0, 'new_hf_jobs': 0,
        'gradients': False, 'qualification_eligible': False, 'reserved_final_seeds_used': False,
        'collector_sha256': digest(__file__),
    }


def main(archive=False):
    review = audit()
    if archive:
        assert not DESCRIPTOR.exists() and not OUT.exists() and not OUT.with_suffix('.tgz').exists(), 'Inspect previous archive outcome before retrying'
        files = [Path(__file__), STRONG / 'profile-resource-components-v1.py', STRONG / 'profile-resource-components-v2.py', STRONG / 'policy_iteration_evidence_archive.py', PACKAGE / 'manifest.json', PACKAGE / 'slow-roots.json', PACKAGE / 'benchmark.py']
        files += [p for folder in (FAILED, COMPLETE) for p in folder.iterdir() if p.is_file()]
        OUT.mkdir()
        for file in sorted(set(files)):
            assert file.is_file() and not file.is_symlink()
            target = OUT / file.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file, target)
            assert digest(file) == digest(target)
        write(OUT / 'review.json', review)
        write(OUT / 'manifest.json', {str(p.relative_to(OUT)): digest(p) for p in sorted(OUT.rglob('*')) if p.is_file()})
        write(DESCRIPTOR, {**review, **upload_evidence(OUT)})
        print({k: read(DESCRIPTOR)[k] for k in ('revision', 'archive_sha256', 'archived_files', 'remote_archive_verified')})
    else:
        print({k: review[k] for k in ('complete', 'onnx_run_wall_fraction', 'engine_pool_wall_fraction', 'prediction_excluding_onnx_seconds', 'scope')})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--archive', action='store_true')
    main(parser.parse_args().archive)
