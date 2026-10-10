"""Compare all prescribed population arms, retaining paired deals and rule strata."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('population_collector', Path(__file__).with_name('collect-population-screen.py'))
collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collector)


def paired_difference(left, right, repeats=20000, seed=10021):
    def index(rows):
        result = {}
        for r in rows:
            key = (r['gameSeed'], r['variant'], r['sealed'], r['seat'])
            if key in result or r['truncated']:
                raise ValueError('Duplicate or truncated paired outcome')
            result[key] = float(r['win'])
        return result
    a, b = index(left), index(right)
    if not a or a.keys() != b.keys():
        raise ValueError('Pair sets do not match')
    groups = {}
    for key in sorted(a):
        groups.setdefault(key[0], []).append(a[key] - b[key])
    if len({len(v) for v in groups.values()}) != 1:
        raise ValueError('Unequal seat/rule coverage between deals')
    # A whole deal (all seat/rule repeats) is the resampling unit.
    deltas = np.array([np.mean(v) for v in groups.values()])
    rng = np.random.default_rng(seed)
    samples = deltas[rng.integers(len(deltas), size=(repeats, len(deltas)))].mean(1)
    return {'games_per_model': len(left), 'independent_deals': len(deltas),
        'win_share_difference': float(deltas.mean()),
        'paired_deal_bootstrap_95_interval': np.quantile(samples, [.025, .975]).tolist()}


def compare(directories, update, output):
    protocol = json.loads((ROOT / 'ai/strong/population-training-protocol-v1.json').read_text())
    if update not in protocol['checkpoint_updates']:
        raise ValueError('Unexpected scheduled update')
    reports, pins = {}, {}
    for arm, directory in directories.items():
        summary = json.loads((directory / 'summary.json').read_text())
        pin = summary['checkpoint']
        if pin['arm'] != arm or pin['update'] != (79 if arm == 'parent' else update):
            raise ValueError('Wrong checkpoint arm or update')
        if pin['strict_parity'] != 'passed':
            raise ValueError('Export parity has not passed')
        pins[arm] = pin
        reports[arm] = {}
        for screen in protocol['evaluation']['screens']:
            n, opponent = screen['players'], screen['opponent']
            cell = f'{opponent}/{n}p'
            data = (directory / f'{opponent}-{n}p.json').read_bytes()
            if hashlib.sha256(data).hexdigest() != summary['cells'][cell]['artifact_sha256']:
                raise ValueError('Screen artifact changed after collection')
            report = json.loads(data)
            collector.verify_report(report, screen, pin, protocol['evaluation'])
            reports[arm][cell] = report['results']
    comparisons = [('heterogeneous', 'homogeneous'), ('heterogeneous', 'control'),
        ('homogeneous', 'control'), ('heterogeneous', 'parent'), ('homogeneous', 'parent'), ('control', 'parent')]
    result = {'update': update, 'checkpoints': pins, 'comparisons': {},
        'primary': update == protocol['primary_checkpoint_update'],
        'qualification_eligible': False,
        'interpretation': 'All comparisons are exploratory marginal intervals from one training seed. Report regressions and every rule/count cell; this is not final qualification.'}
    for left, right in comparisons:
        cells = {}
        for cell, a in reports[left].items():
            b = reports[right][cell]
            cells[cell] = {'overall': paired_difference(a, b), 'by_rules': {}}
            for variant in ['original', 'recharged']:
                for sealed in [False, True]:
                    select = lambda rows: [r for r in rows if r['variant'] == variant and r['sealed'] == sealed]
                    cells[cell]['by_rules'][f'{variant}/{"sealed" if sealed else "open"}'] = paired_difference(select(a), select(b))
        result['comparisons'][f'{left}-minus-{right}'] = cells
    output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'update': update, 'comparisons': len(comparisons), 'output': str(output)}))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for arm in ['parent', 'control', 'homogeneous', 'heterogeneous']:
        p.add_argument('--' + arm, type=Path, required=True)
    p.add_argument('--update', type=int, choices=[9, 19], required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    compare({arm: getattr(args, arm).resolve() for arm in ['parent', 'control', 'homogeneous', 'heterogeneous']}, args.update, args.output)
