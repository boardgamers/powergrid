"""One separate shutdown diagnostic; never replaces the original timing job."""
import ast
import hashlib
import importlib.util
from pathlib import Path
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'ai/strong'))
from strategic_collection import read, write, digest
from huggingface_hub import HfApi, get_token

CASE = 'surrogate-runtime-exit-diagnostic-v1'
GUARD = ROOT/'ai/runs'/f'{CASE}-launch.json'
spec = importlib.util.spec_from_file_location('timing_manager', ROOT/'ai/strong/manage-surrogate-continuation-selected-cost-v1.py')
manager = importlib.util.module_from_spec(spec)
spec.loader.exec_module(manager)

DIAGNOSTIC = r'''
import atexit, faulthandler, os, sys, threading, time
from pathlib import Path
sys.path.insert(0, str(Path('/workspace/ai/strong')))
faulthandler.enable()
faulthandler.dump_traceback_later(60, repeat=True)
def event(stage):
    print({'diagnostic_stage': stage, 'threads': [{'name': t.name, 'daemon': t.daemon} for t in threading.enumerate()]}, flush=True)
def exiting():
    event('atexit-reached')
    faulthandler.cancel_dump_traceback_later()
atexit.register(exiting)
event('started')
from huggingface_hub import hf_hub_download
from strategic_collection import ROOT, read, write, digest
from hybrid_search import Model
from opponent_surrogate_policy_v1 import SurrogatePolicy
from surrogate_continuation_selected_cost_v1 import source_check, runtime_roots, validate_inputs, MEMBERS, resources
from surrogate_continuation_study_v1 import run_chunk, verify_chunk, policy_digest
from policy_iteration_evidence_archive import upload_evidence

def main():
    before = source_check()
    roots = runtime_roots()
    frozen, _, _, policy = validate_inputs()
    os.environ['PG_REFERENCE_RUNTIME'] = str(ROOT)
    assert not os.environ.get('NODE_OPTIONS')
    pin = resources.MODEL_PIN
    focal = Model(hf_hub_download(pin['repo'], pin['path'], revision=pin['revision']), threads=1)
    surrogate = SurrogatePolicy(policy, MEMBERS)
    event('models-loaded')
    out = ROOT/'ai/runs/surrogate-runtime-exit-diagnostic-v1'
    out.mkdir(parents=True, exist_ok=False)
    root = roots['6p-3-bid']
    began = time.perf_counter()
    run_chunk(root, 'surrogate_opponent_v1', 0, 8, focal, surrogate, out/'engineering-probe',
              workers=8, surrogate_sha256=policy_digest(policy))
    checked = verify_chunk(out/'engineering-probe', root, surrogate_sha256=policy_digest(policy))
    event('engine-pool-closed')
    assert before == source_check()
    report = {'purpose': 'Isolated process-shutdown diagnostic, not a replacement timing or scientific study.',
              'root': '6p-3-bid', 'engineering_continuations': 16, 'fresh_scientific_continuations': 0,
              'caps': checked['caps'], 'seconds': time.perf_counter()-began,
              'source_sha256': os.environ['SOURCE_SHA256'], 'policy_sha256': policy_digest(policy),
              'frozen_inputs_sha256': os.environ['STUDY_INPUTS_SHA256'], 'gradients': False,
              'original_timing_job': '6adda6dd1e112550ce7e86c1', 'original_job_changed': False,
              'qualification_eligible': False, 'reserved_final_seeds_used': False}
    write(out/'diagnostic.json', report)
    write(out/'manifest.json', {str(p.relative_to(out)): digest(p) for p in sorted(out.rglob('*')) if p.is_file()})
    event('before-upload')
    evidence = upload_evidence(out)
    print({'diagnostic_report': report, 'evidence': evidence}, flush=True)
    event('after-upload')

main()
event('main-returned')
'''
ast.parse(DIAGNOSTIC)
old = 'python -u ai/strong/surrogate_continuation_selected_cost_v1.py'
assert manager.BOOTSTRAP.count(old) == 1
bootstrap = manager.BOOTSTRAP.replace(old, "python -u - <<'DIAGNOSTIC'\n"+DIAGNOSTIC+"\nDIAGNOSTIC\necho DIAGNOSTIC_PYTHON_EXITED\n")
source = manager.prerequisites()
assert not GUARD.exists(), 'Inspect the original diagnostic handle; no automatic retry'
guard = {'case': CASE, 'stage': 'launch_intent', 'created_at': datetime.now(timezone.utc).isoformat(),
         'source': source, 'bootstrap_sha256': hashlib.sha256(bootstrap.encode()).hexdigest(),
         'launcher_sha256': digest(__file__), 'original_job_id': '6adda6dd1e112550ce7e86c1',
         'original_job_changed': False, 'flavor': 'cpu-upgrade', 'timeout': '30m', 'ssh': True,
         'engineering_continuations': 16, 'fresh_scientific_continuations': 0,
         'gradients': False, 'qualification_eligible': False, 'reserved_final_seeds_used': False}
with GUARD.open('x') as stream:
    __import__('json').dump(guard, stream, indent=2)
try:
    env = {'SOURCE_ARCHIVE': source['archive'], 'SOURCE_REVISION': source['revision'],
           'SOURCE_SHA256': source['sha256'], 'SOURCE_MANIFEST_SHA256': source['manifest_sha256'],
           'SOURCE_MANIFEST_FILES': str(source['manifest_files']), 'STUDY_INPUTS_SHA256': source['study_inputs_sha256'],
           'HF_HUB_DISABLE_PROGRESS_BARS': '1', 'PYTHONDONTWRITEBYTECODE': '1'}
    token = get_token()
    assert token
    job = HfApi().run_job(image='python:3.11-slim-bookworm', command=['bash', '-lc', bootstrap], env=env,
                         secrets={'HF_TOKEN': token}, flavor='cpu-upgrade', timeout='30m', ssh=True,
                         name=CASE, labels={'project': 'powergrid-ai', 'stage': CASE})
    guard.update(stage='launched', job_id=job.id)
except BaseException as error:
    guard.update(stage='launch_unknown', failure_type=type(error).__name__)
    raise
finally:
    write(GUARD, guard)
print({key: guard[key] for key in ('case', 'stage', 'job_id', 'original_job_changed') if key in guard}, flush=True)
