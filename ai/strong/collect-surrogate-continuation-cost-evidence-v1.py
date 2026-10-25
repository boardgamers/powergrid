"""Archive every original cost calibration and independently count terminal/search work."""
import argparse
from fractions import Fraction
import importlib.util
from pathlib import Path
import shutil

from strategic_collection import ROOT, read, write, digest
from policy_iteration_evidence_archive import upload_evidence

STRONG = ROOT/'ai/strong'
spec = importlib.util.spec_from_file_location('cost_evidence_manager', STRONG/'manage-surrogate-continuation-cost-v1.py')
manager = importlib.util.module_from_spec(spec); spec.loader.exec_module(manager)
OUT = ROOT/'ai/runs/surrogate-continuation-cost-complete-evidence-v1'
DESCRIPTOR = STRONG/'surrogate-continuation-cost-complete-evidence-v1.json'


def independent_credit(row, seat, n):
    assert row['truncated'] is False
    players = row['diagnostic']['terminal']; assert len(players) == n
    scores = [tuple(p[k] for k in ('powered', 'money', 'cities')) for p in players]
    assert all(type(v) is int and v >= 0 for score in scores for v in score)
    assert all(powered <= cities for powered, _, cities in scores)
    winners = [i for i, score in enumerate(scores) if not any(other > score for other in scores)]
    credit = Fraction(int(seat in winners), len(winners))
    assert row['value'] == float(credit)
    return credit


def work_counts(result, workers):
    """Prior-bid search is shared by both actions inside the same worker/world."""
    assert result['begin'] == 0 and result['count'] == result['samples'] == 8
    assert len(result['rows']) == 16 and workers == 8
    # The frozen EnginePool gives each worker two consecutive environments;
    # options are ordered by world, then the two actions. Thus each prior is
    # actually computed once per world and copied into both action receipts.
    forward = sum(r['searchStats']['evaluations'] for r in result['rows'])
    row_attributed_prior = sum(r['diagnostic']['priorSearchStats']['evaluations'] for r in result['rows'])
    prior = 0
    for sample in range(8):
        a, b = result['rows'][sample*2:sample*2+2]
        assert a['sample'] == b['sample'] == sample
        assert a['diagnostic']['priorSearchStats'] == b['diagnostic']['priorSearchStats']
        assert a['initialBelief'] == b['initialBelief']
        prior += a['diagnostic']['priorSearchStats']['evaluations']
    assert row_attributed_prior == 2*prior
    return {'forward_evaluations': forward, 'prior_evaluations_once_per_worker_world': prior,
            'row_attributed_prior_evaluations': row_attributed_prior,
            'actual_nested_evaluations': forward+prior,
            'row_attributed_nested_evaluations': forward+row_attributed_prior}


def audit():
    assert manager.INDEX.exists(), 'All 24 original calibrations must verify and index before archival'
    previous = read(manager.INDEX); result = manager.index(); assert previous == result
    assert result['complete'] and result['jobs'] == 24 and result['continuations'] == 768 and result['caps'] == 0
    inputs = read(manager.launcher.PREP/'layout'/manager.INPUTS.relative_to(ROOT))
    measurements = {}; credits_checked = 0; work = {'forward_evaluations': 0, 'prior_evaluations_once_per_worker_world': 0,
        'row_attributed_prior_evaluations': 0, 'actual_nested_evaluations': 0, 'row_attributed_nested_evaluations': 0}
    for key, receipt in sorted(result['cases'].items()):
        folder = manager.COLLECTED/receipt['case']/'artifacts'; q = inputs['roots'][key]['identity']
        modes = {}
        for mode in manager.MODES:
            raw = read(folder/mode/'result.json'); intent = read(folder/mode/'intent.json')
            for row in raw['rows']:
                independent_credit(row, q['seat'], q['players']); credits_checked += 1
            counts = work_counts(raw, intent['workers'])
            for name, value in counts.items(): work[name] += value
            modes[mode] = {**receipt['review']['modes'][mode], 'search_work': counts}
        assert sum(m['search_work']['row_attributed_nested_evaluations'] for m in modes.values()) == receipt['review']['nested_reference_evaluations']
        measurements[key] = {'job_id': receipt['job_id'], 'modes': modes,
                             'raw_evidence_bytes': receipt['review']['raw_evidence_bytes']}
    assert credits_checked == 768
    return {'complete': True, 'jobs': 24, 'roots': 24, 'continuations': credits_checked, 'caps': 0,
            'all_terminal_credits_recomputed': True, 'all_saved_job_audits_reproduced': True,
            'index_sha256': digest(manager.INDEX), 'source': result['source'], 'plan_sha256': result['plan_sha256'],
            'measurements': measurements, 'search_work': work,
            'search_work_note': 'Prior-bid evaluations are computed once per worker/world but copied into both action rows. The original receipt field nested_reference_evaluations is row-attributed, not the physical count. This independent audit deduplicates priors using the frozen 16-environment / 8-worker partition without changing any execution or raw receipt.',
            'code_hashes': {**manager.code_hashes(), str(Path(__file__).relative_to(ROOT)): digest(__file__),
                            'ai/pool.py': digest(ROOT/'ai/pool.py')},
            'full_study_admitted': False, 'gradient_updates': 0, 'new_hf_jobs': 0,
            'qualification_eligible': False, 'reserved_final_seeds_used': False,
            'scope': 'Complete HF cost calibration on separate runtime roots. Not fidelity, model selection, calibrated win probability or full-game playing strength.'}


def main(archive):
    review = audit()
    if not archive: print({k: review[k] for k in ('complete', 'jobs', 'continuations', 'search_work')}); return
    assert not any(p.exists() for p in (OUT, OUT.with_suffix('.tgz'), DESCRIPTOR)), 'Reconcile the original archive before retry'
    files = [manager.INDEX, manager.launcher.PLAN, manager.launcher.SOURCE, manager.launcher.PREFLIGHT,
             STRONG/'test_surrogate_continuation_cost_evidence_v1.py', STRONG/'test_surrogate_continuation_runtime_v1.py',
             STRONG/'policy_iteration_evidence_archive.py']
    files += [ROOT/name for name in review['code_hashes']]
    files += [ROOT/name for name in review['source']['new_files'] if (ROOT/name).exists()]
    files += [manager.launcher.PREP/'layout'/manager.INPUTS.relative_to(ROOT), manager.launcher.PREP/'layout-check.json',
              ROOT/'ai/runs/surrogate-continuation-cost-checkpoint-v1.json',
              ROOT/'ai/runs/surrogate-continuation-cost-tests-v1.log',
              ROOT/'ai/runs/surrogate-continuation-cost-evidence-tests-v1.log']
    files += [p for p in manager.COLLECTED.rglob('*') if p.is_file()]
    files += list(manager.launcher.GUARDS.glob('*.json'))
    OUT.mkdir()
    for path in sorted(set(files)):
        assert path.is_file() and not path.is_symlink()
        destination = OUT/path.relative_to(ROOT); destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination); assert digest(destination) == digest(path)
    write(OUT/'review.json', review)
    write(OUT/'manifest.json', {str(p.relative_to(OUT)): digest(p) for p in sorted(OUT.rglob('*')) if p.is_file()})
    write(DESCRIPTOR, {**review, **upload_evidence(OUT)})
    print({k: read(DESCRIPTOR)[k] for k in ('revision', 'archive_sha256', 'archived_files', 'remote_archive_verified')})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__); parser.add_argument('--archive', action='store_true')
    main(parser.parse_args().archive)
