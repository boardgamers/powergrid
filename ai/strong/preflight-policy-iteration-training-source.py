"""Exercise the packaged dependency closure; never run gradients here."""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys

from huggingface_hub import hf_hub_download
from strategic_collection import ROOT, read, write, digest
from policy_iteration_job import DESIGN, DATA_PIN, MANIFEST, recover_data


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--code-only', action='store_true')
    args = parser.parse_args()
    design = read(DESIGN)
    result = {'passed': False, 'code_only': args.code_only, 'design_sha256': digest(DESIGN),
              'gradients': False, 'qualification_eligible': False}
    if not args.code_only:
        data_dir = ROOT/'ai/runs/policy-iteration-training-data-v2'
        data, metadata, report = recover_data(data_dir)
        result.update(data_pin_sha256=digest(DATA_PIN), data_check_sha256=digest(data_dir/'data-check.json'),
                      label_manifest_sha256=digest(MANIFEST), positions=len(metadata), split_counts=report['split_counts'])
        del data, metadata
    features = ROOT/'ai/runs/policy-iteration-features-v2'
    features.mkdir(parents=True, exist_ok=True)
    for file in ['features.npz', 'metadata.json', 'feature-check.json']:
        pin = design['features']
        path = Path(hf_hub_download(pin['repo'], pin['prefix']+'/'+file, revision=pin['revision']))
        assert digest(path) == pin['files'][file]
        if (features/file).exists():
            assert digest(features/file) == pin['files'][file]
        else:
            shutil.copy2(path, features/file)
    logs = ROOT/'ai/runs/policy-iteration-training-source-checks-v2'
    logs.mkdir(exist_ok=False)
    scripts = ['test_model_policy_iteration.py', 'preflight-policy-iteration-model.py', 'test_policy_iteration_training.py']
    for script in scripts:
        with (logs/(script+'.log')).open('w') as stream:
            subprocess.run([sys.executable, '-u', 'ai/strong/'+script], cwd=ROOT, stdout=stream,
                           stderr=subprocess.STDOUT, check=True)
        print({'source_check_passed': script}, flush=True)
    result.update(passed=True, model_preflight=read(ROOT/'ai/strong/policy-iteration-model-preflight-v2.json'),
                  logs={str(f.relative_to(ROOT)): digest(f) for f in logs.iterdir()})
    write(ROOT/'ai/strong/policy-iteration-training-source-check-v2.json', result)
    print({k: v for k, v in result.items() if k not in ['model_preflight', 'logs']}, flush=True)


if __name__ == '__main__':
    main()
