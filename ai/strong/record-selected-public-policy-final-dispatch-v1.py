"""Record and archive offline final transport checks; no submission operation."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess

from huggingface_hub import HfApi
from policy_iteration_evidence_archive import upload_evidence
from public_policy_final_audit_v1 import digest, read
import selected_public_policy_final_dispatch_v1 as dispatch

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'ai/runs/selected-public-policy-final-dispatch-preflight-v1'
REPORT = ROOT/'ai/strong/selected-public-policy-final-dispatch-preflight-v1.json'
NAME = 'selected-public-policy-final-dispatch-evidence-v1'
ARCHIVE = ROOT/'ai/runs'/NAME
DESCRIPTOR = ROOT/'ai/strong'/(NAME+'.json')


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False); stream.write('\n')


def main():
    assert all(not p.exists() for p in (OUT, REPORT, ARCHIVE, ARCHIVE.with_suffix('.tgz'), ARCHIVE.with_suffix('.intent.json'), DESCRIPTOR)), 'Inspect original recording/upload; never overwrite'
    logs = [ROOT/'ai/runs'/name for name in (
        'selected-public-policy-final-dispatch-tests-v1-first.log',
        'selected-public-policy-final-dispatch-tests-v1-with-bootstrap.log',
        'selected-public-policy-final-dispatch-tests-v1-bootstrap-fixed.log')]
    assert 'Ran 10 tests' in logs[0].read_text() and logs[0].read_text().rstrip().endswith('OK')
    assert 'FAILED (failures=1)' in logs[1].read_text() and 'test_exact_exercised_setup_and_final_entry' in logs[1].read_text()
    assert 'Ran 12 tests' in logs[2].read_text() and logs[2].read_text().rstrip().endswith('OK')
    p = ROOT/'ai/strong/manage-current-auction-runtime-v1.py'
    spec = importlib.util.spec_from_file_location('unchanged_setup', p)
    reference = importlib.util.module_from_spec(spec); spec.loader.exec_module(reference)
    bootstrap = dispatch.final_bootstrap(reference.BOOTSTRAP)
    subprocess.run(['bash', '-n'], input=bootstrap, text=True, check=True, capture_output=True)
    source_proof = ROOT/'ai/strong/selected-public-policy-final-source-preflight-v1.json'
    proof = read(source_proof); source = ROOT/'ai/runs/selected-public-policy-final-source-preflight-v1/source'
    assert proof['passed'] and proof['validated_jobs'] == 320 and proof['synthetic_candidate_and_allocation_only']
    assert digest(source/'final-plan.json') == proof['plan_sha256']
    assert digest(source/'source-manifest.json') == proof['source_manifest_sha256']
    plan = read(source/'final-plan.json')
    release = {'version': 1, 'admission_sha256': '7'*64, 'source': {
        'repo': 'coyotte508/powergrid-ai-training-v1', 'revision': '8'*40,
        'archive': 'synthetic-dispatch-validation-only.tgz', 'sha256': '9'*64,
        'source_manifest_sha256': proof['source_manifest_sha256']}, 'plan': plan,
        'allocation': {r['name']: {'flavor': 'cpu-upgrade', 'timeout': '5h'} for r in plan['rows']},
        'bootstrap_sha256': hashlib.sha256(bootstrap.encode()).hexdigest()}
    assert len(dispatch.validate_release(release, bootstrap)) == 320
    # validate_release is pure: no API, ledger creation or execution is involved.
    ledger = read(ROOT/'ai/strong/experiments.json'); assert ledger['final_seed_prefix_used'] is False and not ledger.get('final_runs')
    owner = read(ROOT/'ai/runs/current-auction-confirmation-recovery-v1/state.json')
    command = (Path('/proc')/str(owner['pid'])/'cmdline').read_bytes().replace(b'\0', b' ').decode()
    assert owner['pid'] == 2398668 and 'coordinate-current-auction-confirmation-recovery-v1.py --start' in command
    assert all(digest(ROOT/n) == h for n, h in owner['code_hashes'].items())
    ready = read(ROOT/'ai/strong/current-full-serving-readiness-v1.json')
    assert all(digest(ROOT/n) == h for n, h in ready['input_hashes'].items())
    OUT.mkdir(); (OUT/'final-bootstrap.sh').write_text(bootstrap)
    save(OUT/'synthetic-release.json', release)
    save(OUT/'owner-observation.json', {'observed_at': datetime.now(timezone.utc).isoformat(),
        'pid': owner['pid'], 'command': command, 'verified_live': True, 'state': owner})
    paths = [Path(__file__), Path(dispatch.__file__), ROOT/'ai/strong/test_selected_public_policy_final_dispatch_v1.py',
        source_proof, ROOT/'ai/strong/selected-public-policy-final-source-evidence-v1.json',
        ROOT/'ai/strong/public_policy_final_audit_v1.py', ROOT/'ai/strong/public_policy_final_contract_v1.py',
        ROOT/'ai/strong/public_policy_runtime_v1.py', ROOT/'ai/strong/final-protocol-multiplayer.json',
        p, ROOT/'ai/strong/node-runtime-cache-v1.json',
        ROOT/'ai/runs/selected-public-policy-final-dispatch-before-bootstrap-newline-fix-v1.py',
        ROOT/'ai/runs/test-selected-public-policy-final-dispatch-before-bootstrap-newline-fix-v1.py', *logs]
    report = {'passed': True, 'created_at': datetime.now(timezone.utc).isoformat(), 'tests': 12,
        'real_source_plan_rows_validated': 320, 'planned_games': 20160,
        'setup_sha256': dispatch.SETUP_SHA256, 'bootstrap_sha256': release['bootstrap_sha256'],
        'input_hashes': {str(p.relative_to(ROOT)): digest(p) for p in paths},
        'synthetic_release_sha256': digest(OUT/'synthetic-release.json'),
        'first_bootstrap_test_failure_preserved': True,
        'new_hf_jobs': 0, 'new_full_games': 0, 'new_policy_calls': 0,
        'real_release_admitted': False, 'candidate_selected': False, 'qualified': False,
        'reserved_final_seeds_used': False,
        'scope': 'Durable dispatch/storage and pinned bootstrap wiring only. Mock API calls and synthetic release metadata. Caller admission/batch/collection integration remains required.'}
    save(REPORT, report)
    sources = set(paths)|{REPORT, ROOT/'ai/SELECTED-PUBLIC-POLICY-FINAL-DISPATCH-2026-10-29.md',
        ROOT/'ai/strong/policy_iteration_evidence_archive.py', ROOT/'ai/strong/strategic_collection.py'}
    sources.update(p for p in OUT.rglob('*') if p.is_file())
    api = HfApi(); repo = 'coyotte508/powergrid-ai-germany-v1'
    assert api.model_info(repo).private and not api.file_exists(repo, 'archives/'+NAME+'.tgz')
    ARCHIVE.mkdir(); manifest = {}
    for p in sorted(sources):
        assert p.is_file() and not p.is_symlink()
        name = str(p.relative_to(ROOT)); before = digest(p); target = ARCHIVE/name
        target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(p.read_bytes())
        assert digest(target) == before == digest(p); manifest[name] = before
    save(ARCHIVE/'recovery.json', {'source_validation_archive': read(ROOT/'ai/strong/selected-public-policy-final-source-evidence-v1.json')['archive'],
        'instruction': 'Restore referenced synthetic source-validation metadata if needed; never execute its contracts or the archived synthetic release. These are completed transport tests, not real final admission. Do not rerun successful checks or restart either original research owner.'})
    manifest['recovery.json'] = digest(ARCHIVE/'recovery.json'); save(ARCHIVE/'manifest.json', manifest)
    save(ARCHIVE.with_suffix('.intent.json'), {'stage': 'upload_intent', 'manifest_sha256': digest(ARCHIVE/'manifest.json')})
    archive = upload_evidence(ARCHIVE)
    save(DESCRIPTOR, {'complete': True, 'tests': 12, 'report_sha256': digest(REPORT), 'archive': archive,
        'real_release_admitted': False, 'candidate_selected': False, 'qualified': False, 'reserved_final_seeds_used': False})
    ARCHIVE.with_suffix('.intent.json').write_text(json.dumps({'stage': 'uploaded_download_verified', 'archive': archive,
        'descriptor_sha256': digest(DESCRIPTOR)}, indent=2)+'\n')
    print(json.dumps({'passed': True, 'tests': 12, 'archive': archive}), flush=True)


if __name__ == '__main__': main()
