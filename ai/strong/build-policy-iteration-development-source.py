"""Add the new evaluation wrapper; keep all frozen engine/evaluator files intact."""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

from huggingface_hub import HfApi, hf_hub_download
from strategic_collection import ROOT, read, write, digest


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--output', type=Path, help='Fresh scratch tree; retain failed attempts')
    args = parser.parse_args()
    protocol = read(ROOT/'ai/strong/policy-iteration-development-protocol-v2.json')
    base = protocol['base_source']
    assert base == read(ROOT/'ai/strong/policy-iteration-labels-source-v2.json')
    assert digest(ROOT/'ai/strong/final-protocol-multiplayer.json') == protocol['final_protocol_sha256']
    archive = Path(hf_hub_download('coyotte508/powergrid-ai-training-v1', base['archive'], repo_type='dataset', revision=base['revision']))
    assert digest(archive) == base['sha256']
    out = args.output or ROOT/'ai/runs/policy-iteration-development-source-v2'
    out.mkdir(exist_ok=False)
    with tarfile.open(archive) as bundle:
        bundle.extractall(out, filter='data')
    before = {str(f.relative_to(out)): digest(f) for f in out.rglob('*') if f.is_file()}
    assert len(before) == 1434
    names = ['policy_iteration_development.py', 'preflight-policy-iteration-development.py',
             'policy-iteration-development-protocol-v2.json', 'policy-iteration-training-design-v2.json',
             'build-policy-iteration-development-source.py']
    overlays = {}
    for name in names:
        rel = 'ai/strong/'+name
        assert rel not in before
        shutil.copy2(ROOT/rel, out/rel)
        overlays[rel] = digest(out/rel)
    synthetic = ROOT/'ai/runs/policy-iteration-training-source-code-v3/ai/runs/policy-iteration-model-preflight-v2'
    subprocess.run([sys.executable, '-u', 'ai/strong/preflight-policy-iteration-development.py',
                    '--synthetic-root', str(synthetic)], cwd=out, check=True)
    check = read(out/'ai/strong/policy-iteration-development-preflight-v2.json')
    assert check['passed'] and check['games'] == 160 and check['synthetic_admission_rejected']
    assert all(digest(out/file) == sha for file, sha in before.items())
    assert all(digest(out/file) == sha for file, sha in overlays.items())
    target = ROOT/'ai/runs/strong-source-policy-iteration-development-20261024-v2.tgz'
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
              'protocol_sha256': digest(ROOT/'ai/strong/policy-iteration-development-protocol-v2.json'),
              'gradients': False, 'qualification_eligible': False}
    write(ROOT/'ai/strong/policy-iteration-development-source-v2.json', source)
    write(ROOT/'ai/strong/policy-iteration-development-preflight-v2.json', {**check, 'source': source})
    print({k: source[k] for k in ['archive', 'revision', 'sha256']}, flush=True)


if __name__ == '__main__':
    main()
