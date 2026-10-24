"""Freeze a measured inference-concurrency experiment, separate from labeling."""
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

from huggingface_hub import HfApi, hf_hub_download
from strategic_collection import ROOT, read, write, digest


def main():
    old = read(ROOT/'ai/strong/policy-iteration-teacher-protocol-v2.json')
    base = read(ROOT/'ai/strong/policy-iteration-teacher-source-v2.json')
    roots = []
    for n in [2, 6]:
        choices = [r for r in old['pilot_roots'] if r['players'] == n and r['decision'] == 'nomination' and r['round'] <= 4]
        roots.append(min(choices, key=lambda r: hashlib.sha256(('concurrency-profile-v2:' + r['rootId']).encode()).hexdigest())['rootId'])
    protocol = ROOT/'ai/strong/policy-iteration-inference-profile-protocol-v2.json'
    assert not protocol.exists()
    write(protocol, {'root_ids': roots, 'teacher_protocol_sha256': digest(ROOT/'ai/strong/policy-iteration-teacher-protocol-v2.json'),
                     'threads': [1, 4], 'fixed_inference_batch': 64, 'modes': old['modes'], 'samples': 96,
                     'control_samples': 2, 'max_steps': 2400, 'workers': 24,
                     'purpose': 'Inference-only concurrency profiling; require exact full policy-choice transcripts and terminal outcomes. No trained model or teacher change is admitted by this experiment.',
                     'qualification_eligible': False})
    archive = Path(hf_hub_download('coyotte508/powergrid-ai-training-v1', base['archive'], repo_type='dataset', revision=base['revision']))
    assert digest(archive) == base['sha256']
    out = ROOT/'ai/runs/policy-iteration-inference-profile-source-v2'
    out.mkdir(exist_ok=False)
    with tarfile.open(archive) as bundle:
        bundle.extractall(out, filter='data')
    before = {str(f.relative_to(out)): digest(f) for f in out.rglob('*') if f.is_file()}
    overlays = {}
    for name in ['profile-policy-iteration-inference.py', 'profile-policy-iteration-continuations.py', protocol.name]:
        rel = 'ai/strong/' + name
        assert rel not in before
        shutil.copy2(ROOT/rel, out/rel)
        overlays[rel] = digest(out/rel)
    logs = out/'ai/runs/inference-profile-checks-v2'
    logs.mkdir(parents=True)
    with (logs/'control.log').open('w') as log:
        subprocess.run([sys.executable, '-u', 'ai/strong/profile-policy-iteration-continuations.py',
                        str(logs/'controls'), '--small'], cwd=out, stdout=log, stderr=subprocess.STDOUT, check=True)
    control = read(logs/'controls/profile.json')
    assert control['passed'] and control['small'] and len(control['records']) == 4
    assert all(digest(out/f) == sha for f, sha in before.items())
    assert all(digest(out/f) == sha for f, sha in overlays.items())
    target = ROOT/'ai/runs/strong-source-policy-iteration-inference-profile-20261024-v2.tgz'
    assert not target.exists()
    with tarfile.open(target, 'w:gz') as bundle:
        for file in sorted(set(before) | set(overlays)):
            bundle.add(out/file, arcname=file, recursive=False)
    commit = HfApi().upload_file(repo_id='coyotte508/powergrid-ai-training-v1', repo_type='dataset', path_or_fileobj=target, path_in_repo=target.name)
    source = {'archive': target.name, 'revision': commit.oid, 'sha256': digest(target), 'bytes': target.stat().st_size,
              'base': {k: base[k] for k in ['archive', 'revision', 'sha256']}, 'overlays': overlays,
              'unchanged_base_files': len(before), 'protocol_sha256': digest(protocol), 'qualification_eligible': False}
    write(ROOT/'ai/strong/policy-iteration-inference-profile-source-v2.json', source)
    write(ROOT/'ai/strong/policy-iteration-inference-profile-preflight-v2.json', {'passed': True, 'source': source, 'control': control})
    print({k: v for k, v in source.items() if k not in ['base', 'overlays']}, flush=True)


if __name__ == '__main__':
    main()
