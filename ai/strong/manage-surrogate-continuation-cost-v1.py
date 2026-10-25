"""Inspect and independently collect the original continuation-cost calibrations."""
import argparse
import ast
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import re

from huggingface_hub import HfApi, hf_hub_download
from strategic_collection import ROOT, read, write, digest
from population_policy_verification import extract_verified
from surrogate_continuation_study_v1 import verify_chunk, verify_result
from surrogate_continuation_runtime_v1 import INPUTS, MODES, validate_inputs

STRONG = ROOT/'ai/strong'
spec = importlib.util.spec_from_file_location('continuation_cost_launch', STRONG/'launch-surrogate-continuation-cost-v1.py')
launcher = importlib.util.module_from_spec(spec); spec.loader.exec_module(launcher)
COLLECTED = ROOT/'ai/runs/surrogate-continuation-cost-collected-v1'
INDEX = STRONG/'surrogate-continuation-cost-results-v1.json'


def code_hashes():
    return {**launcher.dependencies(), **{str(p.relative_to(ROOT)): digest(p) for p in [Path(__file__),
        STRONG/'population_policy_verification.py', STRONG/'surrogate_opponent_continuations_v1.py']}}


def original(key):
    plan, source, row = launcher.admission(key); path = launcher.GUARDS/(row['case']+'.json'); guard = read(path)
    assert guard['stage'] == 'launched' and guard['row'] == row and guard['source'] == source
    assert guard['key'] == key and guard['case'] == row['case'] and guard['plan_sha256'] == digest(launcher.PLAN)
    assert re.fullmatch('[a-f0-9]{24}', guard['job_id'])
    return plan, source, row, guard, path


def inspect(key):
    _, _, row, guard, path = original(key)
    return {'key': key, 'case': row['case'], 'job_id': guard['job_id'], 'guard_sha256': digest(path),
            'authoritative_status': HfApi().inspect_job(job_id=guard['job_id']).status.stage,
            'checked_at': datetime.now(timezone.utc).isoformat()}


def audit(folder, source, key, evidence):
    folder = Path(folder); manifest = read(folder/'manifest.json')
    assert {str(p.relative_to(folder)) for p in folder.rglob('*') if p.is_file()} == set(manifest) | {'manifest.json'}
    assert digest(folder/'manifest.json') == evidence['manifest_sha256'] and len(manifest)+1 == evidence['archived_files']
    assert all(digest(folder/name) == sha for name, sha in manifest.items())
    inputs_path = launcher.PREP/'layout'/INPUTS.relative_to(ROOT); inputs = read(inputs_path); validate_inputs(inputs)
    assert digest(inputs_path) == source['inputs_sha256']
    root = inputs['roots'][key]; state = read(folder/'job.json')
    assert state['stage'] == 'complete' and state['key'] == key and state['case'] == 'surrogate-continuation-cost-v1-'+key
    assert state['source_revision'] == source['revision'] and state['source_sha256'] == source['sha256']
    assert state['source_manifest_sha256'] == source['manifest_sha256'] and state['inputs_sha256'] == source['inputs_sha256']
    assert state['protocol_sha256'] == source['protocol_sha256']
    assert state['job_runner_sha256'] == source['new_files']['ai/strong/surrogate_continuation_runtime_v1.py']
    assert all(state[k] is False for k in ('gradients', 'qualification_eligible', 'reserved_final_seeds_used', 'automatic_retries'))
    assert state['caps'] == 0 and state['continuations'] == 32 and set(state['modes']) == set(MODES)
    worlds = None; nested = 0
    for mode in MODES:
        result = verify_chunk(folder/mode, root); checked = verify_result(root, result, mode, 0, 8)
        assert checked['caps'] == 0 and len(result['rows']) == 16
        same = {k: v['sha256'] for k, v in checked['worlds'].items()}
        if worlds is None: worlds = same
        else: assert worlds == same
        measured = state['modes'][mode]
        assert measured['rows'] == 16 and measured['status_sha256'] == digest(folder/mode/'status.json')
        assert measured['memory_sampling_period_seconds'] == .2
        for name in ('seconds', 'cpu_seconds', 'sampled_peak_total_rss_bytes', 'memory_samples'):
            assert type(measured[name]) in (int, float) and 0 < measured[name] < float('inf')
        nested += sum(r['searchStats']['evaluations']+r['diagnostic']['priorSearchStats']['evaluations'] for r in result['rows'])
    expected_audit = {'complete': True, 'key': key, 'continuations': 32, 'caps': 0, 'modes': state['modes'],
                      'paired_worlds_exact': True, 'training_eligible': False, 'qualification_eligible': False}
    assert read(folder/'audit.json') == expected_audit
    return {**expected_audit, 'nested_reference_evaluations': nested,
            'raw_evidence_bytes': sum(p.stat().st_size for p in folder.rglob('*') if p.is_file())}


def verified(key):
    plan, source, row, guard, path = original(key)
    folder = COLLECTED/row['case']; receipt_path = folder/'verified.json'
    if not receipt_path.exists(): return None
    receipt = read(receipt_path)
    assert receipt['verified'] and receipt['authoritative_status'] == 'COMPLETED'
    assert receipt['job_id'] == guard['job_id'] and receipt['guard_sha256'] == digest(path)
    assert receipt['source'] == source and receipt['plan_sha256'] == digest(launcher.PLAN)
    assert receipt['collector_code_hashes'] == code_hashes()
    artifacts = folder/'artifacts'; manifest = read(artifacts/'manifest.json')
    assert digest(artifacts/'manifest.json') == receipt['evidence']['manifest_sha256']
    assert all(digest(artifacts/name) == sha for name, sha in manifest.items())
    return receipt


def collect(key):
    previous = verified(key)
    if previous: return previous
    plan, source, row, _, _ = original(key); status = inspect(key)
    folder = COLLECTED/row['case']; folder.mkdir(parents=True, exist_ok=True); write(folder/'status.json', status)
    if status['authoritative_status'] != 'COMPLETED': return status
    hashes = code_hashes(); lines = '\n'.join(str(line) for line in HfApi().fetch_job_logs(job_id=status['job_id'], follow=False))
    (folder/'job.log').write_text(lines); receipts = []
    for line in lines.splitlines():
        if not line.startswith('{'): continue
        try: record = ast.literal_eval(line)
        except (SyntaxError, ValueError): continue
        if isinstance(record, dict) and record.get('status', {}).get('case') == row['case'] and 'evidence' in record: receipts.append(record)
    assert len(receipts) == 1, 'Missing or ambiguous original upload receipt'
    remote = receipts[0]; evidence = remote['evidence']
    assert evidence['repo'] == 'coyotte508/powergrid-ai-germany-v1' and evidence['archive_path'] == f'archives/{row["case"]}.tgz'
    assert evidence['remote_archive_verified'] and re.fullmatch('[a-f0-9]{40}', evidence['revision']) and evidence['format'] == 'tar.gz'
    archive = Path(hf_hub_download(evidence['repo'], evidence['archive_path'], revision=evidence['revision']))
    assert digest(archive) == evidence['archive_sha256']; artifacts = folder/'artifacts'
    if not artifacts.exists(): extract_verified(archive, artifacts)
    assert read(artifacts/'job.json') == remote['status']
    review = audit(artifacts, source, key, evidence); assert hashes == code_hashes()
    result = {**status, 'verified': True, 'source': source, 'plan_sha256': digest(launcher.PLAN), 'review': review,
              'evidence': evidence, 'collector_code_hashes': hashes, 'gradients': False, 'qualification_eligible': False}
    temporary = folder/'verified.tmp.json'; write(temporary, result); temporary.replace(folder/'verified.json')
    return result


def index():
    plan = read(launcher.PLAN); receipts = {row['key']: verified(row['key']) for row in plan['cases']}
    assert len(receipts) == 24 and all(receipts.values()), 'All original calibrations must verify'
    for key, receipt in receipts.items():
        assert audit(COLLECTED/receipt['case']/'artifacts', receipt['source'], key, receipt['evidence']) == receipt['review']
    result = {'complete': True, 'jobs': 24, 'continuations': 768, 'caps': 0,
              'plan_sha256': digest(launcher.PLAN), 'source': plan['source'], 'cases': receipts,
              'collector_code_hashes': code_hashes(), 'full_study_admitted': False,
              'gradients': False, 'qualification_eligible': False, 'reserved_final_seeds_used': False}
    if INDEX.exists(): assert read(INDEX) == result
    else:
        temporary = INDEX.with_suffix('.tmp.json'); write(temporary, result); temporary.replace(INDEX)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__); sub = parser.add_subparsers(dest='command', required=True)
    for command in ('inspect', 'collect'): sub.add_parser(command).add_argument('key')
    sub.add_parser('collect-ready'); sub.add_parser('index'); args = parser.parse_args()
    if args.command == 'collect-ready':
        plan = read(launcher.PLAN)
        with ThreadPoolExecutor(max_workers=4) as pool: results = list(pool.map(collect, [row['key'] for row in plan['cases']]))
        print({'verified': sum(r.get('verified', False) for r in results), 'jobs': len(results)}, flush=True)
    else:
        result = index() if args.command == 'index' else globals()[args.command](args.key)
        print({k: result[k] for k in ('case', 'job_id', 'authoritative_status', 'verified', 'complete', 'continuations') if k in result})
