"""Exactly replay preselected development wins/losses with public move ledgers."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from infer import Model
from pool import EnginePool

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('selection', type=Path)
parser.add_argument('model', type=Path)
parser.add_argument('output', type=Path)
args = parser.parse_args()
selection = json.loads(args.selection.read_text())
model = Model(args.model)
assert model.sha256 == selection['model_sha256']
args.output.mkdir(parents=True, exist_ok=True)
os.environ['NODE_OPTIONS'] = '--require ' + str(Path(__file__).with_name('trace-public-game.cjs').resolve())
if os.environ.get('PG_EXTRA_PRELOAD'):
    os.environ['NODE_OPTIONS'] += ' --require ' + os.environ['PG_EXTRA_PRELOAD']
reports = []
for expected in selection['matches']:
    name = f'episode-{expected["episode"]}'
    trace = args.output / (name + '.jsonl')
    trace.write_text('')
    os.environ['PG_TRACE_PATH'] = str(trace.resolve())
    pool = EnginePool(1, seed=selection['seed'], script='ai/strong/bridge.cjs')
    start = time.monotonic()
    ended = []
    try:
        current = pool.call(dict(op='reset', n=1, playerCount=2, offset=expected['episode'],
            mode='economic', arenaSeed=selection['seed'],
            featureRevisions={'learner': '4.0-multiplayer'}))['observations']
        while current[0] is not None:
            row = current[0]
            action, _ = model.predict(row['state'], row['actions'])
            reply = pool.call(dict(op='step', actions=[action]))
            current = reply['observations']
            ended.extend(reply['ended'])
    finally:
        pool.close()
    assert len(ended) == 1
    keys = ['episode', 'gameSeed', 'truncated', 'value', 'playerCount', 'variant',
        'sealed', 'steps', 'roles', 'policyMoves', 'searchStats', 'final']
    differences = [k for k in keys if ended[0][k] != expected[k]]
    result = {'episode': expected['episode'], 'gameSeed': expected['gameSeed'],
        'seat': expected['seat'], 'variant': expected['variant'], 'sealed': expected['sealed'],
        'expected_win': expected['win'], 'exact_terminal_replay': not differences,
        'differences': differences, 'actual': ended[0],
        'trace_sha256': hashlib.sha256(trace.read_bytes()).hexdigest(),
        'moves_logged': len(trace.read_text().splitlines()), 'seconds': time.monotonic() - start}
    (args.output / (name + '.json')).write_text(json.dumps(result, indent=2) + '\n')
    reports.append(result)
    (args.output / 'replays.json').write_text(json.dumps(reports, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'actual'}), flush=True)
    if differences:
        raise ValueError('Replay diverged from frozen arena; investigate before analysis')
