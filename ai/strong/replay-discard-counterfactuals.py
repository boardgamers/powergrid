"""Single-decision causal diagnostics on fixed actual deals; never training labels."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'ai'))
from infer import Model
from pool import EnginePool


def read(path):
    return json.loads(Path(path).read_text())


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('selection', type=Path)
    parser.add_argument('protocol', type=Path)
    parser.add_argument('model', type=Path)
    parser.add_argument('reference', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    selection, protocol = read(args.selection), read(args.protocol)
    assert protocol['selection_sha256'] == digest(args.selection)
    model = Model(args.model)
    assert model.sha256 == selection['model_sha256']
    matches = {r['episode']: r for r in selection['matches']}
    args.output.mkdir(parents=True, exist_ok=True)
    os.environ['NODE_OPTIONS'] = ' '.join('--require ' + str(ROOT / 'ai/strong' / f)
        for f in ['trace-public-game.cjs', 'intervene-discard.cjs'])
    rows = []
    for case in protocol['cases']:
        expected = matches[case['episode']]
        reference_file = args.reference / f'episode-{case["episode"]}.jsonl'
        reference = [json.loads(line) for line in reference_file.read_text().splitlines()]
        roots = [i for i, r in enumerate(reference) if r['seat'] == case['seat']
                 and r['before']['round'] == case['round'] and r['action']['name'] == 'DiscardPowerPlant']
        assert len(roots) == 1
        root_index = roots[0]
        assert reference[root_index]['action']['data'] == case['original_discard']
        for discard in case['alternatives']:
            trace = args.output / f'episode-{case["episode"]}-discard-{discard}.jsonl'
            trace.write_text('')
            os.environ['PG_TRACE_PATH'] = str(trace.resolve())
            os.environ['PG_DISCARD_BRANCH'] = json.dumps({**case, 'discard': discard})
            pool = EnginePool(1, seed=selection['seed'], script='ai/strong/bridge.cjs')
            ended = []
            try:
                observations = pool.call(dict(op='reset', n=1, playerCount=2, offset=case['episode'],
                    mode='economic', arenaSeed=selection['seed'],
                    featureRevisions={'learner': '4.0-multiplayer'}))['observations']
                while observations[0] is not None:
                    row = observations[0]
                    action, _ = model.predict(row['state'], row['actions'])
                    reply = pool.call(dict(op='step', actions=[action]))
                    observations = reply['observations']; ended.extend(reply['ended'])
            finally:
                pool.close()
            assert len(ended) == 1 and not ended[0]['truncated']
            intervention = read(str(trace) + '.intervention.json')
            assert intervention['applied'] == 1
            assert sorted(a['data'] for a in intervention['legal'] if a['name'] == 'DiscardPowerPlant') == case['alternatives']
            actual = [json.loads(line) for line in trace.read_text().splitlines()]
            assert actual[:root_index] == reference[:root_index], 'Changed a decision before the selected root'
            assert actual[root_index]['before'] == reference[root_index]['before']
            assert actual[root_index]['action'] == {'name': 'DiscardPowerPlant', 'data': discard}
            original = discard == case['original_discard']
            if original:
                assert digest(trace) == digest(reference_file), 'Original branch must reproduce the entire trace'
                for key in ['episode', 'gameSeed', 'truncated', 'value', 'playerCount', 'variant',
                            'sealed', 'steps', 'roles', 'policyMoves', 'searchStats', 'final']:
                    assert ended[0][key] == expected[key], key
            rows.append({'episode': case['episode'], 'discard': discard, 'original': original,
                'round': case['round'], 'seat': case['seat'], 'original_win': expected['win'],
                'win': ended[0]['value'][case['seat']], 'identical_prefix_moves': root_index,
                'trace_sha256': digest(trace), 'intervention_sha256': digest(str(trace) + '.intervention.json'),
                'result': ended[0]})
        print(json.dumps({'episode': case['episode'], 'original_win': expected['win'],
                          'branches': {r['discard']: r['win'] for r in rows if r['episode'] == case['episode']}}), flush=True)
        (args.output / 'branches.json').write_text(json.dumps(rows, indent=2) + '\n')
    assert len(rows) == protocol['branch_games']
    report = {'games': len(rows), 'selected_trajectories': len(protocol['cases']),
        'original_traces_identical': sum(r['original'] for r in rows),
        'all_prefixes_identical': True, 'truncations': 0,
        'protocol_sha256': digest(args.protocol), 'selection_sha256': digest(args.selection),
        'model_sha256': model.sha256, 'branches_sha256': digest(args.output / 'branches.json'),
        'scope': protocol['purpose'], 'qualification_eligible': False, 'trained': False}
    (args.output / 'check.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
