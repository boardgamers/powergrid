"""Verify complete local/8840U batching comparisons and preserve them once."""
import argparse
import importlib.util
import json
from pathlib import Path
import shutil

from strategic_collection import ROOT, read, write, digest
from policy_iteration_evidence_archive import upload_evidence

STRONG = ROOT / 'ai/strong'
LOCAL = ROOT / 'ai/runs/bucketed-resource-inference-probe-v1'
SERVING = ROOT / 'ai/runs/bucketed-serving-inference-probe-v1'
TARGET = ROOT / 'ai/runs/bucketed-resource-inference-target-v1'
COLLECTED = TARGET / 'collected'
PACKAGE = ROOT / 'ai/runs/resource-replanning-8840u-prepared-v1/package'
OUT = ROOT / 'ai/runs/bucketed-inference-evidence-v1'
DESCRIPTOR = STRONG / 'bucketed-inference-evidence-v1.json'


def checked_status(folder):
    status = read(folder / 'status.json')
    assert status['stage'] == 'complete'
    assert all(digest(folder / name) == sha for name, sha in status['output_hashes'].items())
    assert status['candidate_sha256'] == digest(STRONG / 'bucketed_inference_v1.py')
    assert status['manifest_sha256'] == digest(PACKAGE / 'manifest.json')
    assert status['policy_adopted'] is status['gradients'] is status['qualification_eligible'] is False
    return status


def padded(counts):
    return sum(len(counts[start:start + 64]) * max(counts[start:start + 64]) for start in range(0, len(counts), 64))


def calls(folder, case):
    rows = [json.loads(line) for line in (folder / (case + '-calls.jsonl')).open()]
    for index, row in enumerate(rows):
        assert row['call'] == index and row['batch_size'] == 64
        assert row['rows'] == len(row['counts']) == len(row['choices']['baseline'])
        assert row['exact_choices'] and row['choices']['baseline'] == row['choices']['bucketed']
        assert all(0 <= choice < count for choice, count in zip(row['choices']['baseline'], row['counts']))
        assert row['baseline_seconds'] >= 0 and row['bucketed_seconds'] >= 0
        assert row['baseline_padded_actions'] == padded(row['counts'])
        assert row['bucketed_padded_actions'] == padded(sorted(row['counts']))
    return rows


def audit():
    spec = importlib.util.spec_from_file_location('bucket_probe', STRONG / 'probe-bucketed-resource-inference-v1.py')
    probe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probe)
    manifest = read(PACKAGE / 'manifest.json')
    assert all(digest(PACKAGE / name) == sha for name, sha in manifest['files'].items())
    local, target, serving = checked_status(LOCAL), checked_status(COLLECTED / 'output'), checked_status(SERVING)
    assert local['runner_sha256'] == target['runner_sha256'] == digest(STRONG / 'probe-bucketed-resource-inference-v1.py')
    assert serving['runner_sha256'] == digest(STRONG / 'probe-bucketed-serving-inference-v1.py')
    guard, receipt = read(TARGET / 'launch.json'), read(COLLECTED / 'launch.json')
    assert guard['stage'] == 'launched' and guard['pid'] == receipt['pid']
    assert '8840U' in receipt['machine']['processor'] and receipt['machine'] == read(COLLECTED / 'machine.json')
    assert guard['local_status_sha256'] == digest(LOCAL / 'status.json')
    assert guard['canonical_status_sha256'] == digest(SERVING / 'status.json')
    assert all(digest(COLLECTED / name) == sha == digest(STRONG / name) for name, sha in guard['files_sha256'].items())
    assert serving['positions'] == 2553 and serving['all_batch_choices_exact'] and serving['all_prior_target_moves_exact']
    choices = read(SERVING / 'choices.json')
    assert len(choices['baseline']) == 2553 and choices['baseline'] == choices['bucketed']
    fixtures = ROOT / 'ai/runs/policy-iteration-trained-8840u-prepared-v2/fixtures.jsonl'
    reference = ROOT / 'ai/runs/policy-iteration-trained-8840u-results-v2/frozen-1.jsonl'
    assert digest(fixtures) == serving['fixtures_sha256'] and digest(reference) == serving['reference_sha256']
    selected = read(PACKAGE / 'slow-roots.json')
    assert read(LOCAL / 'inputs.json') == read(COLLECTED / 'output/inputs.json') == selected
    assert set(local['roots']) == set(target['roots']) == set(selected)
    cells = {}
    for case, entry in selected.items():
        left, right = calls(LOCAL, case), calls(COLLECTED / 'output', case)
        normalized = lambda rows: [{k: v for k, v in row.items() if k not in ('baseline_seconds', 'bucketed_seconds')} for row in rows]
        assert normalized(left) == normalized(right)
        for folder, status, rows in [(LOCAL, local, left), (COLLECTED / 'output', target, right)]:
            totals = status['roots'][case]
            assert totals['calls'] == len(rows) and totals['exact_all_choices'] and totals['exact_recorded_result']
            for key in ('rows', 'baseline_seconds', 'bucketed_seconds', 'baseline_padded_actions', 'bucketed_padded_actions'):
                assert totals[key] == sum(row[key] for row in rows)
            result = read(folder / (case + '-result.json'))
            assert probe.semantic(result) == probe.semantic(entry['reference'])
            assert result['search']['truncated'] == 0
        cells[case] = {'local': local['roots'][case], 'target': target['roots'][case],
                      'target_inference_speed_ratio': target['roots'][case]['baseline_seconds'] / target['roots'][case]['bucketed_seconds'],
                      'exact_cross_host_observations_choices_and_continuations': True}
    return {'complete': True, 'canonical_positions': 2553, 'stress_roots': 4,
            'stress_predictions_per_host': sum(cell['target']['rows'] for cell in cells.values()),
            'cells': cells, 'target_machine': receipt['machine'],
            'model_sha256': manifest['model_sha256'], 'candidate_sha256': digest(STRONG / 'bucketed_inference_v1.py'),
            'collector_sha256': digest(__file__), 'new_hf_jobs': 0, 'new_games': 0, 'gradients': False,
            'policy_adopted': False, 'qualification_eligible': False, 'reserved_final_seeds_used': False,
            'scope': 'Batch regrouping, unchanged float64 model. All 2,553 canonical choices matched locally and all four old four-world stress roots matched across local/actual 8840U. Inference timers alternate order within the same fixed workloads. Selected engineering cases, not representative serving latency, strength or full-game equivalence for an adopted runtime.'}


def main(archive):
    review = audit()
    if archive:
        assert not OUT.exists() and not OUT.with_suffix('.tgz').exists() and not DESCRIPTOR.exists(), 'Inspect previous archive before retrying'
        files = [file for folder in (LOCAL, SERVING, TARGET) for file in folder.rglob('*') if file.is_file()]
        files += [STRONG / name for name in ('bucketed_inference_v1.py', 'probe-bucketed-resource-inference-v1.py', 'probe-bucketed-serving-inference-v1.py', 'collect-bucketed-inference-v1.py', 'policy_iteration_evidence_archive.py')]
        files += [PACKAGE / 'manifest.json', PACKAGE / 'slow-roots.json', ROOT / 'ai/runs/policy-iteration-trained-8840u-prepared-v2/fixtures.jsonl', ROOT / 'ai/runs/policy-iteration-trained-8840u-results-v2/frozen-1.jsonl']
        OUT.mkdir()
        for file in sorted(set(files)):
            assert not file.is_symlink()
            dest = OUT / file.relative_to(ROOT)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file, dest)
            assert digest(file) == digest(dest)
        write(OUT / 'review.json', review)
        write(OUT / 'manifest.json', {str(file.relative_to(OUT)): digest(file) for file in sorted(OUT.rglob('*')) if file.is_file()})
        write(DESCRIPTOR, {**review, **upload_evidence(OUT)})
        print({k: read(DESCRIPTOR)[k] for k in ('revision', 'archive_sha256', 'archived_files', 'remote_archive_verified')})
    else:
        print(json.dumps(review, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--archive', action='store_true')
    main(parser.parse_args().archive)
