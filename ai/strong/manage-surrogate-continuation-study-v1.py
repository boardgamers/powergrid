"""Collect every original paired root job and analyze the unchanged full corpus."""
import argparse
import ast
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import importlib.util
from pathlib import Path
import re

from huggingface_hub import HfApi, hf_hub_download
from strategic_collection import ROOT, read, write, digest
from population_policy_verification import extract_verified
import surrogate_continuation_job_v1 as job
from surrogate_continuation_analysis_v1 import analyze

STRONG = ROOT/'ai/strong'
spec = importlib.util.spec_from_file_location('study_launcher', STRONG/'launch-surrogate-continuation-study-v1.py')
launcher = importlib.util.module_from_spec(spec); spec.loader.exec_module(launcher)
COLLECTED = ROOT/'ai/runs/surrogate-continuation-study-collected-v1'
INDEX = STRONG/'surrogate-continuation-study-results-v1.json'
ANALYSIS = STRONG/'surrogate-continuation-study-comparison-v1.json'


def dependencies():
    return {**launcher.dependencies(), str(Path(__file__).relative_to(ROOT)): digest(__file__)}


def manifest_check(folder, evidence):
    folder = Path(folder); manifest = read(folder/'manifest.json')
    assert {str(p.relative_to(folder)) for p in folder.rglob('*') if p.is_file()} == set(manifest) | {'manifest.json'}
    assert digest(folder/'manifest.json') == evidence['manifest_sha256'] and len(manifest)+1 == evidence['archived_files']
    assert all(digest(folder/name) == sha for name, sha in manifest.items())


def audit(folder, source, root, evidence):
    folder = Path(folder); manifest_check(folder, evidence); state = read(folder/'job.json')
    assert root['identity']['mode'] == 'root' and state['scope'] == 'fresh_fidelity'
    assert state['provenance'] == {'source_revision': source['revision'], 'source_sha256': source['sha256'],
        'source_manifest_sha256': source['manifest_sha256'], 'study_inputs_sha256': source['study_inputs_sha256'],
        'root_manifest_sha256': source['root_manifest_sha256'], 'selection_freeze_sha256': source['selection_freeze_sha256']}
    checked = job.verify_root_job(folder, root, source['surrogate_policy_sha256'])
    assert checked == read(folder/'audit.json')
    assert checked['continuations'] == 48 and checked['paired_worlds_exact'] and checked['all_modes_retained']
    return {**checked, 'paired_sha256': digest(folder/'paired.json'), 'measurements': state['modes'],
            'raw_evidence_bytes': sum(p.stat().st_size for p in folder.rglob('*') if p.is_file())}


def verified(row, source, root):
    guard, path = launcher.original(row, source); folder = COLLECTED/row['case']; receipt = folder/'verified.json'
    if not receipt.exists(): return None
    result = read(receipt)
    assert result['verified'] and result['authoritative_status'] == 'COMPLETED'
    assert result['case'] == row['case'] and result['root_id'] == row['root_id'] and result['job_id'] == guard['job_id']
    assert result['guard_sha256'] == digest(path) and result['plan_sha256'] == digest(launcher.PLAN)
    assert result['source'] == source and result['collector_code_hashes'] == dependencies()
    assert result['review'] == audit(folder/'artifacts', source, root, result['evidence'])
    return result


def collect_row(row, source, root):
    previous = verified(row, source, root)
    if previous: return previous
    guard, path = launcher.original(row, source); api = HfApi(); stage = api.inspect_job(job_id=guard['job_id']).status.stage
    status = {'case': row['case'], 'root_id': row['root_id'], 'job_id': guard['job_id'], 'guard_sha256': digest(path),
              'authoritative_status': stage, 'checked_at': datetime.now(timezone.utc).isoformat()}
    folder = COLLECTED/row['case']; folder.mkdir(parents=True, exist_ok=True); write(folder/'status.json', status)
    if stage in ('RUNNING', 'SCHEDULING'): return status
    hashes = dependencies(); lines = '\n'.join(str(line) for line in api.fetch_job_logs(job_id=guard['job_id'], follow=False))
    (folder/'job.log').write_text(lines); receipts = []
    for line in lines.splitlines():
        if not line.startswith('{'): continue
        try: record = ast.literal_eval(line)
        except (SyntaxError, ValueError): continue
        if isinstance(record, dict) and record.get('status', {}).get('case') == row['case'] and 'evidence' in record: receipts.append(record)
    if stage != 'COMPLETED' and len(receipts) != 1:
        failure = {**status, 'verified': False, 'upload_receipts_found': len(receipts), 'logs_preserved': True}
        write(folder/'failure.json', failure); return failure
    assert len(receipts) == 1, 'Missing or ambiguous original upload receipt'
    remote = receipts[0]; evidence = remote['evidence']
    assert evidence['repo'] == 'coyotte508/powergrid-ai-germany-v1' and evidence['archive_path'] == f'archives/{row["case"]}.tgz'
    assert evidence['remote_archive_verified'] and evidence['format'] == 'tar.gz' and re.fullmatch('[a-f0-9]{40}', evidence['revision'])
    archive = Path(hf_hub_download(evidence['repo'], evidence['archive_path'], revision=evidence['revision']))
    assert digest(archive) == evidence['archive_sha256']; artifacts = folder/'artifacts'
    if not artifacts.exists(): extract_verified(archive, artifacts)
    manifest_check(artifacts, evidence); assert read(artifacts/'job.json') == remote['status']
    if stage != 'COMPLETED':
        failure = {**status, 'verified': False, 'evidence': evidence, 'partial_artifacts_preserved': True}
        write(folder/'failure.json', failure); return failure
    review = audit(artifacts, source, root, evidence); assert hashes == dependencies()
    result = {**status, 'verified': True, 'source': source, 'plan_sha256': digest(launcher.PLAN),
              'review': review, 'evidence': evidence, 'collector_code_hashes': hashes,
              'gradients': False, 'qualification_eligible': False, 'reserved_final_seeds_used': False}
    temporary = folder/'verified.tmp.json'; write(temporary, result); temporary.replace(folder/'verified.json')
    return result


def collect_ready():
    plan, source, manifest = launcher.admission(); roots = job.manifest_roots(manifest)
    present = {p.stem for p in launcher.GUARDS.glob('*.json')}; assert present <= {row['case'] for row in plan['cases']}
    rows = [row for row in plan['cases'] if row['case'] in present]
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda row: collect_row(row, source, roots[row['root_id']]), rows))
    return {'jobs_submitted': len(rows), 'jobs_verified': sum(r.get('verified', False) for r in results),
            'failed_jobs': [r for r in results if r['authoritative_status'] not in ('RUNNING', 'SCHEDULING', 'COMPLETED')],
            'caps': sum(r['review']['caps'] for r in results if r.get('verified'))}


def index():
    plan, source, manifest = launcher.admission(); roots = job.manifest_roots(manifest)
    expected = {row['case'] for row in plan['cases']}
    assert {p.stem for p in launcher.GUARDS.glob('*.json')} == expected, 'Require every original planned job'
    receipts = {row['root_id']: verified(row, source, roots[row['root_id']]) for row in plan['cases']}
    assert len(receipts) == len(roots) == 480 and all(receipts.values()), 'Require every original paired root; never drop failures'
    records = {rid: read(COLLECTED/r['case']/'artifacts/paired.json') for rid, r in receipts.items()}
    comparison = analyze(manifest, list(records.values()))
    caps = sum(r['review']['caps'] for r in receipts.values()); assert comparison['caps'] == caps
    assert comparison['complete'] is (caps == 0)
    if caps: assert comparison['primary'] is comparison['whole_deal_uncertainty'] is None
    result = {'complete': caps == 0, 'all_jobs_verified': True, 'jobs': 480, 'roots': 480, 'continuations': 23040, 'caps': caps,
              'source': source, 'plan_sha256': digest(launcher.PLAN), 'collector_code_hashes': dependencies(),
              'paired_records': {rid: {'case': r['case'], 'job_id': r['job_id'], 'paired_sha256': r['review']['paired_sha256'],
                                      'receipt_sha256': digest(COLLECTED/r['case']/'verified.json')} for rid, r in receipts.items()},
              'comparison_sha256_canonical': job.object_hash(comparison), 'gradients': False,
              'qualification_eligible': False, 'reserved_final_seeds_used': False,
              'scope': 'Diagnostic continuation fidelity. No policy selected, full-game strength claim or deployment latency claim.'}
    for path, data in ((ANALYSIS, comparison), (INDEX, result)):
        if path.exists(): assert read(path) == data
        else:
            temporary = path.with_suffix('.tmp.json'); write(temporary, data); temporary.replace(path)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__); parser.add_argument('operation', choices=['collect-ready', 'index'])
    args = parser.parse_args(); result = index() if args.operation == 'index' else collect_ready()
    print({k: result[k] for k in ('complete', 'jobs', 'roots', 'continuations', 'jobs_submitted', 'jobs_verified', 'failed_jobs', 'caps') if k in result})
