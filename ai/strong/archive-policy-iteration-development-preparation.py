"""Save the complete runner preflight, synthetic fixtures and exact live probes."""
from pathlib import Path
import shutil
from huggingface_hub import HfApi, hf_hub_download
from strategic_collection import ROOT, read, write, digest


def main():
    source = read(ROOT/'ai/strong/policy-iteration-development-source-v2.json')
    preflight = read(ROOT/'ai/strong/policy-iteration-development-preflight-v2.json')
    status = read(ROOT/'ai/strong/policy-iteration-development-status-v2.json')
    labels = read(ROOT/'ai/strong/policy-iteration-labels-results-v2.json')
    assert preflight['passed'] and preflight['games'] == 160 and preflight['source'] == source
    assert len(status['jobs']) == 2 and {j['players'] for j in status['jobs']} == {2, 6}
    assert all(j['key'] == 'parent' and j['mode'] == 'smoke' and j['stage'] == 'launched' for j in status['jobs'])
    out = ROOT/'ai/runs/policy-iteration-development-preparation-evidence-v2'
    out.mkdir(exist_ok=False)
    names = ['policy-iteration-development-source-v2.json', 'policy-iteration-development-preflight-v2.json',
             'policy-iteration-development-protocol-v2.json', 'policy-iteration-development-status-v2.json',
             'policy-iteration-development-job-controls-v2.json', 'manage-policy-iteration-development.py',
             'archive-policy-iteration-development-preparation.py', 'policy-iteration-labels-results-v2.json',
             'policy-iteration-labels-status-v2.json', 'policy-iteration-capacity-checkpoint-v2.json']
    for name in names:
        shutil.copy2(ROOT/'ai/strong'/name, out/name)
    for rel, sha in source['overlays'].items():
        assert digest(ROOT/rel) == sha
        destination = out/'code'/rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT/rel, destination)
    for name in ['policy-iteration-development-source-v2', 'policy-iteration-development-source-v3']:
        shutil.copytree(ROOT/'ai/runs'/name/'ai/runs/policy-iteration-development-preflight-v2', out/name)
    for file in (ROOT/'ai/runs/policy-iteration-development-launches-v2').glob('*.json'):
        destination = out/'guards'/file.name
        destination.parent.mkdir(exist_ok=True)
        shutil.copy2(file, destination)
    synthetic = ROOT/'ai/runs/policy-iteration-training-source-code-v3/ai/runs/policy-iteration-model-preflight-v2'
    for key in ['frozen-0', 'frozen-1', 'public-0', 'public-1']:
        pin = preflight['cases'][key+'-2p']['model_pin']
        assert pin['synthetic_untrained'] and not pin['training_verified']
        for file in ['inference64.pt', 'inference64.onnx']:
            assert digest(synthetic/key/file) == pin['files'][file]
            destination = out/'synthetic-fixtures'/key/file
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(synthetic/key/file, destination)
    for key, case in labels['cases'].items():
        file = ROOT/'ai/runs/policy-iteration-labels-verified-v2'/key/'verified.json'
        assert digest(file) == case['verified_sha256']
        destination = out/'verified-labels'/(key+'.json')
        destination.parent.mkdir(exist_ok=True)
        shutil.copy2(file, destination)
    write(out/'manifest.json', {str(f.relative_to(out)): digest(f) for f in out.rglob('*') if f.is_file()})
    repo, prefix = 'coyotte508/powergrid-ai-germany-v1', 'runs/'+out.name
    commit = HfApi().upload_folder(repo_id=repo, folder_path=out, path_in_repo=prefix)
    sha = digest(out/'manifest.json')
    assert digest(hf_hub_download(repo, prefix+'/manifest.json', revision=commit.oid)) == sha
    result = {'repo': repo, 'revision': commit.oid, 'prefix': prefix, 'manifest_sha256': sha,
              'source': source, 'plumbing_games': 160, 'models_are_synthetic_or_parent': True,
              'new_candidate_development_games': 0, 'live_parent_probe_handles': [j['job_id'] for j in status['jobs']],
              'parent_probe_status_checked_at': status['checked_at'], 'parent_probe_status_counts': status['status_counts'],
              'verified_label_shards': labels['complete_shards'], 'label_rollouts_including_pilot': labels['rollouts'],
              'gradients': False, 'reserved_final_seeds_used': False, 'qualification_eligible': False}
    write(ROOT/'ai/strong/policy-iteration-development-preparation-evidence-v2.json', result)
    print({k: v for k, v in result.items() if k != 'source'}, flush=True)


if __name__ == '__main__':
    main()
