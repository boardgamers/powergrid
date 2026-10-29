"""Collect the completed pilot and independently check every terminal credit.

No inference, simulation, training, submission or policy selection occurs here.
"""
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from fractions import Fraction
import json
from pathlib import Path
import re
import statistics

from huggingface_hub import HfApi
from checkpoint_bucket_archives_v3 import download_archive, checked_receipt
from current_auction_resource_job_v2 import tree
from prepare_auction_discount_teacher_v1 import ROOT, PROTOCOL, digest, read, object_hash, save

OUT = ROOT/'ai/runs/auction-discount-teacher-collected-v1'
REPORT = ROOT/'ai/strong/auction-discount-teacher-results-v1.json'


def audit(root, result, protocol_sha):
    """Recompute action/world coverage, tie credits and reported margins."""
    assert object_hash(root['request']) == root['public_root_sha256']
    assert result['protocol_sha256'] == protocol_sha and result['training_ready'] is False
    c = result['continuations']; options = list(range(len(root['legal'])))
    baseline = result['baseline']; seat = root['request']['player']; players = root['players']
    assert c['mode'] == 'neural_population' and c['options'] == options and baseline in options
    assert c['samples'] == c['count'] == 4 and c['begin'] == 0
    assert len(c['rows']) == 4*len(options)
    assert c['caps'] == c['outer_caps'] == c['nested_caps'] == 0 and c['usable'] is True
    assert c['qualification_eligible'] is False and c['seconds'] > 0
    assert len(root['request']['state']['players']) == players and 0 <= seat < players
    credits = {a: [] for a in options}; worlds = {}; roles = {}; steps = neural = 0
    for ordinal, row in enumerate(c['rows']):
        sample, action = divmod(ordinal, len(options))
        assert (row['env'], row['sample'], row['actionIndex']) == (ordinal, sample, action)
        assert row['truncated'] is False and 0 < row['steps'] <= 2400
        world = row['diagnostic']['sampledWorldSha256']
        assert re.fullmatch('[a-f0-9]{64}', world) and worlds.setdefault(sample, world) == world
        assert len(row['roles']) == players and roles.setdefault(sample, row['roles']) == row['roles']
        terminal = row['diagnostic']['terminal']; assert len(terminal) == players
        scores = [tuple(p[k] for k in ('powered', 'money', 'cities')) for p in terminal]
        assert all(type(v) is int and v >= 0 for score in scores for v in score)
        best = max(scores)
        credit = Fraction(1, scores.count(best)) if scores[seat] == best else Fraction(0)
        assert row['value'] == float(credit)
        credits[action].append(credit)
        assert row['searchStats']['truncated'] == 0
        assert sum(row['policyDecisions'].values()) == row['steps']
        steps += row['steps']; neural += row['policyDecisions']['neural']
    assert neural == c['inference_decisions']['neural']
    assert c['inference_decisions']['surrogate'] == 0
    means = {a: sum(values, Fraction(0))/4 for a, values in credits.items()}
    margins = {a: means[a]-means[baseline] for a in options}
    eligible = [a for a in options if a == baseline or margins[a] > Fraction(1, 8)]
    selected = max(eligible, key=lambda a: (means[a], a == baseline, -a))
    expected_means = {str(a): str(v) for a, v in means.items()}
    expected_margins = {str(a): str(v) for a, v in margins.items()}
    exact = result['exact_summary']
    assert exact['baseline'] == baseline and exact['selected'] == selected and exact['eligible'] == eligible
    assert exact['meanCredits'] == expected_means and exact['pairedMeanMargins'] == expected_margins
    assert exact['populationMeanMargins'] == {'neural_population': expected_margins}
    assert exact['fallbackReason'] is None and exact['truncated'] == 0
    assert exact['minimumAdvantage'] == '1/8' and exact['populationModes'] == ['neural_population']
    return {'rootId': root['rootId'], 'players': players, 'split': root['split'], 'kind': root['kind'],
            'sealed': root['sealed'], 'variant': root['variant'], 'options': len(options),
            'rollouts': len(c['rows']), 'seconds': c['seconds'], 'steps': steps, 'neural_decisions': neural,
            'baseline': baseline, 'pilot_selected': selected, 'mean_credits': expected_means,
            'paired_margins': expected_margins, 'public_root_sha256': root['public_root_sha256']}


def main():
    assert not REPORT.exists(), 'Inspect completed pilot audit before rerunning'
    protocol = read(PROTOCOL); launch = read(ROOT/'ai/strong/auction-discount-teacher-launch-v1.json')
    api = HfApi(); info = api.inspect_job(job_id=launch['job_id'], namespace='coyotte508')
    assert info.status.stage == 'COMPLETED', 'Preserve incomplete/failed pilots; do not retry'
    log = (OUT/'job.log').read_text(); records = []
    for line in log.splitlines():
        try:
            value = json.loads(line)
            if isinstance(value, dict): records.append(value)
        except ValueError: pass
    receipts = [r for r in records if 'bucket_evidence' in r]
    assert receipts == read(OUT/'receipts.json') and len(receipts) == 70
    final = records[-1]; assert final['complete'] and final['executed'] and final['roots'] == 70
    roots = read(ROOT/protocol['roots']['file']); assert digest(ROOT/protocol['roots']['file']) == protocol['roots']['sha256']
    assert [r['rootId'] for r in roots] == [r['rootId'] for r in receipts]
    assert len({r['rootId'] for r in roots}) == len({r['public_root_sha256'] for r in roots}) == 70
    identity = read(ROOT/'ai/runs/auction-discount-teacher-preflight-v1/report.json')['identity']

    def collect(index):
        receipt = receipts[index]['bucket_evidence']; name = f'pg-discount-teacher-pilot-v1-root-{index:03d}'
        dest = OUT/f'roots/{index:03d}'; checked_receipt(receipt, name)
        if not dest.exists(): download_archive(receipt, name, dest, HfApi())
        tree(dest, 'manifest.json', receipt['manifest_sha256'])
        root = read(dest/'root.json'); result = read(dest/'result.json')
        assert root == roots[index] and result['identity'] == identity
        summary = audit(root, result, digest(PROTOCOL))
        summary['result_sha256'] = digest(dest/'result.json')
        return summary

    with ThreadPoolExecutor(max_workers=4) as pool: summaries = list(pool.map(collect, range(70)))
    assert Counter(s['split'] for s in summaries) == {'train': 36, 'validation': 34}
    assert sum(s['rollouts'] for s in summaries) == final['rollouts']
    costs = {}
    for players in range(2, 7):
        rows = [r for r in summaries if r['players'] == players]
        seconds = sum(r['seconds'] for r in rows); rollouts = sum(r['rollouts'] for r in rows)
        costs[str(players)] = {'roots': len(rows), 'rollouts': rollouts, 'seconds': seconds,
            'seconds_per_rollout': seconds/rollouts, 'median_seconds_per_root': statistics.median(r['seconds'] for r in rows)}
    report = {'created_at': datetime.now(timezone.utc).isoformat(), 'job_id': launch['job_id'],
        'stage': info.status.stage, 'independently_audited': True, 'roots': len(summaries),
        'rollouts': sum(r['rollouts'] for r in summaries), 'steps': sum(r['steps'] for r in summaries),
        'neural_decisions': sum(r['neural_decisions'] for r in summaries), 'caps': 0,
        'job_program_seconds': final['seconds'], 'continuation_seconds': sum(r['seconds'] for r in summaries),
        'costs_by_player_count': costs, 'source': launch['source'], 'protocol_sha256': digest(PROTOCOL),
        'log_sha256': digest(OUT/'job.log'), 'receipts_sha256': digest(OUT/'receipts.json'),
        'auditor_sha256': digest(__file__), 'identity': identity, 'summaries': summaries,
        'pilot_targets_training_ready': False, 'new_gradient_updates': 0,
        'interpretation': 'Coverage/runtime evidence only. Four sampled worlds are too few for reliable training targets or playing-strength claims.',
        'qualified': False, 'reserved_final_seeds_used': False}
    save(REPORT, report)
    print(json.dumps({k: report[k] for k in ('roots', 'rollouts', 'steps', 'neural_decisions', 'caps',
        'job_program_seconds', 'continuation_seconds', 'costs_by_player_count')}), flush=True)


if __name__ == '__main__': main()
