"""Verify all arms, unchanged roots and paired full-game discard-intervention results."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'ai'))
from infer import Model, Node
from arena_statistics import validate_pairs, win_summary
from huggingface_hub import hf_hub_download
def load(name, filename):
    s = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m
audit = load('discard_audit_collector', 'collect-public-discard-teacher.py')
paired = load('discard_intervention_pairs', 'compare-population-screens.py').paired_difference
read, write, digest = audit.read, audit.write, audit.digest


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('revision')
    p.add_argument('output', type=Path)
    a = p.parse_args()
    assert re.fullmatch('[a-f0-9]{40}', a.revision)
    protocol_path = ROOT / 'ai/strong/public-discard-intervention-protocol-v1.json'
    protocol = read(protocol_path)
    source = read(ROOT / 'ai/strong/public-discard-intervention-source-v1.json')
    out = a.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    pin = protocol['model']
    model = Model(hf_hub_download(protocol['repo'], pin['path'], revision=pin['revision']), threads=4)
    assert model.sha256 == pin['sha256']
    worker = Node('strong/worker.cjs')
    reports, roots_by_arm, status_by_arm = {}, {}, {}
    try:
        for arm in protocol['arms']:
            target = out / arm
            target.mkdir()
            prefix = 'runs/public-discard-intervention-v1-' + arm
            def fetch(name):
                assert Path(name).name == name
                raw = Path(hf_hub_download(protocol['repo'], prefix + '/' + name, revision=a.revision)).read_bytes()
                (target / name).write_bytes(raw)
            fetch('intervention-check.json')
            status = read(target / 'intervention-check.json')
            expected = {'status': 'complete', 'arm': arm, 'smoke': False, 'players': protocol['players'],
                'model_sha256': pin['sha256'], 'protocol_sha256': digest(protocol_path),
                'source_revision': source['revision'], 'source_sha256': source['sha256'],
                'games': protocol['games_per_arm'], 'game_caps': 0, 'search_caps': 0,
                'trained': False, 'qualification_eligible': False}
            for key, value in expected.items():
                assert status[key] == value, key
            assert set(status['artifact_sha256']) == {'roots.jsonl', 'games.json'}
            for name, sha in status['artifact_sha256'].items():
                fetch(name)
                assert digest(target / name) == sha
            report = read(target / 'games.json')
            rows = report['results']
            assert report['arm'] == arm
            assert len(rows) == protocol['games_per_arm']
            assert {r['episode'] for r in rows} == set(range(protocol['games_per_arm']))
            validate_pairs(rows, protocol['players'])
            assert {r['gameSeed'] for r in rows} == {protocol['arena_seed'] + '-' + str(i) for i in range(protocol['deals'])}
            assert all(not r['truncated'] and not r['searchStats'] for r in rows)
            assert report['summary'] == win_summary(rows)
            roots = [json.loads(s) for s in (target / 'roots.jsonl').read_text().splitlines()]
            index = {r['episode']: r for r in roots}
            assert len(index) == len(roots) == status['roots']
            games = {r['episode']: r for r in rows}
            for root in roots:
                game = games[root['episode']]
                assert root['rootIndex'] == root['episode']
                assert all(root[k] == game[k] for k in ['variant', 'sealed'])
                state, seat = root['request']['state'], root['request']['player']
                assert seat == game['seat'] and root['players'] == protocol['players']
                assert state['round'] == root['round']
                assert max(len(p['cities']) for p in state['players']) >= state['citiesToEndGame'] - 3
                assert not state['powerPlantsDeck'] and not state['hiddenLog'] and state['seed'] == 'secret'
                assert 'powerPlantDeckAfterStep3' not in state
                assert not state.get('automation', {}).get('plans')
                assert root['public_root_sha256'] == hashlib.sha256(json.dumps(root['request'], sort_keys=True).encode()).hexdigest()
                observation = worker.call({**root['request'], 'featureRevision': pin['feature_revision']})
                assert observation['moves'] == root['legal'] and len(root['legal']) > 1
                assert all(m['name'] == 'DiscardPowerPlant' for m in root['legal'])
                assert root['model_proposal'] == model.predict(observation['state'], observation['actions'])[0]
                assert root['model_move'] == root['legal'][root['model_proposal']]
                assert root['selected_move'] == root['legal'][root['selected']]
                if arm == 'parent':
                    assert 'guidance' not in root and root['selected'] == root['model_proposal']
                else:
                    assert root['selected'] == audit.chosen(root['guidance'])
            if arm != 'parent':
                audit_protocol = {**protocol, 'continuations': [arm], 'batches': [protocol['search_batch']]}
                evaluations, caps = audit.verify_rows([r['guidance'] for r in roots], roots, audit_protocol)
            else:
                evaluations, caps = 0, 0
            assert report['search_evaluations'] == status['search_evaluations'] == evaluations
            assert report['search_caps'] == status['search_caps'] == caps == 0
            assert report['interventions'] == status['interventions'] == sum(r['selected'] != r['model_proposal'] for r in roots)
            roots_by_arm[arm], reports[arm], status_by_arm[arm] = index, report, status
        parent = roots_by_arm['parent']
        for arm, roots in roots_by_arm.items():
            assert roots.keys() == parent.keys(), 'Intervention changed root selection'
            for i, root in roots.items():
                for key in ['request', 'legal', 'model_proposal', 'model_move', 'round', 'public_root_sha256']:
                    assert root[key] == parent[i][key], 'Pre-intervention root changed: ' + key
    finally:
        worker.close()
    summary = {'revision': a.revision, 'protocol_sha256': digest(protocol_path),
        'arms': {arm: {**r['summary'], 'roots': len(roots_by_arm[arm]), 'interventions': r['interventions'],
                      'search_evaluations': r['search_evaluations'], 'search_caps': 0} for arm, r in reports.items()},
        'all_pre_intervention_public_roots_and_proposals_identical': True, 'contrasts': {},
        'trained': False, 'qualification_eligible': False,
        'interpretation': 'Fresh 2p economic-opponent development games, complete paired seats/rules. Marginal whole-deal bootstrap intervals. No claim for other counts, independent opponents, learned model improvement or full qualification.'}
    for contrast in protocol['analysis']['contrasts']:
        left, right = contrast.split('-minus-')
        def compare(x, y):
            return paired(x, y, repeats=protocol['analysis']['bootstrap_replicates'], seed=protocol['analysis']['bootstrap_seed'])
        result = {'overall': compare(reports[left]['results'], reports[right]['results']), 'rules': {}}
        for variant in ['original', 'recharged']:
            for sealed in [False, True]:
                select = lambda rows: [r for r in rows if r['variant'] == variant and r['sealed'] == sealed]
                result['rules'][variant + ('/sealed' if sealed else '/open')] = compare(select(reports[left]['results']), select(reports[right]['results']))
        summary['contrasts'][contrast] = result
    write(out / 'comparison.json', summary)
    write(out / 'verified.json', {'revision': a.revision, 'verified': True, 'games': sum(r['games'] for r in status_by_arm.values()),
        'model_proposals_reproduced': sum(len(r) for r in roots_by_arm.values()),
        'game_caps': 0, 'search_caps': 0, 'qualification_eligible': False,
        'sha256': {str(p.relative_to(out)): digest(p) for p in out.rglob('*') if p.is_file()}})
    print({'arms': summary['arms'], 'overall_contrasts': {k: v['overall'] for k, v in summary['contrasts'].items()}})


if __name__ == '__main__':
    main()
