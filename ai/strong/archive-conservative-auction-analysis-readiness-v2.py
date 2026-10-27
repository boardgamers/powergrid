"""Archive analysis tooling/tests without collecting or submitting any jobs."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil

from huggingface_hub import HfApi
import numpy as np
from policy_iteration_evidence_archive import upload_evidence
from public_policy_development_job_v1 import read, write, digest

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'ai/runs/conservative-auction-analysis-readiness-v2'
DESCRIPTOR = ROOT/'ai/strong/conservative-auction-analysis-readiness-v2.json'
OWNER = ROOT/'ai/runs/conservative-auction-development-coordinator-v2/state.json'


def main():
    parser = argparse.ArgumentParser(__doc__); parser.add_argument('--archive', action='store_true', required=True)
    parser.parse_args()
    assert not any(p.exists() for p in (OUT, OUT.with_suffix('.tgz'), OUT.with_suffix('.intent.json'), DESCRIPTOR)), 'Inspect prior archive outcome'
    repo = 'coyotte508/powergrid-ai-germany-v1'; api = HfApi()
    assert api.repo_info(repo).private
    assert 'archives/'+OUT.name+'.tgz' not in api.list_repo_files(repo), 'Inspect existing remote archive'
    owner = read(OWNER); process = Path('/proc')/str(owner['pid'])/'cmdline'
    live = process.exists() and b'coordinate-conservative-auction-development-v2.py' in process.read_bytes()
    assert live or owner['stage'] == 'complete', 'Inspect stopped original owner'
    assert all(digest(ROOT/name) == sha for name, sha in owner['code_hashes'].items())
    statuses = [{'job_id': j, 'stage': api.inspect_job(job_id=j).status.stage} for j in owner['original_pilots']]
    test_log = ROOT/'ai/runs/conservative-auction-analysis-tests-v2.log'
    assert 'Ran 14 tests' in test_log.read_text() and test_log.read_text().rstrip().endswith('OK')
    names = ('conservative_auction_analysis_v2.py', 'compare-conservative-auction-development-v2.py',
             'test_conservative_auction_analysis_v2.py', 'archive-conservative-auction-analysis-readiness-v2.py',
             'conservative-auction-development-protocol-v2.json', 'conservative-auction-development-readiness-v2.json',
             'conservative-auction-runtime-source-v2.json')
    paths = {ROOT/'ai/strong'/name for name in names}
    paths.update((test_log, ROOT/'ai/RESUME.md', ROOT/'ai/CONSERVATIVE-AUCTION-ANALYSIS-2026-10-27.md',
                  ROOT/'ai/CONSERVATIVE-AUCTION-DEVELOPMENT-2026-10-27.md'))
    checkpoint = {'created_at': datetime.now(timezone.utc).isoformat(), 'owner_snapshot': owner,
        'owner_verified_live': live, 'original_pilot_statuses': statuses,
        'analysis_tests_passed': 14, 'numpy_version': np.__version__, 'synthetic_outcomes_are_not_evidence': True,
        'actual_archive_reader_check': {'job_id': '6ae0fa243fb22a235dd31616',
            'revision': '05345057533b5fd407f8466c4dea0f720e22511c',
            'archive_sha256': 'daf7312d68a97860ca5ce3df037ae76f30067d65bfd523aebb0fc7ed666997aa',
            'scope': 'Previously independently verified archive-reader check; no pilot strength interpretation'},
        'previous_goal_turn': 'verified wait on original owner and four exact HF handles',
        'current_goal_turn': 'progress: complete-grid independent analysis implemented and tested; execution pins preserved',
        'analysis_executed_on_development_grid': False, 'new_jobs_from_analysis_work': 0,
        'candidate_selected': False, 'qualification_eligible': False, 'reserved_final_seeds_used': False}
    OUT.mkdir(); hashes = {}
    for path in sorted(paths):
        name = str(path.relative_to(ROOT)); dest = OUT/name; dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, dest); hashes[name] = digest(path); assert digest(dest) == hashes[name]
    write(OUT/'checkpoint.json', checkpoint); hashes['checkpoint.json'] = digest(OUT/'checkpoint.json')
    write(OUT/'manifest.json', hashes)
    with OUT.with_suffix('.intent.json').open('x') as stream:
        json.dump({'manifest_sha256': digest(OUT/'manifest.json'), 'archive_path': 'archives/'+OUT.name+'.tgz'}, stream)
    evidence = upload_evidence(OUT)
    assert all(digest(ROOT/name) == sha for name, sha in owner['code_hashes'].items())
    write(DESCRIPTOR, {'analysis_readiness_verified': True, 'archive': evidence, 'checkpoint': checkpoint,
        'full_development_comparison_complete': False, 'qualification_eligible': False, 'reserved_final_seeds_used': False})
    print(json.dumps(evidence), flush=True)


if __name__ == '__main__': main()
