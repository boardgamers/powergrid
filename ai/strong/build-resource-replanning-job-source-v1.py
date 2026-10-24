"""Package the tested HF wrapper; source availability never authorizes a launch."""
import argparse
from pathlib import Path
import shutil
import tarfile

from huggingface_hub import HfApi, hf_hub_download
from strategic_collection import ROOT, read, write, digest
from resource_development_v1 import PROTOCOL, verify_pins

STRONG = ROOT / 'ai/strong'
BASE = STRONG / 'resource-replanning-runtime-source-v1.json'
WRAPPER = STRONG / 'resource-replanning-development-job-v1.py'
PREFLIGHT = ROOT / 'ai/runs/resource-development-wrapper-preflight-v1'
PREP = ROOT / 'ai/runs/resource-replanning-job-source-prepared-v1'
SOURCE = STRONG / 'resource-replanning-job-source-v1.json'
ARCHIVE = ROOT / 'ai/runs/strong-source-resource-replanning-jobs-v1.tgz'
REPO = 'coyotte508/powergrid-ai-training-v1'


def prerequisites():
    protocol, base, proof = read(PROTOCOL), read(BASE), read(PREFLIGHT / 'receipt.json')
    verify_pins(protocol)
    assert base['remote_archive_verified'] and base['protocol_sha256'] == digest(PROTOCOL)
    assert proof['job_contracts_checked'] == 378 and proof['invalid_contracts_rejected'] == 13
    assert proof['execution_boundaries_checked'] == 3
    assert proof['real_model_and_opponent_hashes_checked'] and proof['runtime_and_development_seeds_distinct']
    assert proof['new_games'] == proof['new_hf_jobs'] == proof['external_uploads'] == 0
    assert proof['runner_sha256'] == digest(WRAPPER)
    assert proof['harness_sha256'] == digest(PREFLIGHT / 'check.py')
    assert len(proof['receipts']) == 3
    for receipt in proof['receipts']:
        folder = PREFLIGHT / 'layout/ai/runs' / receipt['case']
        assert receipt['expected_failure_recorded']
        assert digest(folder / 'resource-check.json') == receipt['status_sha256']
        status = read(folder / 'resource-check.json')
        assert status['stage'] == 'failed' and status['error'].startswith('ReachedEvaluation:')
        assert all(digest(folder / name) == sha for name, sha in read(folder / 'manifest.json').items())
    return protocol, base, proof


def prepare():
    protocol, base, proof = prerequisites()
    assert not any(path.exists() for path in (PREP, SOURCE, ARCHIVE)), 'Inspect an existing preparation before proceeding'
    original = ROOT / 'ai/runs' / base['archive']
    assert digest(original) == base['sha256']
    PREP.mkdir()
    layout = PREP / 'layout'
    layout.mkdir()
    with tarfile.open(original) as bundle:
        members = bundle.getmembers()
        assert all(member.isfile() and not Path(member.name).is_absolute()
                   and '..' not in Path(member.name).parts for member in members)
        bundle.extractall(layout, filter='data')
    before = {str(file.relative_to(layout)): digest(file) for file in layout.rglob('*') if file.is_file()}
    assert len(before) == 1482
    assert digest(layout / 'resource-runtime-manifest.json') == base['manifest_sha256']
    runtime_manifest = read(layout / 'resource-runtime-manifest.json')
    assert len(runtime_manifest) == proof['frozen_files_unchanged'] == 1481
    assert all(before[name] == digest(PREFLIGHT / 'layout' / name) == sha
               for name, sha in runtime_manifest.items())
    assert not (layout / 'ai/runs').exists()
    added = {}
    for file in (WRAPPER, Path(__file__)):
        name = str(file.relative_to(ROOT))
        assert name not in before
        shutil.copy2(file, layout / name)
        added[name] = digest(file)
        assert digest(layout / name) == added[name]
    assert digest(layout / WRAPPER.relative_to(ROOT)) == digest(PREFLIGHT / 'layout' / WRAPPER.relative_to(ROOT))
    assert all(digest(layout / name) == sha for name, sha in before.items())
    manifest = {**before, **added}
    write(layout / 'resource-job-manifest.json', manifest)
    with tarfile.open(ARCHIVE, 'w:gz') as bundle:
        for name in sorted([*manifest, 'resource-job-manifest.json']):
            bundle.add(layout / name, arcname=name, recursive=False)
    prepared = {
        'repo': REPO, 'archive': ARCHIVE.name, 'sha256': digest(ARCHIVE), 'bytes': ARCHIVE.stat().st_size,
        'manifest_sha256': digest(layout / 'resource-job-manifest.json'), 'protocol_sha256': digest(PROTOCOL),
        'base': base, 'base_descriptor_sha256': digest(BASE), 'unchanged_base_files': len(before),
        'new_files': added, 'preflight_receipt_sha256': digest(PREFLIGHT / 'receipt.json'),
        'preflight': proof, 'clean_package_matches_tested_runtime_and_wrapper': True,
        'no_generated_run_outputs_in_package': True, 'runtime_admitted': False,
        'development_admitted': False, 'new_hf_jobs': 0, 'gradients': False,
        'qualification_eligible': False, 'reserved_final_seeds_used': False,
    }
    write(PREP / 'prepared.json', prepared)
    print({key: prepared[key] for key in ('archive', 'sha256', 'unchanged_base_files', 'runtime_admitted', 'new_hf_jobs')}, flush=True)


def upload():
    prerequisites()
    assert not SOURCE.exists(), 'Inspect the existing source descriptor before any upload'
    prepared = read(PREP / 'prepared.json')
    assert digest(ARCHIVE) == prepared['sha256'] and digest(PROTOCOL) == prepared['protocol_sha256']
    assert digest(BASE) == prepared['base_descriptor_sha256']
    assert digest(PREFLIGHT / 'receipt.json') == prepared['preflight_receipt_sha256']
    assert all(digest(ROOT / name) == sha for name, sha in prepared['new_files'].items())
    assert digest(PREP / 'layout/resource-job-manifest.json') == prepared['manifest_sha256']
    assert all(digest(PREP / 'layout' / name) == sha
               for name, sha in read(PREP / 'layout/resource-job-manifest.json').items())
    with (PREP / 'upload-intent.json').open('x') as stream:
        stream.write('{"purpose":"one source upload; inspect uncertain outcomes before any retry"}\n')
    commit = HfApi().upload_file(repo_id=REPO, repo_type='dataset', path_or_fileobj=ARCHIVE, path_in_repo=ARCHIVE.name)
    write(PREP / 'upload-receipt.json', {'repo': REPO, 'revision': commit.oid, 'archive': ARCHIVE.name, 'sha256': prepared['sha256']})
    assert digest(hf_hub_download(REPO, ARCHIVE.name, repo_type='dataset', revision=commit.oid)) == prepared['sha256']
    source = {**prepared, 'revision': commit.oid, 'remote_archive_verified': True,
              'preparation_sha256': digest(PREP / 'prepared.json')}
    write(SOURCE, source)
    print({key: source[key] for key in ('archive', 'revision', 'sha256', 'remote_archive_verified')}, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('stage', choices=('prepare', 'upload'))
    globals()[parser.parse_args().stage]()
