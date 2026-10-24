"""Archive the prespecified next experiment and its inference-only checks."""
import shutil
from huggingface_hub import HfApi, hf_hub_download
from strategic_collection import ROOT, read, write, digest


def main():
    report = read(ROOT/'ai/strong/policy-iteration-training-preflight-v2.json')
    assert report['complete'] and not report['gradient_loop_executed']
    assert report['design_sha256'] == digest(ROOT/'ai/strong/policy-iteration-training-design-v2.json')
    for file, sha in report['code'].items():
        assert digest(ROOT/'ai/strong'/file) == sha
    for name in ['policy-iteration-data-preflight-v2.json', 'policy-iteration-model-preflight-v2.json']:
        for file, sha in read(ROOT/'ai/strong'/name)['code'].items():
            path = ROOT/file if file.startswith('ai/') else ROOT/'ai/strong'/file
            assert digest(path) == sha
    files = ['policy-iteration-training-design-v2.json', 'policy-iteration-training-preflight-v2.json',
             'policy-iteration-data-preflight-v2.json', 'policy-iteration-model-preflight-v2.json',
             'policy-iteration-feature-cache-results-v2.json', 'policy-iteration-feature-cache-evidence-v2.json',
             'policy-iteration-labels-source-v2.json', 'policy-iteration-labels-protocol-v2.json',
             'model_policy_iteration.py', 'policy_iteration_data.py', 'policy_iteration_training.py',
             'policy_iteration_check.py', 'prepare-policy-iteration-training-data.py', 'train-policy-iteration.py',
             'export-policy-iteration.py', 'preflight-policy-iteration-data.py', 'preflight-policy-iteration-model.py',
             'test_model_policy_iteration.py', 'test_policy_iteration_training.py', 'archive-policy-iteration-preparation.py']
    out = ROOT/'ai/runs/policy-iteration-training-preparation-evidence-v2'
    out.mkdir(exist_ok=False)
    for file in files:
        shutil.copy2(ROOT/'ai/strong'/file, out/file)
    write(out/'manifest.json', {f.name: digest(f) for f in out.iterdir()})
    repo, prefix = 'coyotte508/powergrid-ai-germany-v1', 'runs/' + out.name
    commit = HfApi().upload_folder(repo_id=repo, folder_path=out, path_in_repo=prefix)
    sha = digest(out/'manifest.json')
    assert digest(hf_hub_download(repo, prefix+'/manifest.json', revision=commit.oid)) == sha
    descriptor = {'repo': repo, 'revision': commit.oid, 'prefix': prefix,
                  'manifest_sha256': sha, 'file_count': len(files), 'design_sha256': report['design_sha256'],
                  'gradient_loop_executed': False, 'hf_training_source_built': False, 'qualification_eligible': False}
    write(ROOT/'ai/strong/policy-iteration-training-preparation-evidence-v2.json', descriptor)
    print(descriptor, flush=True)


if __name__ == '__main__':
    main()
