"""Prepare and observe one exact learned-opponent benchmark on the AMD 8840U."""
import argparse
import json
from pathlib import Path
import shutil
import statistics
import subprocess
import sys
import tarfile

from strategic_collection import ROOT, read, write, digest

PREP = ROOT/'ai/runs/surrogate-opponent-8840u-prepared-v1'
COLLECTED = ROOT/'ai/runs/surrogate-opponent-8840u-collected-v1'
GUARD = ROOT/'ai/strong/surrogate-opponent-8840u-launch-v1.json'
REMOTE = '/home/coyotte508/powergrid-ai-surrogate-opponent-8840u-v1'
PYTHON = '/home/coyotte508/powergrid-ai-baseline/.venv/bin/python'
RUNNER = ROOT/'ai/strong/run-surrogate-opponent-cpu-v1.py'
SOURCE = ROOT/'ai/strong/surrogate-continuation-study-source-v1.json'
HF_RESULT = ROOT/'ai/strong/surrogate-continuation-selected-cost-results-v1.json'


def prepare():
    assert not PREP.exists() and not GUARD.exists()
    source = read(SOURCE); prior = read(HF_RESULT)
    assert prior['verified'] and prior['authoritative_status'] == 'COMPLETED' and prior['source'] == source
    assert prior['review']['roots'] == 24 and prior['review']['continuations'] == 384 and prior['review']['caps'] == 0
    source_root = ROOT/'ai/runs/surrogate-continuation-study-source-prepared-v1/layout'
    source_manifest = source_root/'surrogate-continuation-study-source-manifest.json'
    hashes = read(source_manifest)
    assert digest(source_manifest) == source['manifest_sha256'] and len(hashes) == source['manifest_files']
    assert all(digest(source_root/name) == sha for name, sha in hashes.items())
    package = PREP/'package'; package.mkdir(parents=True)
    for name in [*hashes, source_manifest.name]:
        target = package/name; target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source_root/name, target)
    focal = ROOT/'ai/runs/policy-iteration-trained-8840u-prepared-v2/local-package-frozen-1/policy.onnx'
    shutil.copy2(focal, package/'focal.onnx'); shutil.copy2(RUNNER, package/'benchmark.py')
    reference = ROOT/'ai/runs/surrogate-continuation-selected-cost-collected-v1/artifacts'
    prior_manifest = read(reference/'manifest.json')
    assert digest(reference/'manifest.json') == prior['evidence']['manifest_sha256']
    assert all(digest(reference/name) == sha for name, sha in prior_manifest.items())
    shutil.copytree(reference, package/'hf-reference')
    manifest = {'source': source, 'hf_reference_evidence': prior['evidence'],
        'hf_result_sha256': digest(HF_RESULT), 'runner_sha256': digest(RUNNER),
        'focal_model_sha256': digest(focal), 'surrogate_policy_sha256': source['surrogate_policy_sha256'],
        'roots': 24, 'continuations': 384, 'workers': 8, 'inference_threads': 1,
        'required_cpu': '8840U', 'huggingface_hub_import_version': '2.0.0',
        'files': {str(p.relative_to(package)): digest(p) for p in package.rglob('*') if p.is_file()},
        'gradients': False, 'qualification_eligible': False, 'reserved_final_seeds_used': False}
    write(package/'benchmark-manifest.json', manifest)
    with tarfile.open(PREP/'package.tgz', 'w:gz') as bundle:
        for p in sorted(package.rglob('*')):
            if p.is_file():
                bundle.add(p, arcname=str(p.relative_to(package)))
    record = {'package_sha256': digest(PREP/'package.tgz'),
              'manifest_sha256': digest(package/'benchmark-manifest.json'), 'runner_sha256': digest(RUNNER),
              'source_manifest_sha256': source['manifest_sha256'], 'source_files_unchanged': len(hashes),
              'files': len(manifest['files']), 'qualification_eligible': False}
    write(PREP/'prepared.json', record); print(record, flush=True)


def launch():
    assert not GUARD.exists()
    prepared = read(PREP/'prepared.json')
    assert digest(PREP/'package.tgz') == prepared['package_sha256'] and digest(RUNNER) == prepared['runner_sha256']
    record = {'stage': 'launch_intent', 'host': 'minipc', 'directory': REMOTE, **prepared,
              'new_hf_jobs': 0, 'gradients': False, 'qualification_eligible': False}
    with GUARD.open('x') as stream:
        json.dump(record, stream, indent=2)
    try:
        subprocess.run(['scp', '-q', str(PREP/'package.tgz'), 'minipc:'+REMOTE+'.tgz'], check=True)
        script = f'''import subprocess,tarfile,json,hashlib,os
from pathlib import Path
root=Path({REMOTE!r});archive=Path({(REMOTE+'.tgz')!r});assert not root.exists()
assert hashlib.sha256(archive.read_bytes()).hexdigest()=={prepared['package_sha256']!r}
root.mkdir()
with tarfile.open(archive) as bundle:bundle.extractall(root,filter='data')
# A separate import dependency directory leaves the existing target environment unchanged.
with (root/'dependency-install.log').open('x') as log:
    subprocess.run([{PYTHON!r},'-m','pip','install','--disable-pip-version-check','--target',str(root/'dependencies'),'huggingface_hub==2.0.0'],stdout=log,stderr=subprocess.STDOUT,check=True)
env={{**os.environ,'PYTHONPATH':str(root/'dependencies'),'PYTHONDONTWRITEBYTECODE':'1','HF_HUB_OFFLINE':'1'}}
with (root/'run.log').open('x') as log:
    child=subprocess.Popen([{PYTHON!r},'-u','-B',str(root/'benchmark.py'),'--package',str(root),'--output',str(root/'output'),'--require-cpu','8840U'],cwd='/tmp',env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
value={{'pid':child.pid,'directory':str(root)}}
(root/'target-launch.json').write_text(json.dumps(value))
print(json.dumps(value))
'''
        response = subprocess.run(['ssh', '-o', 'BatchMode=yes', 'minipc', 'python3 -'],
                                  input=script, text=True, capture_output=True, check=True)
        remote = json.loads(response.stdout); record.update(stage='launched', pid=remote['pid'])
    except BaseException as error:
        record.update(stage='launch_unknown', error=type(error).__name__+': '+str(error)); raise
    finally:
        write(GUARD, record)
    print(record, flush=True)


def inspect():
    guard = read(GUARD); assert guard['stage'] == 'launched'
    script = f'''import json
from pathlib import Path
root=Path({REMOTE!r});proc=Path('/proc')/{str(guard['pid'])!r};state=root/'output/status.json'
command=(proc/'cmdline').read_bytes() if (proc/'cmdline').exists() else b''
value={{'pid':{guard['pid']},'process_present':proc.exists(),'command_matches':str(root/'benchmark.py').encode() in command,'status':json.loads(state.read_text()) if state.exists() else None,'log_tail':(root/'run.log').read_text()[-3000:]}}
print(json.dumps(value))
'''
    response = subprocess.run(['ssh', '-o', 'BatchMode=yes', 'minipc', 'python3 -'],
                              input=script, text=True, capture_output=True, check=True)
    state = json.loads(response.stdout); write(PREP/'last-target-status.json', state)
    print({k: state[k] for k in ('pid', 'process_present', 'command_matches', 'log_tail')}, flush=True)
    if state['status']:
        print({k: state['status'][k] for k in ('stage', 'processor', 'passed', 'seconds') if k in state['status']}, flush=True)
    return state


def collect():
    observed = inspect(); status = observed['status']
    assert status and status['stage'] == 'completed' and status['passed']
    assert not observed['command_matches'], 'Wait for this original benchmark process to exit'
    assert not COLLECTED.exists(); COLLECTED.mkdir()
    for name in ['output', 'run.log', 'dependency-install.log', 'target-launch.json']:
        subprocess.run(['scp', '-qr', 'minipc:'+REMOTE+'/'+name, str(COLLECTED)], check=True)
    out = COLLECTED/'output'; target = read(out/'status.json'); manifest = read(PREP/'package/benchmark-manifest.json')
    assert target == status and '8840U' in target['processor']
    assert target['manifest_sha256'] == digest(PREP/'package/benchmark-manifest.json')
    assert target['roots'] == 24 and target['continuations'] == 384 and target['caps'] == 0
    assert all(digest(out/name) == sha for name, sha in target['output_hashes'].items())
    # Re-run the original independent saved-outcome verifier locally, without inference.
    verify_script = '''import sys,json
from pathlib import Path
package=Path(sys.argv[1]);out=Path(sys.argv[2]);sys.path.insert(0,str(package/'ai/strong'))
import surrogate_continuation_selected_cost_v1 as cost
from surrogate_continuation_job_v1 import source_check,validate_inputs
from surrogate_continuation_study_v1 import policy_digest
source_check();roots=cost.runtime_roots();_,_,_,selected=validate_inputs()
check=cost.verify(out/'continuations',roots,policy_digest(selected));assert check['complete'] and check['caps']==0
for key in roots:
 actual=json.loads((out/'continuations'/key/'result.json').read_text());reference=json.loads((package/'hf-reference'/key/'result.json').read_text())
 assert {k:v for k,v in actual.items() if k!='seconds'}=={k:v for k,v in reference.items() if k!='seconds'}
print(json.dumps({'roots':len(roots),'continuations':384,'all_saved_receipts_exact':True}))
'''
    with (COLLECTED/'independent-audit.log').open('x') as log:
        subprocess.run([sys.executable, '-B', '-c', verify_script, str(PREP/'package'), str(out)],
                       cwd='/tmp', stdout=log, stderr=subprocess.STDOUT, check=True,
                       env={**__import__('os').environ, 'PYTHONDONTWRITEBYTECODE': '1'})
    measurements = target['measurements']; seconds = [v['seconds'] for v in measurements.values()]
    assessment = {'complete': True, 'processor': target['processor'], 'target_status_sha256': digest(out/'status.json'),
        'roots': 24, 'continuations': 384, 'caps': 0, 'all_saved_receipts_exact': True,
        'component_batch_seconds_median': statistics.median(seconds), 'component_batch_seconds_max': max(seconds),
        'total_cpu_seconds': sum(v['cpu_seconds'] for v in measurements.values()),
        'max_sampled_total_rss_bytes': max(v['sampled_peak_total_rss_bytes'] for v in measurements.values()),
        'by_player_count': {str(n): {'roots': 12, 'median_seconds': statistics.median(v['seconds'] for k, v in measurements.items() if k.startswith(str(n)+'p-')),
                                   'max_seconds': max(v['seconds'] for k, v in measurements.items() if k.startswith(str(n)+'p-'))} for n in (2, 6)},
        'manifest_sha256': target['manifest_sha256'], 'surrogate_policy_sha256': manifest['surrogate_policy_sha256'],
        'focal_model_sha256': manifest['focal_model_sha256'], 'scope': target['scope'],
        'new_hf_jobs': 0, 'gradients': False, 'qualification_eligible': False, 'reserved_final_seeds_used': False}
    write(COLLECTED/'assessment.json', assessment); print(assessment, flush=True)


def archive():
    from policy_iteration_evidence_archive import upload_evidence
    assessment = read(COLLECTED/'assessment.json'); assert assessment['complete']
    out = ROOT/'ai/runs/surrogate-opponent-8840u-evidence-v1'; assert not out.exists(); out.mkdir()
    files = [Path(__file__), RUNNER, GUARD, SOURCE, HF_RESULT, PREP/'package.tgz', PREP/'prepared.json',
             PREP/'package/benchmark-manifest.json', PREP/'last-target-status.json']
    files += [p for p in COLLECTED.rglob('*') if p.is_file()]
    for source in files:
        target = out/source.relative_to(ROOT); target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source, target)
        assert digest(source) == digest(target)
    write(out/'assessment.json', assessment)
    write(out/'manifest.json', {str(p.relative_to(out)): digest(p) for p in out.rglob('*') if p.is_file()})
    receipt = upload_evidence(out)
    descriptor = {**assessment, 'runtime_manifest_sha256': assessment['manifest_sha256'], 'archive': receipt,
                  'assessment_sha256': digest(out/'assessment.json')}
    write(ROOT/'ai/strong/surrogate-opponent-8840u-evidence-v1.json', descriptor); print(receipt, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('operation', choices=['prepare', 'launch', 'inspect', 'collect', 'archive'])
    globals()[parser.parse_args().operation]()
