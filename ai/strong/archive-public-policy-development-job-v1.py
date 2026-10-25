"""Archive the original local development-job execution; never rerun it."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil

from policy_iteration_evidence_archive import upload_evidence
from public_policy_development_job_v1 import read, write, digest
from public_policy_final_audit_v1 import audit_shard
from public_policy_final_contract_v1 import audit_execution_binding

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT/'ai/runs/public-policy-development-job-preflight-v1'
OUT = ROOT/'ai/runs/public-policy-development-job-evidence-v1'
DESCRIPTOR = ROOT/'ai/strong/public-policy-development-job-evidence-v1.json'


def main():
    parser = argparse.ArgumentParser(__doc__); parser.add_argument('--archive', action='store_true', required=True)
    parser.parse_args()
    assert not any(p.exists() for p in (OUT, OUT.with_suffix('.tgz'), DESCRIPTOR))
    prep = read(RUN/'prepared.json'); result = read(RUN/'result.json')
    assert result['complete'] and result['games'] == 8 and result['decisions'] == 1607
    assert result['all_public_decisions_and_terminals_exact'] and result['runtime_manifest_unchanged']
    assert result['prepared_sha256'] == digest(RUN/'prepared.json')
    assert read(RUN/'state.json')['stage'] == 'complete'
    source = RUN/'source'; assert digest(source/'source-manifest.json') == prep['source_manifest_sha256']
    assert all(digest(source/name) == sha for name, sha in read(source/'source-manifest.json').items())
    case = next(c for c in prep['cases'] if c['name'] == 'filter-offset-2p')
    identity = prep['identities'][case['descriptor']]; target = RUN/case['name']/'evaluation'
    audit = audit_shard(target, case['shard'], identity, reserved=False); assert audit == result['audit']
    binding = audit_execution_binding(target, identity, digest(source/'artifact/ai/strong/public_policy_final_runner_v1.py'))
    assert read(target/'audit.json') == {**audit, 'execution_binding': binding}
    test_log = ROOT/'ai/runs/public-policy-development-job-tests-v1.log'
    assert 'Ran 8 tests' in test_log.read_text() and test_log.read_text().rstrip().endswith('OK')
    study = read(ROOT/'ai/runs/surrogate-continuation-study-coordinator-v1/state.json')
    assert all(digest(ROOT/name) == sha for name, sha in study['code_hashes'].items())
    process = Path('/proc')/str(study['pid'])/'cmdline'
    live = process.exists() and b'coordinate-surrogate-continuation-study-v1.py' in process.read_bytes()
    assert live or study['stage'] in ('complete', 'complete_with_caps')
    assert read(ROOT/'ai/strong/experiments.json')['final_seed_prefix_used'] is False
    checkpoint = {'checked_at': datetime.now(timezone.utc).isoformat(),
                  'previous_goal_turn': 'verified wait: original study PID 3502343 confirmed live; user hybrid question answered',
                  'current_goal_turn': 'progress: portable development job tested on exact frozen runtime and complete games',
                  'study_owner_live': live, 'study_pinned_code_unchanged': True, 'study_state': study,
                  'new_hf_jobs': 0, 'reserved_final_seeds_used': False}
    paths = {p for p in RUN.rglob('*') if p.is_file()}
    paths.update({test_log, Path(__file__), ROOT/'ai/strong/public_policy_development_job_v1.py',
                  ROOT/'ai/strong/test_public_policy_development_job_v1.py',
                  ROOT/'ai/strong/check-public-policy-development-job-v1.py'})
    OUT.mkdir(); hashes = {}
    for path in sorted(paths):
        name = str(path.relative_to(ROOT)); dest = OUT/name; dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest); hashes[name] = digest(path); assert digest(dest) == hashes[name]
    write(OUT/'checkpoint.json', checkpoint); hashes['checkpoint.json'] = digest(OUT/'checkpoint.json')
    write(OUT/'manifest.json', hashes)
    print(json.dumps({'stage': 'uploading', 'files': len(hashes)+1}), flush=True)
    archive = upload_evidence(OUT)
    write(DESCRIPTOR, {**result, 'archive': archive, 'checkpoint': checkpoint,
          'source_files': prep['source_files'], 'unit_tests': 8,
          'limitation': 'Local clean-source execution only. HF bootstrap/submission/collection admission and actual selected-recipe runtime must still be verified. This development wrapper explicitly rejects final games.'})
    print(json.dumps(archive), flush=True)


if __name__ == '__main__':
    main()
