"""Preserve the HF wrapper/source checks separately from playing-strength data."""
import importlib.util
from pathlib import Path
import shutil

from strategic_collection import ROOT, read, write, digest
from policy_iteration_evidence_archive import upload_evidence

STRONG = ROOT / 'ai/strong'
spec = importlib.util.spec_from_file_location('resource_job_source', STRONG / 'build-resource-replanning-job-source-v1.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)
OUT = ROOT / 'ai/runs/resource-job-source-preflight-evidence-v1'
DESCRIPTOR = STRONG / 'resource-job-source-preflight-evidence-v1.json'


def main():
    protocol, base, proof = builder.prerequisites()
    source = read(builder.SOURCE)
    assert source['remote_archive_verified'] and source['runtime_admitted'] is False
    assert source['development_admitted'] is False and source['new_hf_jobs'] == 0
    assert source['base'] == base and source['preflight'] == proof
    assert source['preparation_sha256'] == digest(builder.PREP / 'prepared.json')
    assert source['preflight_receipt_sha256'] == digest(builder.PREFLIGHT / 'receipt.json')
    assert digest(builder.ARCHIVE) == source['sha256']
    assert digest(builder.PREP / 'layout/resource-job-manifest.json') == source['manifest_sha256']
    assert all(digest(builder.PREP / 'layout' / name) == sha
               for name, sha in read(builder.PREP / 'layout/resource-job-manifest.json').items())
    assert all(digest(ROOT / name) == sha for name, sha in source['new_files'].items())
    assert not OUT.exists() and not OUT.with_suffix('.tgz').exists() and not DESCRIPTOR.exists(), \
        'Inspect any previous upload attempt before another archive'
    files = [Path(__file__), builder.SOURCE, builder.BASE, builder.WRAPPER, Path(builder.__file__),
             builder.PROTOCOL, STRONG / 'policy_iteration_evidence_archive.py',
             STRONG / 'resource_development_v1.py', STRONG / 'resource_policy_verification_v1.py']
    files += [builder.PREFLIGHT / name for name in ('check.py', 'check.log', 'receipt.json')]
    files += [file for file in (builder.PREFLIGHT / 'layout/ai/runs').rglob('*') if file.is_file()]
    files += [builder.PREP / name for name in ('prepared.json', 'upload-intent.json', 'upload-receipt.json',
                                               'layout/resource-job-manifest.json')]
    review = {'complete_preflight': True, 'source': source, 'proof': proof,
              'collector_sha256': digest(__file__), 'runtime_admitted': False,
              'development_admitted': False, 'new_hf_jobs': 0, 'new_games': 0, 'gradients': False,
              'qualification_eligible': False, 'reserved_final_seeds_used': False,
              'scope': 'Execution-boundary checks only. The three ReachedEvaluation records are intentional local preflight stops, not failed HF jobs or game results. The complete local resource pilot and measured HF calibration remain required before the strength screen.'}
    OUT.mkdir()
    for file in sorted(set(files)):
        assert file.is_file() and not file.is_symlink()
        target = OUT / file.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file, target)
        assert digest(file) == digest(target)
    write(OUT / 'review.json', review)
    write(OUT / 'manifest.json', {str(file.relative_to(OUT)): digest(file)
                                 for file in sorted(OUT.rglob('*')) if file.is_file()})
    descriptor = {**review, **upload_evidence(OUT)}
    write(DESCRIPTOR, descriptor)
    print({key: descriptor[key] for key in ('revision', 'archive_path', 'archive_sha256', 'archived_files',
                                           'remote_archive_verified', 'runtime_admitted', 'new_hf_jobs')}, flush=True)


if __name__ == '__main__':
    main()
