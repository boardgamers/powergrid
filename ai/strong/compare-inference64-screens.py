"""Compare the complete repaired cohort without mixing FP32 outcomes or training seeds."""
import argparse
from pathlib import Path
from inference64_screen import config, read, write, digest, collect, check_validation, PROTOCOL
from five_plant_screen import load_module

p = argparse.ArgumentParser(__doc__)
p.add_argument('cohort', choices=['five-plant', 'population'])
p.add_argument('directory', type=Path)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
protocol, cfg, _ = config(a.cohort, 'parent')
paired = load_module('precision_paired_comparison', 'compare-population-screens.py').paired_difference
reports, summaries = {}, {}
for key in cfg['models']:
    out = a.directory / key
    status, verified = read(out / 'screen-check.json'), read(out / 'verified.json')
    assert verified['verified'] and verified['cohort'] == a.cohort and verified['key'] == key
    assert verified['screen_report_sha256'] == digest(out / 'screen-check.json')
    assert status['status'] == 'complete' and status['protocol_sha256'] == digest(PROTOCOL)
    assert status['games'] == cfg['evaluation']['games_per_candidate'] and status['truncations'] == 0
    for name, sha in status['artifact_sha256'].items():
        assert not Path(name).is_absolute() and '..' not in Path(name).parts
        assert digest(out / name) == sha
    manifest = read(out / 'evaluated-model.json')
    assert manifest['cohort'] == a.cohort and manifest['key'] == key
    assert manifest['derivative'] == cfg['models'][key]['derivative']
    check_validation(out, manifest, protocol)
    assert collect(out, cfg, manifest) == read(out / 'summary.json')
    summaries[key] = read(out / 'summary.json')
    reports[key] = {f'{s["opponent"]}/{s["players"]}p': read(out / f'{s["opponent"]}-{s["players"]}p.json')['results']
                    for s in cfg['evaluation']['screens']}
ev = cfg['evaluation']
result = {'cohort': a.cohort, 'protocol_sha256': digest(PROTOCOL), 'summaries': summaries,
    'contrasts': {}, 'qualification_eligible': False,
    'interpretation': 'Prescribed final checkpoints and original development deals, uniformly using explicit FP64 candidate derivatives. Every count/rule cell retained. Whole-deal marginal exploratory intervals, not multiplicity-adjusted. Two feature-training seeds reported separately without treating repeated deals as independent. Population comparison has one training seed. Original FP32 failures and results are not relabelled. Full strength gate and reserved final seeds remain required.'}
for left, right in cfg['contrasts']:
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
print({'cohort': a.cohort, 'games': ev['games_per_candidate'] * len(cfg['models']), 'contrasts': len(result['contrasts'])})
