"""Freeze and control-check the full-data wrapper without changing its engine."""
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

from huggingface_hub import HfApi, hf_hub_download
from strategic_collection import ROOT, read, write, digest

NAMES = ['policy_iteration_labels.py', 'preflight-policy-iteration-labels.py',
         'policy-iteration-labels-protocol-v2.json', 'profile-policy-iteration-continuations.py']


def main():
    p = read(ROOT/'ai/strong/policy-iteration-labels-protocol-v2.json')
    helper = 'ai/strong/profile-policy-iteration-continuations.py'
    assert digest(ROOT/helper) == p['inference_profile']['source']['overlays'][helper]
    base = p['base_source']
    archive = Path(hf_hub_download('coyotte508/powergrid-ai-training-v1', base['archive'], repo_type='dataset', revision=base['revision']))
    assert digest(archive) == base['sha256']
    out = ROOT/'ai/runs/policy-iteration-labels-source-v2'
    out.mkdir(exist_ok=False)
    with tarfile.open(archive) as bundle:
        bundle.extractall(out, filter='data')
    before = {str(f.relative_to(out)): digest(f) for f in out.rglob('*') if f.is_file()}
    overlays = {}
    for name in NAMES:
        rel = 'ai/strong/' + name
        assert rel not in before
        shutil.copy2(ROOT/rel, out/rel)
        overlays[rel] = digest(out/rel)
    logs = out/'ai/runs/full-label-source-checks-v2'
    logs.mkdir(parents=True)
    with (logs/'preflight.log').open('w') as log:
        subprocess.run([sys.executable, '-u', 'ai/strong/preflight-policy-iteration-labels.py'], cwd=out,
                       stdout=log, stderr=subprocess.STDOUT, check=True)
    check = read(out/'ai/runs/policy-iteration-labels-preflight-v2/preflight.json')
    assert check['passed'] and check['exact_pilot_controls'] == 8 and check['new_root_controls'] == 2
    assert check['full_96_world_pilot_controls'] == 1
    assert check['planned_root_mode_pairs'] == 34560
    assert all(digest(out/file) == sha for file, sha in before.items())
    assert all(digest(out/file) == sha for file, sha in overlays.items())
    target = ROOT/'ai/runs/strong-source-policy-iteration-labels-20261024-v2.tgz'
    assert not target.exists()
    with tarfile.open(target, 'w:gz') as bundle:
        for file in sorted(set(before) | set(overlays)):
            bundle.add(out/file, arcname=file, recursive=False)
    commit = HfApi().upload_file(repo_id='coyotte508/powergrid-ai-training-v1', repo_type='dataset', path_or_fileobj=target, path_in_repo=target.name)
    source = {'archive': target.name, 'revision': commit.oid, 'sha256': digest(target), 'bytes': target.stat().st_size,
              'base': base, 'overlays': overlays, 'unchanged_base_files': len(before),
              'protocol_sha256': digest(ROOT/'ai/strong/policy-iteration-labels-protocol-v2.json'), 'qualification_eligible': False}
    write(ROOT/'ai/strong/policy-iteration-labels-source-v2.json', source)
    write(ROOT/'ai/strong/policy-iteration-labels-preflight-v2.json', {'passed': True, 'source': source, 'controls': check,
          'logs': {str(f.relative_to(out)): digest(f) for f in logs.iterdir()}, 'gradients': False, 'qualification_eligible': False})
    print({k: v for k, v in source.items() if k not in ['base', 'overlays']}, flush=True)


if __name__ == '__main__':
    main()
