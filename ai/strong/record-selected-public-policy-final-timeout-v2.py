"""Record measured final-shard timeout compatibility without admitting jobs.

Uses only the four complete runtime pilots and synthetic final-release controls.
No confirmation outcomes, new simulations, training, candidate selection or jobs.
"""
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import importlib.util
import json
import math
from pathlib import Path
import shutil

from huggingface_hub import HfApi
from policy_iteration_evidence_archive import upload_evidence
from public_policy_final_audit_v1 import digest, read, schedule
from selected_public_policy_final_dispatch_v1 import durable_write, validate_release

ROOT = Path(__file__).resolve().parents[2]
STRONG = ROOT / 'ai/strong'
RUNS = ROOT / 'ai/runs'
OUT = RUNS / 'selected-public-policy-final-timeout-v2'
REPORT = STRONG / 'selected-public-policy-final-timeout-v2.json'
ARCHIVE = RUNS / 'selected-public-policy-final-timeout-evidence-v2'
DESCRIPTOR = STRONG / 'selected-public-policy-final-timeout-evidence-v2.json'


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value); return value


def main():
    assert not REPORT.exists() and not (OUT / 'validation-intent.json').exists()
    assert all(not p.exists() for p in (ARCHIVE, DESCRIPTOR, ARCHIVE.with_suffix('.tgz'), ARCHIVE.with_suffix('.intent.json'))), 'Inspect existing outcome; do not repeat'
    owner = read(RUNS / 'current-auction-network-resume-v1/state.json')
    proc = Path('/proc') / str(owner['pid'])
    assert owner['pid'] == 3788704 and proc.is_dir() and (proc / 'stat').read_text().split()[2] != 'Z'
    assert 'coordinate-current-auction-network-resume-v1.py --start-reviewed' in (proc / 'cmdline').read_text().replace('\0', ' ')
    assert all(digest(ROOT / n) == sha for n, sha in owner['code_hashes'].items())
    test_counts = {'dispatch': 14, 'collection': 16, 'streaming': 8}
    for name, count in test_counts.items():
        log = (OUT / (name + '-tests-first.log')).read_text()
        assert f'Ran {count} tests' in log and log.rstrip().endswith('OK')
    planner = module('unchanged_confirmation_resource_planner', STRONG / 'prepare-current-auction-grid-v1.py')
    source = read(STRONG / 'current-auction-grid-source-v1.json')
    pilots = read(STRONG / 'current-auction-runtime-results-v1.json')
    pilot_source = read(STRONG / 'current-auction-runtime-source-v1.json')
    assert source['runtime_results_sha256'] == digest(STRONG / 'current-auction-runtime-results-v1.json')
    sizing = planner.resources(planner.protocol(), pilots, pilot_source, digest(STRONG / 'current-auction-runtime-source-v1.json'))
    assert sizing == source['sizing']
    projections = {}
    for arm, seconds in sizing['per_game_seconds'].items():
        projections[arm] = {}
        for n in range(2, 7):
            games = 16*n
            projected = sizing['setup_allowance_seconds'] + sizing['runtime_multiplier']*seconds*games
            hours = math.ceil(projected/(sizing['timeout_utilization']*3600))
            assert hours <= 24
            projections[arm][str(n)] = {'games_per_fixed_final_shard': games,
                'projected_seconds_with_existing_margin': projected, 'timeout_hours': hours,
                'exceeds_previous_validator_cap': hours > 12}
    assert projections['conservative_population']['6']['timeout_hours'] == 13
    fixture = RUNS / 'selected-public-policy-final-dispatch-preflight-v1'
    release = deepcopy(read(fixture / 'synthetic-release.json'))
    bootstrap = (fixture / 'final-bootstrap.sh').read_text()
    assert release['plan']['jobs'] == 320 and release['plan']['games'] == 20160
    assert [r['shard'] for r in release['plan']['rows']] == schedule()
    for row in release['plan']['rows']:
        hours = projections['conservative_population'][str(row['shard']['players'])]['timeout_hours']
        release['allocation'][row['name']] = {'flavor': sizing['flavor'], 'timeout': f'{hours}h'}
    old = module('preserved_pre_timeout_extension_dispatch', OUT / 'selected_public_policy_final_dispatch_v1.py')
    try: old.validate_release(release, bootstrap)
    except ValueError as error: rejection = str(error)
    else: raise AssertionError('Old cap did not reject measured final timeout')
    assert rejection == 'Invalid timeout' and len(validate_release(release, bootstrap)) == 320
    inputs = [Path(__file__).resolve(), STRONG / 'selected_public_policy_final_dispatch_v1.py',
        STRONG / 'test_selected_public_policy_final_dispatch_v1.py', STRONG / 'selected_public_policy_final_collection_v1.py',
        STRONG / 'test_selected_public_policy_final_collection_v1.py', STRONG / 'selected_public_policy_final_streaming_v1.py',
        STRONG / 'test_selected_public_policy_final_streaming_v1.py', STRONG / 'prepare-current-auction-grid-v1.py',
        STRONG / 'current-auction-grid-source-v1.json', STRONG / 'current-auction-runtime-results-v1.json',
        STRONG / 'current-auction-runtime-source-v1.json', STRONG / 'final-protocol-multiplayer.json',
        fixture / 'synthetic-release.json', fixture / 'final-bootstrap.sh',
        OUT / 'selected_public_policy_final_dispatch_v1.py', OUT / 'test_selected_public_policy_final_dispatch_v1.py']
    inputs += [OUT / (name + '-tests-first.log') for name in test_counts]
    pins = {str(p.relative_to(ROOT)): digest(p) for p in inputs}
    durable_write(OUT / 'validation-intent.json', {'scope': 'Synthetic final timeout validation only; no actual selection or final admission',
        'input_hashes': pins, 'automatic_retries': False}, exclusive=True)
    durable_write(OUT / 'synthetic-release-with-projected-timeouts.json', release, exclusive=True)
    report = {'passed': True, 'created_at': datetime.now(timezone.utc).isoformat(),
        'scope': 'Original complete runtime-pilot cost extrapolation and synthetic release validation only. Actual final allocation must be reviewed against the complete confirmation costs before admission.',
        'input_hashes': pins, 'tests': test_counts, 'tests_total': sum(test_counts.values()),
        'projections': projections, 'unchanged_final_jobs': 320, 'unchanged_final_games': 20160,
        'synthetic_release_sha256': digest(OUT / 'synthetic-release-with-projected-timeouts.json'),
        'old_validator_rejection': rejection, 'new_validator_accepts_all_original_shards': True,
        'projection_timeout_counts': dict(Counter(a['timeout'] for a in release['allocation'].values())),
        'pilot_jobs': [{k: m[k] for k in ('name', 'job_id', 'arm', 'players', 'games', 'seconds', 'sampled_peak_total_rss_bytes')} for m in sizing['measurements']],
        'workers': sizing['workers'], 'flavor': sizing['flavor'], 'memory_margin': sizing['memory_margin'],
        'doubled_measured_peak_bytes': 2*sizing['sampled_peak_rss_bytes'],
        'existing_memory_envelope_bytes': .8*32*1024**3,
        'documentation': ['https://huggingface.co/docs/hub/en/jobs-configuration'],
        'new_cap_is_local_validation_bound_not_claimed_hf_maximum': True,
        'owner_pid': owner['pid'], 'owner_verified_live': True, 'unchanged_owner_pins': len(owner['code_hashes']),
        'owner_audited_jobs_at_observation': owner['verified_jobs'], 'owner_submitted_jobs_at_observation': owner['submitted_jobs'],
        'new_hf_jobs_by_this_work': 0, 'new_games': 0, 'new_policy_calls': 0,
        'candidate_selected': False, 'actual_final_allocation_admitted': False, 'qualified': False, 'reserved_final_seeds_used': False}
    assert all(digest(ROOT / n) == sha for n, sha in owner['code_hashes'].items())
    assert all(digest(ROOT / n) == sha for n, sha in pins.items())
    durable_write(REPORT, report, exclusive=True)
    repo = 'coyotte508/powergrid-ai-germany-v1'; api = HfApi()
    assert api.model_info(repo).private and not api.file_exists(repo, 'archives/' + ARCHIVE.name + '.tgz')
    sources = {ROOT / n for n in pins} | {REPORT, OUT / 'validation-intent.json',
        OUT / 'synthetic-release-with-projected-timeouts.json', STRONG / 'policy_iteration_evidence_archive.py',
        STRONG / 'selected-public-policy-final-dispatch-evidence-v1.json',
        STRONG / 'selected-public-policy-final-collection-evidence-v1.json',
        STRONG / 'selected-public-policy-final-streaming-evidence-v1.json'}
    ARCHIVE.mkdir(); manifest = {}
    for p in sorted(sources):
        assert p.is_file() and not p.is_symlink()
        name = str(p.relative_to(ROOT)); dest = ARCHIVE / name; dest.parent.mkdir(parents=True, exist_ok=True)
        with p.open('rb') as src, dest.open('xb') as dst: shutil.copyfileobj(src, dst)
        assert digest(dest) == digest(p); manifest[name] = digest(p)
    durable_write(ARCHIVE / 'manifest.json', manifest, exclusive=True)
    durable_write(ARCHIVE.with_suffix('.intent.json'), {'stage': 'upload_intent', 'report_sha256': digest(REPORT)}, exclusive=True)
    evidence = upload_evidence(ARCHIVE)
    durable_write(DESCRIPTOR, {'complete': True, 'archive': evidence, 'report_sha256': digest(REPORT),
        'tests': 38, 'new_games': 0, 'new_jobs': 0, 'qualified': False, 'reserved_final_seeds_used': False}, exclusive=True)
    durable_write(ARCHIVE.with_suffix('.intent.json'), {'stage': 'uploaded_download_verified',
        'archive': evidence, 'descriptor_sha256': digest(DESCRIPTOR)})
    print(json.dumps({'passed': True, 'tests': 38, 'old_cap_rejection': rejection,
        'projected_population_timeout_hours_by_count': {n: p['timeout_hours'] for n, p in projections['conservative_population'].items()},
        'archive': evidence}), flush=True)


if __name__ == '__main__': main()
