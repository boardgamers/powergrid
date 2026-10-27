"""Archive the verified pilot source and original four submission handles."""
import argparse
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import shutil

from policy_iteration_evidence_archive import upload_evidence
from huggingface_hub import HfApi
from public_policy_development_job_v1 import digest, read, write

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'ai/runs/conservative-auction-runtime-launch-evidence-v2'
DEST = ROOT/'ai/strong/conservative-auction-runtime-launch-evidence-v2.json'
spec = importlib.util.spec_from_file_location('pilot_manager', Path(__file__).with_name('manage-conservative-auction-runtime-v2.py'))
manager = importlib.util.module_from_spec(spec); spec.loader.exec_module(manager)


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--archive', action='store_true', required=True); parser.parse_args()
    assert not any(p.exists() for p in (OUT, OUT.with_suffix('.tgz'), OUT.with_suffix('.intent.json'), DEST))
    api = HfApi(); assert api.repo_info('coyotte508/powergrid-ai-germany-v1').private
    assert 'archives/'+OUT.name+'.tgz' not in api.list_repo_files('coyotte508/powergrid-ai-germany-v1')
    source = manager.source_checked(); guards = []
    for row in source['rows']:
        guard = read(manager.OUT/row['name']/'launch.json')
        assert guard['stage'] == 'launched' and guard['source'] == source and guard['row'] == row
        guards.append({'name': row['name'], 'job_id': guard['job_id']})
    assert len({row['job_id'] for row in guards}) == 4
    paths = {p for p in manager.OUT.rglob('*') if p.is_file() and not p.name.startswith('.')}
    paths.update(p for p in manager.LOCAL.iterdir() if p.is_file())
    for name in ('prepare-conservative-auction-runtime-v2.py', 'manage-conservative-auction-runtime-v2.py',
                 'public_policy_measured_job_v1.py', 'test_conservative_auction_runtime_v2.py',
                 'archive-conservative-auction-runtime-launch-v2.py', 'conservative-auction-development-protocol-v2.json',
                 'conservative-auction-design-evidence-v1.json', 'conservative-auction-forced-prior-evidence-v1.json', 'conservative-auction-forced-prior-results-v1.json', 'policy_iteration_evidence_archive.py'):
        paths.add(ROOT/'ai/strong'/name)
    paths.update((manager.SOURCE, ROOT/'ai/runs/conservative-auction-runtime-tests-v2.log',
                  ROOT/'ai/strong/conservative-auction-runtime-launch-state-v2.json'))
    paths.update((ROOT/'ai/RESUME.md', ROOT/'ai/CONSERVATIVE-AUCTION-RUNTIME-2026-10-27.md'))
    OUT.mkdir(); hashes = {}
    for path in sorted(paths):
        name = str(path.relative_to(ROOT)); dest = OUT/name; dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, dest); hashes[name] = digest(path); assert digest(dest) == hashes[name]
    checkpoint = {'created_at': datetime.now(timezone.utc).isoformat(), 'original_jobs': guards,
        'status': 'submitted; completion and runtime admission pending', 'source': source,
        'preflight': read(manager.LOCAL/'verified.json'), 'measurement_check': read(manager.OUT/'local-check.json'),
        'new_hf_jobs': 4, 'runtime_games_planned': 64, 'new_strength_games': 0,
        'gradient_updates': 0, 'grid_admitted': False, 'reserved_final_seeds_used': False}
    write(OUT/'checkpoint.json', checkpoint); hashes['checkpoint.json'] = digest(OUT/'checkpoint.json')
    write(OUT/'manifest.json', hashes)
    write(OUT.with_suffix('.intent.json'), {'manifest_sha256': digest(OUT/'manifest.json'), 'archive_path': 'archives/'+OUT.name+'.tgz'})
    print(json.dumps({'stage': 'uploading', 'files': len(hashes)+1}), flush=True)
    evidence = upload_evidence(OUT)
    write(DEST, {'launch_evidence_complete': True, 'runtime_results_complete': False,
        'original_jobs': guards, 'source_sha256': digest(manager.SOURCE), 'archive': evidence,
        'preflight': checkpoint['preflight'], 'measurement_check': checkpoint['measurement_check'],
        'submission_tests': 7, 'grid_admitted': False, 'reserved_final_seeds_used': False})
    print(json.dumps(evidence), flush=True)


if __name__ == '__main__': main()
