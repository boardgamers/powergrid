"""Preserve the entire paired study, including capped roots and adverse groups."""
import argparse
from fractions import Fraction
import importlib.util
from pathlib import Path
import shutil

from strategic_collection import ROOT, read, write, digest
from policy_iteration_evidence_archive import upload_evidence

STRONG = ROOT/'ai/strong'
spec = importlib.util.spec_from_file_location('study_archive_manager', STRONG/'manage-surrogate-continuation-study-v1.py')
manager = importlib.util.module_from_spec(spec); spec.loader.exec_module(manager)
OUT = ROOT/'ai/runs/surrogate-continuation-study-complete-evidence-v1'
DESCRIPTOR = STRONG/'surrogate-continuation-study-complete-evidence-v1.json'


def terminal_credit(row, seat, players):
    if row['truncated']:
        assert row['value'] is None and row['diagnostic']['terminal'] is None
        return None
    final = row['diagnostic']['terminal']; assert len(final) == players
    scores = [tuple(p[k] for k in ('powered', 'money', 'cities')) for p in final]
    assert all(type(v) is int and v >= 0 for score in scores for v in score)
    assert all(powered <= cities for powered, _, cities in scores)
    winners = [i for i, score in enumerate(scores) if not any(other > score for other in scores)]
    credit = Fraction(int(seat in winners), len(winners)); assert row['value'] == float(credit)
    return credit


def audit():
    assert manager.INDEX.exists(), 'Index all 480 original jobs before archival; never archive a survivor subset'
    old = read(manager.INDEX); result = manager.index(); assert old == result and result['all_jobs_verified']
    assert result['jobs'] == result['roots'] == 480 and result['continuations'] == 23040
    manifest = read(manager.launcher.builder.FROZEN/'roots.json'); roots = manager.job.manifest_roots(manifest)
    checked = outer_caps = 0; work = {k: 0 for k in ('decisions', 'evaluations', 'truncated')}; measurements = {}
    for rid, receipt in result['paired_records'].items():
        folder = manager.COLLECTED/receipt['case']/'artifacts'; root = roots[rid]; q = root['identity']
        state = read(folder/'job.json'); measurements[rid] = {'case': receipt['case'], 'job_id': receipt['job_id'], 'modes': state['modes']}
        for mode in manager.job.MODES:
            raw = read(folder/mode/'result.json')
            for row in raw['rows']:
                credit = terminal_credit(row, q['seat'], q['players'])
                checked += credit is not None; outer_caps += credit is None
            physical = manager.job.search_work(raw, 8)['physical_total']
            for name in work: work[name] += physical[name]
    assert checked+outer_caps == 23040 and outer_caps <= result['caps']
    comparison = read(manager.ANALYSIS)
    assert manager.job.object_hash(comparison) == result['comparison_sha256_canonical']
    if result['caps']:
        assert comparison['primary'] is comparison['whole_deal_uncertainty'] is None
    else:
        assert checked == 23040 and comparison['complete'] and comparison['groups'] == 60
    return {'all_original_jobs_audited': True, 'complete': result['complete'], 'jobs': 480, 'roots': 480,
            'continuations': 23040, 'caps': result['caps'], 'outer_capped_continuations': outer_caps,
            'terminal_credits_independently_recomputed': checked, 'physical_reference_work': work,
            'measurements': measurements, 'index_sha256': digest(manager.INDEX), 'comparison_sha256': digest(manager.ANALYSIS),
            'source': result['source'], 'plan_sha256': result['plan_sha256'],
            'code_hashes': {**manager.dependencies(), str(Path(__file__).relative_to(ROOT)): digest(__file__)},
            'gradient_updates': 0, 'new_hf_jobs': 0, 'qualification_eligible': False, 'reserved_final_seeds_used': False,
            'scope': 'Complete fixed continuation-fidelity experiment. Capped records and every adverse group retained. No deployment candidate or full-game strength claim.'}


def main(archive=False):
    review = audit()
    if not archive:
        print({k: review[k] for k in ('complete', 'jobs', 'continuations', 'caps', 'terminal_credits_independently_recomputed')}); return
    assert not any(p.exists() for p in (OUT, OUT.with_suffix('.tgz'), DESCRIPTOR)), 'Inspect the original upload intent/receipt before retrying'
    launcher = manager.launcher; builder = launcher.builder
    paths = [manager.INDEX, manager.ANALYSIS, launcher.PLAN, launcher.PROOF, builder.SOURCE,
             launcher.calibration.RESULT, builder.COST, builder.ROOTS,
             STRONG/'policy_iteration_evidence_archive.py', STRONG/'test_surrogate_continuation_study_management_v1.py',
             STRONG/'coordinate-surrogate-continuation-study-v1.py', STRONG/'test_surrogate_continuation_study_coordinator_v1.py',
             STRONG/'test_surrogate_continuation_study_archive_v1.py']
    paths += [ROOT/name for name in review['code_hashes']]
    paths += [builder.FROZEN/name for name in ('roots.json', 'policy.json', 'frozen.json')]
    paths += [ROOT/'ai/runs'/name for name in ('surrogate-continuation-study-management-tests-v1.log',
        'surrogate-continuation-study-coordinator-tests-v1.log', 'surrogate-continuation-study-coordinator-preflight-v1.json',
        'surrogate-continuation-study-archive-tests-v1.log', 'surrogate-continuation-study-archive-preflight-v1.json')]
    paths += list(launcher.GUARDS.glob('*.json'))
    paths += [p for p in manager.COLLECTED.rglob('*') if p.is_file()]
    coordinator = ROOT/'ai/runs/surrogate-continuation-study-coordinator-v1'
    paths += list(coordinator.glob('*.json'))
    OUT.mkdir()
    for path in sorted(set(paths)):
        assert path.is_file() and not path.is_symlink()
        destination = OUT/path.relative_to(ROOT); destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination); assert digest(destination) == digest(path)
    write(OUT/'review.json', review)
    write(OUT/'manifest.json', {str(p.relative_to(OUT)): digest(p) for p in sorted(OUT.rglob('*')) if p.is_file()})
    write(DESCRIPTOR, {**review, **upload_evidence(OUT)})
    print({k: read(DESCRIPTOR)[k] for k in ('complete', 'revision', 'archive_sha256', 'archived_files', 'remote_archive_verified')})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__); parser.add_argument('--archive', action='store_true')
    main(parser.parse_args().archive)
