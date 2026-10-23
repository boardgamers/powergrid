"""Freeze the evaluation runtime before candidate results, keeping teacher engine intact."""
import shutil
import subprocess
import sys
import tarfile
from huggingface_hub import HfApi, hf_hub_download
from strategic_collection import ROOT, read, write, digest


def main():
    base = read(ROOT/'ai/strong/strategic-teacher-training-source-v1.json')
    archive = hf_hub_download('coyotte508/powergrid-ai-training-v1', base['archive'],
        repo_type='dataset', revision=base['revision'])
    assert digest(archive) == base['sha256']
    out = ROOT/'ai/runs/strategic-correction-screen-source-v1'
    out.mkdir(exist_ok=False)
    with tarfile.open(archive) as bundle:
        bundle.extractall(out, filter='data')
    before = {str(p.relative_to(out)):digest(p) for p in out.rglob('*') if p.is_file()}
    overlays = {}
    for name in ['evaluate.py', 'encoders.cjs', 'features-v4_3.cjs', 'collect-population-screen.py',
                 'strategic_correction_screen.py', 'preflight-strategic-correction-screen.py',
                 'strategic-correction-screen-protocol-v1.json']:
        relative = 'ai/strong/'+name
        shutil.copy2(ROOT/relative, out/relative)
        overlays[relative] = digest(out/relative)
    unchanged = {name:sha for name,sha in before.items() if name not in overlays}
    for name in ['core.cjs', 'strong/bridge.cjs', 'strong/economics.cjs', 'strong/search.cjs',
                 'strong/features-v4.cjs', 'strong/features-v4_1.cjs', 'strong/features-v4_2.cjs']:
        assert 'ai/'+name in unchanged
    checks = out/'ai/runs'
    checks.mkdir(parents=True)
    with (checks/'preflight.log').open('w') as log:
        subprocess.run([sys.executable, 'ai/strong/preflight-strategic-correction-screen.py',
            str(ROOT/'ai/strong/strategic-correction-screen-pins-v1/parent.json'), 'ai/runs/screen-preflight'],
            cwd=out, stdout=log, stderr=subprocess.STDOUT, check=True)
    assert all(digest(out/name) == sha for name,sha in unchanged.items())
    assert all(digest(out/name) == sha for name,sha in overlays.items())
    target = ROOT/'ai/runs/strong-source-strategic-correction-screen-20261023-v1.tgz'
    assert not target.exists()
    with tarfile.open(target, 'w:gz') as bundle:
        for name in sorted(set(before) | set(overlays)):
            bundle.add(out/name, arcname=name, recursive=False)
    commit = HfApi().upload_file(repo_id='coyotte508/powergrid-ai-training-v1', repo_type='dataset',
        path_or_fileobj=target, path_in_repo=target.name)
    source = {'revision': commit.oid, 'archive': target.name, 'sha256': digest(target),
        'base': {k:base[k] for k in ['revision', 'archive', 'sha256']}, 'overlays': overlays,
        'unchanged_base_file_count': len(unchanged),
        'protocol_sha256': digest(ROOT/'ai/strong/strategic-correction-screen-protocol-v1.json'),
        'model_pins': 'Each job separately pins the exact canonical MODEL_PIN JSON and its SHA256. No checkpoint selection from development results.',
        'qualification_eligible': False}
    write(ROOT/'ai/strong/strategic-correction-screen-source-v1.json', source)
    checked = read(out/'ai/runs/screen-preflight/preflight.json')
    checked.update(source_revision=source['revision'], source_sha256=source['sha256'],
        unchanged_base_file_count=len(unchanged))
    write(ROOT/'ai/strong/strategic-correction-screen-preflight-v1.json', checked)
    print({k:v for k,v in source.items() if k not in ['overlays', 'base']})


if __name__ == '__main__':
    main()
