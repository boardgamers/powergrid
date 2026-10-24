"""Package four frozen, untrained architecture fixtures for target CPU timing."""
import shutil
import tarfile
import tempfile

from huggingface_hub import hf_hub_download
from strategic_collection import ROOT, read, write, digest


def main():
    source = read(ROOT/'ai/strong/policy-iteration-development-source-v2.json')
    evidence = read(ROOT/'ai/strong/policy-iteration-development-preparation-evidence-v2.json')
    preflight = read(ROOT/'ai/strong/policy-iteration-development-preflight-v2.json')
    assert evidence['source'] == source == preflight['source'] and preflight['passed']
    out = ROOT/'ai/runs/policy-iteration-8840u-prepared-v2'
    out.mkdir(exist_ok=False)
    archive = hf_hub_download('coyotte508/powergrid-ai-training-v1', source['archive'],
                              repo_type='dataset', revision=source['revision'])
    assert digest(archive) == source['sha256']
    runtime = out/'frozen-source'
    runtime.mkdir()
    with tarfile.open(archive) as bundle:
        bundle.extractall(runtime, filter='data')
    strong = ['infer.py', 'worker.cjs', 'encoders.cjs', 'feature_contract.py', 'search_scope.py',
              'features.cjs', 'features-v3_0.cjs', 'features-v4.cjs', 'features-v4_1.cjs',
              'features-v4_1_control.cjs', 'features-v4_2.cjs', 'features-v4_3.cjs',
              'economics.cjs', 'economics-v3_0.cjs', 'economics-v4_1.cjs', 'spatial.cjs',
              'public-graph.cjs', 'geographic-proposals.cjs', 'search.cjs']
    copied = ['ai/core.cjs', 'ai/infer.py'] + ['ai/strong/'+name for name in strong]
    models = {}
    for key in ['frozen-0', 'frozen-1', 'public-0', 'public-1']:
        pin = dict(preflight['cases'][key+'-2p']['model_pin'])
        assert pin['synthetic_untrained'] and pin['training_verified'] is False
        pin.update(revision=evidence['revision'], prefix=evidence['prefix']+'/synthetic-fixtures/'+key)
        model = hf_hub_download(pin['repo'], pin['prefix']+'/inference64.onnx', revision=pin['revision'])
        assert digest(model) == pin['files']['inference64.onnx']
        with tempfile.TemporaryDirectory() as temp:
            package = __import__('pathlib').Path(temp)
            shutil.copytree(runtime/'engine', package/'engine')
            for file in copied:
                target = package/file
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(runtime/file, target)
                assert digest(target) == digest(runtime/file)
            shutil.copy2(ROOT/'ai/requirements-serve.txt', package/'ai/requirements-serve.txt')
            shutil.copy2(model, package/'policy.onnx')
            (package/'serve.py').write_text('''import hashlib,json,os,sys
from pathlib import Path
root=Path(__file__).resolve().parent
assert len(sys.argv)==1
manifest=json.loads((root/'manifest.json').read_text())
model=root/'policy.onnx'
assert hashlib.sha256(model.read_bytes()).hexdigest()==manifest['model_sha256']
os.execv(sys.executable,[sys.executable,str(root/'ai/strong/infer.py'),str(model),'--search-samples','0','--search-scope','all'])
''')
            (package/'START.txt').write_text('Untrained Powergrid architecture fixture for CPU cost measurement only. No model strength or production claim. Run serve.py with JSONL requests on stdin. Requires Node24, Python3.11/3.12 and ai/requirements-serve.txt.\n')
            manifest = {'model_sha256': digest(model), 'model_repository_revision': pin['revision'],
                        'feature_revision': pin['feature_revision'], 'schema': 4, 'source': source,
                        'synthetic_untrained': True, 'qualification_eligible': False,
                        'search_samples': 0, 'geographic_search': False, 'search_scope': 'all',
                        'files': {str(p.relative_to(package)): digest(p) for p in package.rglob('*') if p.is_file()}}
            for file, sha in manifest['files'].items():
                if file.startswith('engine/') or file in copied:
                    assert digest(runtime/file) == sha
            write(package/'manifest.json', manifest)
            shutil.copy2(package/'manifest.json', out/(key+'-package-manifest.json'))
            with tarfile.open(out/(key+'.tgz'), 'w:gz') as bundle:
                for file in sorted(package.rglob('*')):
                    if file.is_file():
                        bundle.add(file, arcname=str(file.relative_to(package)))
            models[key] = {'pin': pin, 'package_sha256': digest(out/(key+'.tgz')),
                           'package_manifest_sha256': digest(package/'manifest.json')}
    for name in ['probe-strategic-packages-8840u.py', 'probe-search-transfer-8840u.py']:
        shutil.copy2(ROOT/'ai/strong'/name, out/name)
    shutil.copy2(runtime/'ai/strong/fixtures/multiplayer-serving-v1.jsonl', out/'fixtures.jsonl')
    manifest = {'source': source, 'models': models,
                'harness_sha256': digest(out/'probe-strategic-packages-8840u.py'),
                'helper_sha256': digest(out/'probe-search-transfer-8840u.py'),
                'fixtures_sha256': digest(out/'fixtures.jsonl'), 'synthetic_untrained': True,
                'gradients': False, 'qualification_eligible': False,
                'scope': 'Engineering CPU cost of four prespecified untrained ensemble architectures on actual AMD8840U, all2553 public fixtures each. Not trained candidates, model strength, final qualification, browser performance or production routing.'}
    write(out/'manifest.json', manifest)
    print({'prepared': str(out), 'models': len(models), 'requests': 10212,
           'manifest_sha256': digest(out/'manifest.json'), 'synthetic_untrained': True}, flush=True)


if __name__ == '__main__':
    main()
