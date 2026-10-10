"""Pair all count/reference/rule cells and require exact unchanged open games."""
import argparse
from pathlib import Path
from five_plant_screen import ROOT, read, write, digest, collect, load_module
from sealed_menu_screen import validate_checks

p = argparse.ArgumentParser(__doc__)
p.add_argument('control', type=Path)
p.add_argument('expanded', type=Path)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
protocol = read(ROOT / 'ai/strong/sealed-menu-protocol-v1.json')
ev = protocol['evaluation']
paired = load_module('menu_paired_stats', 'compare-population-screens.py').paired_difference
summaries, rows = {}, {}
for key in ['control', 'expanded']:
    directory = getattr(a, key)
    status = read(directory / 'screen-check.json')
    assert status['key'] == key and status['status'] == 'complete' and status['games'] == 7520
    assert status['protocol_sha256'] == digest(ROOT / 'ai/strong/sealed-menu-protocol-v1.json')
    assert status['fixture_sha256'] == protocol['fixture_sha256'] and status['trained'] is False
    for name, sha in status['artifact_sha256'].items():
        assert Path(name).name == name and digest(directory / name) == sha
    manifest = read(directory / 'checkpoint.json')
    pin = protocol['conditions'][key]
    assert manifest['key'] == key and manifest['revision'] == pin['revision']
    assert manifest['hashes'] == {'latest.pt': pin['checkpoint_sha256'], 'latest.onnx': pin['model_sha256']}
    validate_checks(directory, manifest)
    summaries[key] = read(directory / 'summary.json')
    assert collect(directory, protocol, manifest) == summaries[key]
    rows[key] = {f'{s["opponent"]}/{s["players"]}p': read(directory / f'{s["opponent"]}-{s["players"]}p.json')['results'] for s in ev['screens']}
result = {'summaries': summaries, 'contrasts': {}, 'open_identity': {}, 'qualification_eligible': False,
          'interpretation': 'Same frozen weights and CPU host. Marginal exploratory whole-deal intervals; not multiplicity-adjusted. All count/rule/reference cells retained. Expanded-reference superiority is not assumed and this experiment cannot qualify a model.'}
for cell, full in rows['expanded'].items():
    control = rows['control'][cell]
    select = lambda rs, variant, sealed: [r for r in rs if r['variant'] == variant and r['sealed'] == sealed]
    comparison = lambda x, y: paired(x, y, repeats=ev['bootstrap_replicates'], seed=ev['bootstrap_seed'])
    result['contrasts'][cell] = {'overall': comparison(full, control), 'by_rules': {
        variant + ('/sealed' if sealed else '/open'): comparison(select(full, variant, sealed), select(control, variant, sealed))
        for variant in ['original', 'recharged'] for sealed in [False, True]}}
    def open_index(rs):
        return {(r['gameSeed'], r['variant'], r['seat']): r for r in rs if not r['sealed']}
    left, right = open_index(full), open_index(control)
    assert left.keys() == right.keys()
    mismatches = [list(k) for k in sorted(left) if left[k] != right[k]]
    result['open_identity'][cell] = {'games': len(left), 'exact_match': not mismatches, 'mismatches': mismatches}
result['all_open_games_identical'] = all(v['exact_match'] for v in result['open_identity'].values())
write(a.output, result)
assert result['all_open_games_identical'], 'Isolation check failed; inspect the saved mismatches before interpreting effects'
print({'games': 15040, 'cells': 13, 'exact_open_games': sum(v['games'] for v in result['open_identity'].values())})
