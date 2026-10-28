"""Archive historical-prefix recovery with the original train/validation split."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from huggingface_hub import HfApi
from policy_iteration_evidence_archive import upload_evidence
from public_policy_development_job_v1 import digest, read

ROOT = Path(__file__).resolve().parents[2]
NAME = 'auction-training-history-evidence-v1'
OUT = ROOT / 'ai/runs' / NAME
RESULT = ROOT / 'ai/strong' / (NAME + '.json')


def save(p, value):
    with p.open('x') as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write('\n')


def main():
    for p in (OUT, OUT.with_suffix('.tgz'), OUT.with_suffix('.intent.json'), RESULT):
        assert not p.exists(), 'Inspect previous archive intent/outcome before retrying'
    sources = {Path(__file__).resolve()}
    reports, rows, episodes = {}, [], set()
    for version, expected in ((1, 160), (2, 880)):
        run = ROOT / f'ai/runs/auction-training-history-v{version}'
        result = ROOT / f'ai/strong/auction-training-history-results-v{version}.json'
        report, design = read(result), read(run / 'design.json')
        assert report['passed'] and report['prefixes_verified'] == expected
        assert report['design_sha256'] == digest(run / 'design.json')
        assert report['qualification_eligible'] is report['training_ready'] is report['reserved_final_seeds_used'] is False
        assert all(report[k] == 0 for k in ['new_hf_jobs', 'new_inference', 'new_games', 'new_rollouts', 'new_gradients'])
        for name, sha in report['artifacts'].items():
            assert digest(run / name) == sha
        for name, sha in design['code'].items():
            assert digest(ROOT / name) == sha
            sources.add(ROOT / name)
        current_episodes = {(r['players'], r['episode']) for r in report['prefixes']}
        assert len(current_episodes) == expected and not current_episodes & episodes
        episodes.update(current_episodes)
        if version == 2:
            assert design['prior_report_sha256'] == digest(ROOT / 'ai/strong/auction-training-history-results-v1.json')
            assert all(r['split'] == 'train' for r in report['prefixes'])
        recovered = [json.loads(line) for line in (run / 'newly-affordable-roots.jsonl').read_text().splitlines()]
        assert len(recovered) == report['newly_affordable_roots']
        assert Counter(r['split'] for r in recovered) == report['coverage']['splits']
        for r in recovered:
            assert not r['labelled'] and (r['players'], r['episode']) in current_episodes
            assert r['split'] == ('validation' if r['deal'] in (0, 4, 8, 12) else 'train')
            assert r['gameSeed'].startswith('policy-iteration-training-v2-')
            g, actor = r['request']['state'], r['request']['player']
            assert g['seed'] == 'secret' and g['powerPlantsDeck'] == g['hiddenLog'] == []
            assert 'powerPlantDeckAfterStep3' not in g and 'automation' not in g
            assert all(p['lastMove'] is None for p in g['players'])
            if r['sealed']:
                assert g['currentBid'] == 0 and all(not p['bid'] for p in g['players'])
            assert g['options']['showMoney'] and g['options']['variant'] == 'recharged'
            assert g['phase'] == 'Auction' and not g.get('chosenPowerPlant') and g['plantDiscountActive']
            assert actor == g['currentPlayers'][0] and g['players'][actor]['money'] == r['money']
            assert 1 <= r['money'] < r['plant'] == g['actualMarket'][0]['number']
            assert r['opening_bid'] == 1 and r['recorded_action'] == {'name': 'Pass', 'data': True}
            assert r['old_legal'] == [{'name': 'Pass', 'data': True}]
            assert len(r['legal']) == 2 and {'name': 'ChoosePowerPlant', 'data': r['plant']} in r['legal']
        rows.extend(recovered)
        reports[str(version)] = {'report_sha256': digest(result), 'design_sha256': report['design_sha256'],
            'prefixes': expected, 'transitions': report['transitions'], 'newly_affordable_roots': len(recovered),
            'coverage': report['coverage'], 'learner_roots': report['learner_roots'], 'opponent_roots': report['opponent_roots']}
        sources.add(result)
        sources.update(p for p in run.rglob('*') if p.is_file())
        sources.add(ROOT / f'ai/runs/auction-training-history-v{version}-first.log')
    assert len(episodes) == 1040
    keys = [(r['players'], r['episode'], r['before_move'], r['request']['player']) for r in rows]
    assert len(keys) == len(set(keys))
    public_hashes = [hashlib.sha256(json.dumps(r['request'], sort_keys=True).encode()).hexdigest() for r in rows]
    assert len(set(public_hashes)) == len(public_hashes)
    sources.update(ROOT / name for name in (
        'ai/AUCTION-TRAINING-HISTORY-2026-10-28.md', 'ai/RESUME.md',
        'ai/strong/current-engine-compatibility-evidence-v1.json',
        'ai/strong/policy-iteration-collection-source-v2.json',
        'ai/strong/policy_iteration_evidence_archive.py', 'ai/strong/strategic_collection.py',
        'ai/runs/conservative-auction-development-attempts-coordinator-v1/state.json'))
    api = HfApi(); repo = 'coyotte508/powergrid-ai-germany-v1'
    assert api.model_info(repo).private and not api.file_exists(repo, 'archives/' + NAME + '.tgz')
    OUT.mkdir(); manifest = {}
    for p in sorted(sources):
        assert p.is_file() and not p.is_symlink()
        name = str(p.relative_to(ROOT)); target = OUT / name
        target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(p.read_bytes())
        manifest[name] = digest(target)
    save(OUT / 'manifest.json', manifest)
    intent = {'created_at': datetime.now(timezone.utc).isoformat(), 'stage': 'prepared_for_upload',
        'manifest_sha256': digest(OUT / 'manifest.json')}
    save(OUT.with_suffix('.intent.json'), intent)
    archive = upload_evidence(OUT)
    save(RESULT, {'status': 'natural_low_cash_nomination_states_recovered_with_split_preserved',
        'reports': reports, 'prefixes': len(episodes), 'transitions': sum(r['transitions'] for r in reports.values()),
        'recovered_roots': len(rows), 'split_counts': dict(Counter(r['split'] for r in rows)),
        'unique_public_requests': len(set(public_hashes)), 'labelled': False, 'training_ready': False,
        'new_hf_jobs': 0, 'new_inference': 0, 'new_games': 0, 'new_rollouts': 0, 'new_gradients': 0,
        'qualification_eligible': False, 'reserved_final_seeds_used': False, 'archive': archive})
    OUT.with_suffix('.intent.json').write_text(json.dumps({**intent, 'stage': 'uploaded_download_verified',
        'archive': archive, 'descriptor_sha256': digest(RESULT)}, indent=2) + '\n')
    print(json.dumps(archive), flush=True)


if __name__ == '__main__':
    main()
