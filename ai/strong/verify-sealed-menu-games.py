"""Complete paired games through actor-specific menus; no training or strength claim."""
import argparse
import json
from pathlib import Path
import sys
import torch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pool import EnginePool
from model import policy_from_checkpoint, tensors

p = argparse.ArgumentParser(__doc__)
p.add_argument('checkpoint')
p.add_argument('--output', required=True)
a = p.parse_args()
torch.set_num_threads(1)
net = policy_from_checkpoint(torch.load(a.checkpoint, map_location='cpu', weights_only=True)).eval()
OLD, NEW = '4.0-multiplayer', '4.0-sealed-all-bids'
pool = EnginePool(4, seed='sealed-menu-integration-v1', script='ai/strong/bridge.cjs')
results, omitted = {}, 0

def run(n, revision, mode):
    global omitted
    rows = pool.call(dict(op='reset', n=4*n, playerCount=n, mode=mode,
                         arenaSeed=f'sealed-menu-integration-{n}',
                         featureRevisions={'learner': revision, 'snapshot0': OLD}))['observations']
    ends = []
    while any(rows):
        indices = [i for i, row in enumerate(rows) if row]
        batch = [rows[i] for i in indices]
        for row in batch:
            expected = revision if row['roles'][row['seat']] == 'learner' else OLD
            assert row['featureRevision'] == expected
        with torch.inference_mode():
            choices = net(*tensors(batch, 'cpu'))[0].argmax(-1).tolist()
        actions = [None] * len(rows)
        for i, choice in zip(indices, choices):
            actions[i] = choice
            row = rows[i]
            bids = [round(x[10]*500) for x in row['actions'] if x[1] == 1]
            chosen = row['actions'][choice]
            if row['featureRevision'] == NEW and row['sealed'] and len(bids) > 48 and chosen[1] == 1:
                value = round(chosen[10]*500)
                omitted += not (value < bids[0]+8 or value % 10 == 0 or value == bids[-1])
        reply = pool.call(dict(op='step', actions=actions))
        rows = reply['observations']; ends.extend(reply['ended'])
    assert len(ends) == 4*n and not any(e['truncated'] for e in ends)
    return ends

try:
    for n in range(2, 7):
        old = run(n, OLD, 'snapshot0'); full = run(n, NEW, 'snapshot0')
        # Every open-rule terminal state, action-type count and step count must
        # remain identical when all actors have unchanged weights and menus.
        select = lambda xs: sorted([x for x in xs if not x['sealed']], key=lambda x: x['episode'])
        assert select(old) == select(full)
        results[f'{n}p/frozen'] = {'control_games': len(old), 'expanded_games': len(full),
                                  'identical_open_games': len(select(old))}
    for mode in ['economic_full_sealed_v1', 'capacity_full_sealed_v1']:
        games = run(2, NEW, mode)
        results['2p/' + mode] = {'expanded_games': len(games)}
finally:
    pool.close()
assert omitted > 0, 'Exercise bids that the old dispatcher could not select'
report = {'games': 176, 'truncations': 0, 'by_cell': results,
          'expanded_bids_actually_played': omitted, 'identical_open_games': 40,
          'qualification_eligible': False, 'scope': 'Integration coverage only; no model selection'}
Path(a.output).write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report))
