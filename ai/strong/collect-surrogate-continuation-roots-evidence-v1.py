"""Preserve the complete fresh-root corpus and independently check its aggregate."""
import argparse
from collections import Counter
from fractions import Fraction
import importlib.util
from pathlib import Path
import shutil

from strategic_collection import ROOT, read, write, digest
from policy_iteration_evidence_archive import upload_evidence
from surrogate_continuation_analysis_v1 import manifest_roots, group

STRONG = ROOT/'ai/strong'
spec = importlib.util.spec_from_file_location('complete_roots_manager', STRONG/'manage-surrogate-continuation-roots-v1.py')
manager = importlib.util.module_from_spec(spec); spec.loader.exec_module(manager)
OUT = ROOT/'ai/runs/surrogate-continuation-roots-complete-evidence-v1'
DESCRIPTOR = STRONG/'surrogate-continuation-roots-complete-evidence-v1.json'


def audit():
    assert manager.INDEX.exists(), 'All five original fresh-root jobs must verify first'
    saved = read(manager.INDEX); current = manager.index(); assert saved == current
    path = ROOT/current['root_manifest']; before = digest(path)
    assert before == current['root_manifest_sha256']
    manifest = read(path); roots = manifest_roots(manifest)
    assert len(roots) == current['selected_roots']
    games = terminal_players = missing_phases = 0; eligible = 0; per_count = Counter(); clusters = Counter()
    # The root manifest/pairs are already frozen. Terminal auditing never chooses roots.
    for game in manifest['games']:
        q = game['identity']; folder = manager.COLLECTED/game['case']/'artifacts/games'/f'game-{q["episode"]}'
        assert read(folder/'contract.json') == q and digest(folder/'roots.json') == game['roots_sha256']
        terminal = read(folder/'terminal.json')
        assert terminal['truncated'] is False and terminal['searchStats']['search_geo']['truncated'] == 0
        players = terminal['final']['players']; assert len(players) == q['players']
        scores = [tuple(p[key] for key in ('powered', 'money', 'cities')) for p in players]
        assert all(type(v) is int and v >= 0 for row in scores for v in row)
        assert all(powered <= cities for powered, _, cities in scores)
        winners = [i for i, score in enumerate(scores) if not any(other > score for other in scores)]
        credits = [Fraction(int(i in winners), len(winners)) for i in range(q['players'])]
        assert terminal['value'] == [float(value) for value in credits]
        games += 1; terminal_players += len(players); per_count[q['players']] += 1
        missing_phases += len(game['missing_phases']); eligible += game['eligible_decisions']
    for root in roots.values(): clusters[f'{group(root)}/{root["identity"]["deal"]}'] += 1
    assert games == 160 and digest(path) == before
    files = [Path(__file__), STRONG/'surrogate_continuation_analysis_v1.py',
             STRONG/'surrogate-continuation-analysis-design-v1.json', STRONG/'policy_iteration_evidence_archive.py']
    return {'complete': True, 'jobs': 5, 'games': games, 'selected_roots': len(roots),
            'eligible_decisions': eligible, 'missing_phases': missing_phases, 'caps': 0,
            'games_per_count': dict(sorted(per_count.items())), 'phase_counts': manifest['phase_counts'],
            'roots_per_group_deal': dict(sorted(clusters.items())),
            'terminal_players_independently_checked': terminal_players,
            'root_manifest_sha256': before, 'index_sha256': digest(manager.INDEX),
            'source': current['source'], 'cases': current['cases'],
            'protocol_sha256': current['protocol_sha256'], 'plan_sha256': current['plan_sha256'],
            'code_hashes': {**manager.code_hashes(), **{str(p.relative_to(ROOT)): digest(p) for p in files}},
            'gradient_updates': 0, 'new_hf_jobs': 0, 'continuation_study_launched': False,
            'qualification_eligible': False, 'reserved_final_seeds_used': False,
            'scope': 'Complete fresh, outcome-independent public roots and frozen action pairs. No learned-surrogate fidelity, action-selection targets or playing-strength qualification.'}


def main(archive=False):
    review = audit()
    if not archive:
        print({k: review[k] for k in ('complete', 'jobs', 'games', 'selected_roots', 'eligible_decisions', 'missing_phases', 'caps')})
        return
    assert not any(p.exists() for p in (OUT, OUT.with_suffix('.tgz'), DESCRIPTOR)), 'Reconcile the original upload; never repeat an uncertain archive'
    files = [manager.INDEX, manager.launcher.PLAN, manager.launcher.SOURCE,
             STRONG/'test_surrogate_continuation_analysis_v1.py',
             STRONG/'test_surrogate_continuation_root_collection_v1.py',
             ROOT/'ai/runs/surrogate-continuation-analysis-preflight-v1.json',
             ROOT/'ai/runs/surrogate-continuation-analysis-tests-v1.log',
             ROOT/'ai/runs/surrogate-continuation-roots-coordinator-v1/state.json']
    files += [ROOT/name for name in review['code_hashes']]
    files += [ROOT/name for name in review['source']['new_files']]
    files += list(manager.launcher.GUARDS.glob('*.json'))
    files += [p for folder in (manager.COLLECTED, manager.FROZEN) for p in folder.rglob('*') if p.is_file()]
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
