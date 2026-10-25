"""One selected-opponent runtime job; no full-study launch or automatic retry."""
import argparse
import ast
from datetime import datetime, timezone
import fcntl
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re

from huggingface_hub import HfApi, get_token, hf_hub_download
from strategic_collection import ROOT, read, write, digest
from population_policy_verification import extract_verified
import surrogate_continuation_selected_cost_v1 as runner

STRONG = ROOT/'ai/strong'


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, STRONG/file)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module


builder = load('selected_cost_source', 'build-surrogate-continuation-study-source-v1.py')
old = load('selected_cost_bootstrap', 'launch-opponent-surrogate-runtime-v1.py')
BOOTSTRAP = old.BOOTSTRAP.replace('opponent-surrogate-source-manifest.json', 'surrogate-continuation-study-source-manifest.json')
OLD_COMMAND = 'python -u ai/strong/opponent-surrogate-collection-job-v1.py "$PLAYERS" 0 1 --mode runtime'
assert BOOTSTRAP.count(OLD_COMMAND) == 1
BOOTSTRAP = BOOTSTRAP.replace(OLD_COMMAND, 'python -u ai/strong/surrogate_continuation_selected_cost_v1.py')
PLAN = STRONG/'surrogate-continuation-selected-cost-admission-v1.json'
GUARDS = ROOT/'ai/runs/surrogate-continuation-selected-cost-launches-v1'
COLLECTED = ROOT/'ai/runs/surrogate-continuation-selected-cost-collected-v1'
RESULT = STRONG/'surrogate-continuation-selected-cost-results-v1.json'
PROOF = ROOT/'ai/runs/surrogate-continuation-selected-cost-manager-preflight-v1.json'


def dependencies():
    paths = [Path(__file__), Path(old.__file__), STRONG/'population_policy_verification.py']
    return {**builder.dependencies(), **{str(p.relative_to(ROOT)): digest(p) for p in paths}}


def allowance(reference):
    assert reference['complete'] and reference['remote_archive_verified'] and reference['caps'] == 0
    assert reference['jobs'] == 24 and reference['continuations'] == 768
    rows = reference['measurements']; assert len(rows) == 24
    mixture = [row['modes']['neural_population']['seconds'] for row in rows.values()]
    peaks = [m['sampled_peak_total_rss_bytes'] for row in rows.values() for m in row['modes'].values()]
    assert all(type(v) in (int, float) and math.isfinite(v) and v > 0 for v in [*mixture, *peaks])
    estimate = 900 + 24 * 8 * max(mixture)
    hours = math.ceil(estimate/(.75*3600)); memory = 2*max(peaks)+4e9
    assert hours <= 12 and memory < 32e9
    return {'flavor': 'cpu-upgrade', 'vcpus': 8, 'ram_gb': 32, 'disk_gb': 50, 'workers': 8,
            'timeout_hours': hours, 'max_concurrent': 1, 'estimated_seconds': estimate,
            'memory_allowance_bytes': memory, 'historical_mixture_max_seconds': max(mixture),
            'historical_peak_rss_bytes': max(peaks),
            'calculation': '15 minutes setup plus 24 roots at eight times the slowest measured population root; 25% timeout reserve. Twice prior peak RSS plus 4 GB allows the learned model and process reserve.',
            'limitation': 'Bounded timing calibration, not a surrogate speed guarantee. Preserve any timeout, failure or cap; do not reduce the fixed roots or worlds. Full study remains unadmitted.'}


def prerequisites():
    prepared = builder.check_prepared(); source = read(builder.SOURCE)
    assert all(source[k] == v for k, v in prepared.items())
    assert source['remote_archive_verified'] and re.fullmatch('[a-f0-9]{40}', source['revision'])
    layout = read(builder.PREP/'layout-check.json')
    assert digest(builder.PREP/'layout-check.json') == source['layout_sha256']
    assert layout['complete'] and layout['source_sha256'] == source['sha256']
    assert layout['source_manifest_sha256'] == source['manifest_sha256']
    assert layout['reports']['fresh']['public_roots_checked'] == 480
    assert layout['reports']['runtime']['runtime_roots_checked'] == 24 and layout['new_continuations'] == 0
    assert source['selected_cost_continuations'] == 384 and source['full_study_admitted'] is False
    proof = read(PROOF)
    assert proof['complete'] and proof['code_hashes'] == dependencies() and proof['tests'] >= 6
    return source


def prepare():
    source = prerequisites()
    plan = {'created_at': datetime.now(timezone.utc).isoformat(), 'case': runner.CASE, 'source': source,
            'source_descriptor_sha256': digest(builder.SOURCE), 'preflight_sha256': digest(PROOF),
            'cost_evidence_sha256': digest(builder.COST), 'admission': allowance(read(builder.COST)),
            'dependency_hashes': dependencies(), 'bootstrap_sha256': hashlib.sha256(BOOTSTRAP.encode()).hexdigest(),
            'jobs': 1, 'roots': 24, 'continuations': 384, 'full_study_admitted': False,
            'gradients': False, 'automatic_retries': False, 'qualification_eligible': False, 'reserved_final_seeds_used': False}
    with PLAN.open('x') as stream: json.dump(plan, stream, indent=2); stream.write('\n')
    return plan


def admission():
    source = prerequisites(); plan = read(PLAN)
    assert plan['source'] == source and plan['source_descriptor_sha256'] == digest(builder.SOURCE)
    assert plan['preflight_sha256'] == digest(PROOF) and plan['cost_evidence_sha256'] == digest(builder.COST)
    assert plan['admission'] == allowance(read(builder.COST)) and plan['dependency_hashes'] == dependencies()
    assert plan['bootstrap_sha256'] == hashlib.sha256(BOOTSTRAP.encode()).hexdigest()
    assert plan['case'] == runner.CASE and plan['jobs'] == 1 and plan['roots'] == 24 and plan['continuations'] == 384
    assert all(plan[k] is False for k in ('full_study_admitted', 'gradients', 'automatic_retries', 'qualification_eligible', 'reserved_final_seeds_used'))
    return plan, source


def original():
    plan, source = admission(); path = GUARDS/(runner.CASE+'.json'); guard = read(path)
    assert guard['stage'] == 'launched', 'Reconcile the original uncertain submission; never replace it'
    assert guard['source'] == source and guard['plan_sha256'] == digest(PLAN) and guard['case'] == runner.CASE
    assert re.fullmatch('[a-f0-9]{24}', guard['job_id'])
    return plan, source, guard, path


def inspect():
    _, _, guard, path = original()
    return {'case': runner.CASE, 'job_id': guard['job_id'], 'guard_sha256': digest(path),
            'authoritative_status': HfApi().inspect_job(job_id=guard['job_id']).status.stage,
            'checked_at': datetime.now(timezone.utc).isoformat()}


def launch(execute=False):
    plan, source = admission()
    if not execute: return {'case': runner.CASE, 'admitted': True, 'execute': False}
    GUARDS.mkdir(parents=True, exist_ok=True)
    with (GUARDS/'.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB); path = GUARDS/(runner.CASE+'.json')
        if path.exists(): return inspect()
        token = get_token(); assert token
        guard = {'case': runner.CASE, 'stage': 'launch_intent', 'source': source, 'plan_sha256': digest(PLAN),
                 'created_at': datetime.now(timezone.utc).isoformat(), 'qualification_eligible': False}
        with path.open('x') as stream: json.dump(guard, stream, indent=2)
        try:
            env = {'SOURCE_ARCHIVE': source['archive'], 'SOURCE_REVISION': source['revision'], 'SOURCE_SHA256': source['sha256'],
                   'SOURCE_MANIFEST_SHA256': source['manifest_sha256'], 'SOURCE_MANIFEST_FILES': str(source['manifest_files']),
                   'STUDY_INPUTS_SHA256': source['study_inputs_sha256'], 'RUNTIME_INPUTS_SHA256': source['runtime_inputs_sha256'],
                   'SURROGATE_POLICY_SHA256': source['surrogate_policy_sha256'], 'HF_HUB_DISABLE_PROGRESS_BARS': '1'}
            job = HfApi().run_job(image='python:3.11-slim-bookworm', command=['bash', '-lc', BOOTSTRAP],
                flavor=plan['admission']['flavor'], timeout=f"{plan['admission']['timeout_hours']}h", name=runner.CASE,
                env=env, secrets={'HF_TOKEN': token}, labels={'project': 'powergrid-ai', 'stage': runner.CASE})
            guard.update(stage='launched', job_id=job.id)
        except BaseException as error:
            # Do not persist exception text: it could contain request secrets.
            guard.update(stage='launch_unknown', failure_type=type(error).__name__); raise
        finally: write(path, guard)
    return {'case': runner.CASE, 'job_id': guard['job_id']}


def audit(folder, source, evidence):
    folder = Path(folder); manifest = read(folder/'manifest.json')
    assert {str(p.relative_to(folder)) for p in folder.rglob('*') if p.is_file()} == set(manifest) | {'manifest.json'}
    assert digest(folder/'manifest.json') == evidence['manifest_sha256'] and len(manifest)+1 == evidence['archived_files']
    assert all(digest(folder/name) == sha for name, sha in manifest.items())
    path = builder.PREP/'layout'/runner.RUNTIME_INPUTS.relative_to(ROOT); inputs = read(path)
    runner.validate_runtime(inputs); assert digest(path) == source['runtime_inputs_sha256']
    state = read(folder/'job.json')
    assert state['scope'] == 'selected_runtime_calibration'
    assert state['provenance'] == {'source_revision': source['revision'], 'source_sha256': source['sha256'],
        'source_manifest_sha256': source['manifest_sha256'], 'study_inputs_sha256': source['study_inputs_sha256'],
        'runtime_inputs_sha256': source['runtime_inputs_sha256'], 'selection_freeze_sha256': source['selection_freeze_sha256']}
    checked = runner.verify(folder, inputs['roots'], source['surrogate_policy_sha256'])
    assert checked == read(folder/'audit.json')
    assert checked['complete'] and checked['roots'] == 24 and checked['continuations'] == 384 and checked['caps'] == 0
    return checked


def collect():
    plan, source, guard, path = original()
    if RESULT.exists():
        previous = read(RESULT)
        assert previous['verified'] and previous['job_id'] == guard['job_id'] and previous['guard_sha256'] == digest(path)
        assert previous['source'] == source and previous['plan_sha256'] == digest(PLAN) and previous['collector_code_hashes'] == dependencies()
        assert previous['review'] == audit(COLLECTED/'artifacts', source, previous['evidence'])
        return previous
    status = inspect(); COLLECTED.mkdir(parents=True, exist_ok=True); write(COLLECTED/'status.json', status)
    if status['authoritative_status'] != 'COMPLETED': return status
    hashes = dependencies(); lines = '\n'.join(str(line) for line in HfApi().fetch_job_logs(job_id=guard['job_id'], follow=False))
    (COLLECTED/'job.log').write_text(lines); receipts = []
    for line in lines.splitlines():
        if not line.startswith('{'): continue
        try: record = ast.literal_eval(line)
        except (SyntaxError, ValueError): continue
        if isinstance(record, dict) and record.get('status', {}).get('case') == runner.CASE and 'evidence' in record: receipts.append(record)
    assert len(receipts) == 1, 'Missing or ambiguous original upload receipt'
    remote = receipts[0]; evidence = remote['evidence']
    assert evidence['repo'] == 'coyotte508/powergrid-ai-germany-v1' and evidence['archive_path'] == f'archives/{runner.CASE}.tgz'
    assert evidence['remote_archive_verified'] and evidence['format'] == 'tar.gz' and re.fullmatch('[a-f0-9]{40}', evidence['revision'])
    archive = Path(hf_hub_download(evidence['repo'], evidence['archive_path'], revision=evidence['revision']))
    assert digest(archive) == evidence['archive_sha256']; artifacts = COLLECTED/'artifacts'
    if not artifacts.exists(): extract_verified(archive, artifacts)
    assert read(artifacts/'job.json') == remote['status']
    review = audit(artifacts, source, evidence); assert hashes == dependencies()
    result = {**status, 'complete': True, 'verified': True, 'source': source, 'plan_sha256': digest(PLAN),
              'review': review, 'evidence': evidence, 'collector_code_hashes': hashes,
              'full_study_admitted': False, 'gradients': False, 'qualification_eligible': False, 'reserved_final_seeds_used': False}
    temporary = RESULT.with_suffix('.tmp.json'); write(temporary, result); temporary.replace(RESULT)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__); parser.add_argument('operation', choices=['prepare', 'launch', 'inspect', 'collect'])
    parser.add_argument('--execute', action='store_true'); args = parser.parse_args()
    assert args.operation == 'launch' or not args.execute
    result = launch(args.execute) if args.operation == 'launch' else globals()[args.operation]()
    print({k: result[k] for k in ('case', 'job_id', 'authoritative_status', 'complete', 'verified', 'admitted', 'execute', 'jobs', 'continuations') if k in result})
