"""Freeze the next label pilot after complete selected-root and control checks."""
import shutil, subprocess, sys, tarfile
from pathlib import Path
from huggingface_hub import HfApi, hf_hub_download
from strategic_collection import ROOT, read, write, digest

NAMES = ['policy_iteration_teacher.py', 'policy-iteration-belief-traces.cjs',
         'preflight-policy-iteration-teacher.py', 'policy-iteration-teacher-protocol-v2.json']


def main():
    p = read(ROOT/'ai/strong/policy-iteration-teacher-protocol-v2.json'); base = p['base_source']
    selection = read(ROOT/'ai/strong/policy-iteration-selection-results-v2.json')
    assert selection['complete'] and selection['selected_roots'] == p['roots']['count']
    archive = Path(hf_hub_download('coyotte508/powergrid-ai-training-v1', base['archive'], repo_type='dataset', revision=base['revision']))
    assert digest(archive) == base['sha256']
    out = ROOT/'ai/runs/policy-iteration-teacher-source-v2'; out.mkdir(exist_ok=False)
    with tarfile.open(archive) as bundle: bundle.extractall(out, filter='data')
    before = {str(f.relative_to(out)): digest(f) for f in out.rglob('*') if f.is_file()}; overlays = {}
    for name in NAMES:
        rel = 'ai/strong/' + name; assert rel not in before
        shutil.copy2(ROOT/rel, out/rel); overlays[rel] = digest(out/rel)
    rel = p['roots']['file']; assert rel not in before
    (out/rel).parent.mkdir(parents=True, exist_ok=True)
    roots = ROOT/'ai/runs/policy-iteration-selected-v2/roots.jsonl.gz'; assert digest(roots) == p['roots']['sha256']
    shutil.copy2(roots, out/rel); overlays[rel] = digest(out/rel)
    logs = out/'ai/runs/source-checks-v2'; logs.mkdir(parents=True)
    smoke = out/'ai/runs/policy-iteration-teacher-shard-smoke-v2'
    commands = [('controls', [sys.executable, '-u', 'ai/strong/preflight-policy-iteration-teacher.py']),
                ('shard', [sys.executable, '-u', 'ai/strong/policy_iteration_teacher.py', '2', 'parent', 'economic', 'neural_economic', 'probe', str(smoke)]),
                ('verify', [sys.executable, 'ai/strong/policy_iteration_teacher.py', '2', 'parent', 'economic', 'neural_economic', 'probe', str(smoke), '--verify'])]
    for name, command in commands:
        print({'checking': name}, flush=True)
        with (logs/(name+'.log')).open('w') as f: subprocess.run(command, cwd=out, stdout=f, stderr=subprocess.STDOUT, check=True)
    controls = read(out/'ai/runs/policy-iteration-teacher-preflight-v2/preflight.json')
    check = read(smoke/'label-check.json'); independent = read(logs/'verify.log')
    assert controls['passed'] and controls['rollouts'] == 584
    assert check['status'] == 'complete' and check['summary'] == independent and independent['roots'] == 12
    assert all(digest(out/name) == sha for name, sha in before.items())
    assert all(digest(out/name) == sha for name, sha in overlays.items())
    target = ROOT/'ai/runs/strong-source-policy-iteration-teacher-20261024-v2.tgz'; assert not target.exists()
    with tarfile.open(target, 'w:gz') as bundle:
        for name in sorted(set(before) | set(overlays)): bundle.add(out/name, arcname=name, recursive=False)
    c = HfApi().upload_file(repo_id='coyotte508/powergrid-ai-training-v1', repo_type='dataset', path_or_fileobj=target, path_in_repo=target.name)
    source = {'archive': target.name, 'revision': c.oid, 'sha256': digest(target), 'bytes': target.stat().st_size,
              'base': base, 'overlays': overlays, 'unchanged_base_files': len(before),
              'protocol_sha256': digest(ROOT/'ai/strong/policy-iteration-teacher-protocol-v2.json'), 'qualification_eligible': False}
    write(ROOT/'ai/strong/policy-iteration-teacher-source-v2.json', source)
    write(ROOT/'ai/strong/policy-iteration-teacher-preflight-v2.json', {'passed': True, 'source': source,
          'controls': controls, 'shard': independent, 'logs': {str(f.relative_to(out)): digest(f) for f in logs.iterdir()},
          'gradients': False, 'qualification_eligible': False})
    print({k: v for k, v in source.items() if k not in ['overlays', 'base']}, flush=True)


if __name__ == '__main__': main()
