"""Compare both predeclared training seeds without counting repeated deals twice."""
import argparse
from pathlib import Path
from five_plant_screen import ROOT, read, write, digest, collect, load_module

p = argparse.ArgumentParser(__doc__)
p.add_argument('directory', type=Path, help='Contains parent and the four protocol-named subdirectories')
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
protocol = read(ROOT / 'ai/strong/five-plant-ablation-protocol-v1.json')
ev = protocol['evaluation']
paired = load_module('paired_comparison', 'compare-population-screens.py').paired_difference
summaries, reports = {}, {}
for key in ['parent', *protocol['runs']]:
    directory = a.directory / key
    verified = read(directory / 'verified.json')
    assert verified['key'] == key and verified['verified'] and verified['games'] == 4000
    assert verified['screen_report_sha256'] == digest(directory / 'screen-check.json')
    status = read(directory / 'screen-check.json')
    assert status['status'] == 'complete' and status['key'] == key
    for name, sha in status['artifact_sha256'].items():
        assert Path(name).name == name and digest(directory / name) == sha
    summary = read(directory / 'summary.json')
    assert summary['checkpoint']['key'] == key
    assert collect(directory, protocol, summary['checkpoint']) == summary
    summaries[key] = summary
    reports[key] = {f'{s["opponent"]}/{s["players"]}p': read(
        directory / f'{s["opponent"]}-{s["players"]}p.json')['results'] for s in ev['screens']}

contrasts = [(f'full-s{seed}', f'control-s{seed}') for seed in protocol['training']['seeds']]
contrasts += [(key, 'parent') for key in protocol['runs']]
result = {'qualification_eligible': False, 'summaries': summaries, 'contrasts': {},
          'interpretation': 'Primary full-minus-control contrasts are reported separately for each training seed and every opponent/count/rule cell. The same 40 deals appear in both seeds; no pooled 80-deal interval. All intervals are marginal exploratory intervals, not multiplicity-adjusted. Two seeds do not characterize all training variance. Final strength gate is unchanged.'}
for left, right in contrasts:
    cells = {}
    for cell, rows in reports[left].items():
        other = reports[right][cell]
        def compare(x, y):
            return paired(x, y, repeats=ev['bootstrap_replicates'], seed=ev['bootstrap_seed'])
        cells[cell] = {'overall': compare(rows, other), 'by_rules': {}}
        for variant in ['original', 'recharged']:
            for sealed in [False, True]:
                select = lambda rs: [r for r in rs if r['variant'] == variant and r['sealed'] == sealed]
                cells[cell]['by_rules'][variant + ('/sealed' if sealed else '/open')] = compare(select(rows), select(other))
    result['contrasts'][left + '-minus-' + right] = cells
write(a.output, result)
print({'comparisons': len(contrasts), 'games': 20000, 'output': str(a.output)})
