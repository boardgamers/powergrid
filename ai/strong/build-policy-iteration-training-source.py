"""Preserve all frozen base files and add a gated training package."""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

from huggingface_hub import HfApi, hf_hub_download
from strategic_collection import ROOT, read, write, digest
from policy_iteration_job import complete_inputs, DESIGN, DATA_PIN, MANIFEST

NAMES = [
    'policy-iteration-labels-source-v2.json', 'policy-iteration-training-design-v2.json',
    'model_policy_iteration.py', 'policy_iteration_data.py', 'policy_iteration_training.py',
    'train-policy-iteration.py', 'export-policy-iteration.py', 'policy_iteration_check.py',
    'prepare-policy-iteration-training-data.py', 'archive-policy-iteration-training-data.py',
    'test_model_policy_iteration.py', 'test_policy_iteration_training.py',
    'preflight-policy-iteration-model.py', 'policy_iteration_job.py',
    'preflight-policy-iteration-training-source.py', 'build-policy-iteration-training-source.py',
    'launch-policy-iteration-training.py',
]


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--code-only', action='store_true', help='No data admission, archive or upload')
    parser.add_argument('--output', type=Path, help='Fresh scratch tree; preserve failed earlier attempts')
    args = parser.parse_args()
    if not args.code_only:
        complete_inputs()  # Fail before any network or file mutation on an incomplete grid.
    base = read(ROOT/'ai/strong/policy-iteration-labels-source-v2.json')
    archive = Path(hf_hub_download('coyotte508/powergrid-ai-training-v1', base['archive'],
                                 repo_type='dataset', revision=base['revision']))
    assert digest(archive) == base['sha256']
    suffix = 'code' if args.code_only else 'complete'
    out = args.output or ROOT/('ai/runs/policy-iteration-training-source-'+suffix+'-v2')
    out.mkdir(exist_ok=False)
    with tarfile.open(archive) as bundle:
        bundle.extractall(out, filter='data')
    before = {str(f.relative_to(out)): digest(f) for f in out.rglob('*') if f.is_file()}
    assert len(before) == 1434
    names = NAMES + ([] if args.code_only else [DATA_PIN.name, MANIFEST.name])
    overlays = {}
    for name in names:
        rel = 'ai/strong/'+name
        assert rel not in before, 'Do not overwrite the frozen runtime'
        shutil.copy2(ROOT/rel, out/rel)
        overlays[rel] = digest(out/rel)
    command = [sys.executable, '-u', 'ai/strong/preflight-policy-iteration-training-source.py']
    if args.code_only:
        command += ['--code-only']
    subprocess.run(command, cwd=out, check=True)
    check_rel = 'ai/strong/policy-iteration-training-source-check-v2.json'
    check = read(out/check_rel)
    assert check['passed'] and check['code_only'] == args.code_only and not check['gradients']
    assert all(digest(out/file) == sha for file, sha in before.items())
    assert all(digest(out/file) == sha for file, sha in overlays.items())
    if args.code_only:
        write(ROOT/'ai/strong/policy-iteration-training-source-code-check-v2.json',
              {**check, 'base': base, 'overlays': overlays, 'unchanged_base_files': len(before)})
        print({'code_only': True, 'passed': True, 'training_admitted': False}, flush=True)
        return
    overlays[check_rel] = digest(out/check_rel)
    target = ROOT/'ai/runs/strong-source-policy-iteration-training-20261024-v2.tgz'
    assert not target.exists()
    with tarfile.open(target, 'w:gz') as bundle:
        for file in sorted(set(before) | set(overlays)):
            bundle.add(out/file, arcname=file, recursive=False)
    commit = HfApi().upload_file(repo_id='coyotte508/powergrid-ai-training-v1', repo_type='dataset',
                                path_or_fileobj=target, path_in_repo=target.name)
    assert digest(hf_hub_download('coyotte508/powergrid-ai-training-v1', target.name,
                                repo_type='dataset', revision=commit.oid)) == digest(target)
    source = {'archive': target.name, 'revision': commit.oid, 'sha256': digest(target), 'bytes': target.stat().st_size,
              'base': base, 'overlays': overlays, 'unchanged_base_files': len(before),
              'design_sha256': digest(DESIGN), 'data_pin_sha256': digest(DATA_PIN),
              'data_check_sha256': check['data_check_sha256'], 'label_manifest_sha256': digest(MANIFEST),
              'check_sha256': digest(out/check_rel), 'gradients': False, 'qualification_eligible': False}
    shutil.copy2(out/check_rel, ROOT/check_rel)
    write(ROOT/'ai/strong/policy-iteration-training-source-v2.json', source)
    print({k: source[k] for k in ['archive', 'revision', 'sha256', 'bytes']}, flush=True)


if __name__ == '__main__':
    main()
