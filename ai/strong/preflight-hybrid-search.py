"""Local ONNX/engine integration checks, not model training or strength evidence."""
import argparse
import copy
import json
from pathlib import Path
from unittest.mock import patch

from strategic_collection import ROOT, read, write, digest, get_model
from hybrid_search import HybridSearch, predict_batch, public_seed, Model, Node, model_revision


def comparable(result):
    return {k: v for k, v in result.items() if k != 'elapsedMs'}


def rejected(fn):
    try:
        fn()
    except ValueError:
        return
    raise AssertionError('Invalid input accepted')


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    architecture_dir = ROOT / 'ai/runs/policy-iteration-8840u-prepared-v2'
    manifest = read(architecture_dir / 'manifest.json')
    assert manifest['synthetic_untrained'] and not manifest['qualification_eligible']
    fixtures = architecture_dir / 'fixtures.jsonl'
    assert digest(fixtures) == manifest['fixtures_sha256']
    requests = [json.loads(line)['request'] for line in fixtures.open()]
    assert len(requests) == 2553
    cells = {}
    for q in requests:
        s = q['state']
        key = len(s['players']), s['options']['variant'], bool(s['options']['fastBid']), s['phase']
        cells.setdefault(key, q)
    assert len(cells) == 80
    models = {'parent': get_model(read(ROOT / 'ai/strong/policy-iteration-labels-protocol-v2.json'))}
    for key, pin in manifest['models'].items():
        path = architecture_dir / ('local-package-' + key) / 'policy.onnx'
        assert digest(path) == pin['pin']['files']['inference64.onnx']
        models[key] = Model(path)
    report = {'passed': False, 'fixtures_sha256': digest(fixtures), 'batch_checks': {}, 'search_checks': {},
              'gradients': False, 'remote_jobs_started': 0, 'new_trained_models': False,
              'reserved_final_seeds_used': False, 'qualification_eligible': False,
              'scope': 'One existing unqualified parent plus four untrained architecture exports. '
                       'Local ONNX integration and search correctness only; not playing strength or AMD8840U timing.'}
    node = Node('strong/hybrid-continuations.cjs')
    try:
        for key, model in models.items():
            revision = model_revision(model)
            prepared = [node.call({**q, 'op': 'prepare', 'featureRevision': revision}) for q in cells.values()]
            rows = [p['observation'] for p in prepared] + [r['encoded'] for p in prepared for r in p['prior']]
            serial = [model.predict(r['state'], r['actions'])[0] for r in rows]
            assert serial == predict_batch(model, rows) == predict_batch(model, rows, 1)
            bad = copy.deepcopy(rows[0]); bad['featureRevision'] = 'unsupported'
            rejected(lambda: predict_batch(model, [bad]))
            bad = copy.deepcopy(rows[0]); bad['actions'] = []
            rejected(lambda: predict_batch(model, [bad]))
            bad = copy.deepcopy(rows[0]); bad['state'][0] = float('nan')
            rejected(lambda: predict_batch(model, [bad]))
            report['batch_checks'][key] = {'model_sha256': model.sha256, 'revision': revision,
                'positions': len(rows), 'serial_fixed64_and_single_row_identical': True,
                'counts': [2, 3, 4, 5, 6], 'rule_phase_cells': 80, 'invalid_inputs_rejected': 3,
                'synthetic_untrained': key != 'parent'}
            print({'batch_checked': key, 'positions': len(rows)}, flush=True)

        selected = {}
        for q in requests:
            s = q['state']; n = len(s['players'])
            if (n not in [2, 6] or n in selected or s['options']['variant'] != 'recharged'
                    or not s['options']['fastBid'] or s['phase'] != 'Auction' or not s.get('chosenPowerPlant')):
                continue
            p = node.call({**q, 'op': 'prepare', 'featureRevision': '4.3-strategic-correction'})
            if p['prior'] and len(p['moves']) > 1:
                selected[n] = q
        assert set(selected) == {2, 6}
        for n, q in selected.items():
            a = node.call({**q, 'op': 'prepare', 'featureRevision': '4.2-discard-correction'})
            b = node.call({**q, 'op': 'prepare', 'featureRevision': '4.3-strategic-correction'})
            assert public_seed(a) == public_seed(b)
            for key in ['parent', 'public-0']:
                with HybridSearch(models[key], samples=1, workers=2) as search:
                    result = search.choose(q)
                case = key + '-' + str(n) + 'p'
                report['search_checks'][case] = result
                if key == 'parent':
                    assert result['search']['usable'] and result['search']['truncated'] == 0
                elif result['search']['truncated']:
                    # Untrained self-play can fail to end. It must remain unusable,
                    # with explicit caps and no selected action based on partial means.
                    assert not result['search']['usable'] and 'meanCredits' not in result['search']
                    assert result['index'] == result['modelProposal']
                    assert result['search']['fallbackReason'] == 'incomplete-rollouts'
                assert result['move'] == b['moves'][result['index']]
                assert result['modelProposal'] in result['search']['options']
                assert set(result['search']['sampleOutcomes']) == {'neural', 'neural_economic'}
                if key == 'parent':
                    with patch('hybrid_search.WORKER', 'strong/sealed-belief-continuations.cjs'):
                        with HybridSearch(models[key], samples=1, workers=2) as control:
                            original = control.choose(q)
                    assert comparable(result) == comparable(original), 'Adapter changed actual neural continuations'
                print({'search_checked': case, 'rollouts': result['search']['evaluations'],
                       'truncated': result['search']['truncated'], 'seconds': result['elapsedMs'] / 1000}, flush=True)
            with HybridSearch(models['public-0'], samples=1, workers=2, modes=('neural_economic',)) as search:
                result = search.choose(q)
            case = 'public-0-economic-' + str(n) + 'p'
            report['search_checks'][case] = result
            assert result['search']['usable'] and result['search']['truncated'] == 0
            print({'search_checked': case, 'rollouts': result['search']['evaluations'],
                   'truncated': result['search']['truncated']}, flush=True)

        q = selected[2]; hidden = copy.deepcopy(q)
        hidden.update(requestId='forbidden-id', revision=987654)
        s = hidden['state']; s['seed'] = 'forbidden-seed'; s['currentBid'] = 888
        s['powerPlantsDeck'] = [{'number': 999}]; s['powerPlantDeckAfterStep3'] = [{'number': 888}]
        s['hiddenLog'] = [{'secret': True}]; s['automation'] = {'plans': {'0': {'secret': True}}}
        for p in s['players']:
            p['bid'] = 777; p['lastMove'] = {'name': 'Bid', 'data': 777}
        with HybridSearch(models['public-0'], samples=1, workers=2) as search:
            altered = search.choose(hidden)
        assert comparable(altered) == comparable(report['search_checks']['public-0-2p'])
        report['hidden_fields_seed_and_full_search_identical'] = True
        with HybridSearch(models['public-0'], samples=1, workers=2, max_steps=1) as search:
            capped = search.choose(selected[6])
        assert not capped['search']['usable'] and capped['search']['truncated'] > 0
        assert capped['index'] == capped['modelProposal'] and 'meanCredits' not in capped['search']
        assert capped['search']['fallbackReason'] == 'incomplete-rollouts'
        report['cap_control'] = capped
        for phase, scope in [('Resources', 'combined'), ('Building', 'auction'), ('Auction', 'building')]:
            q = next(q for q in cells.values() if q['state']['phase'] == phase)
            with HybridSearch(models['public-0'], samples=1, workers=2, scope=scope) as search:
                skipped = search.choose(q)
                assert search.pool is None and skipped['search'] is None
                assert skipped['index'] == skipped['modelProposal']
        report['phase_gating_controls'] = 3
        for kwargs in [{'samples': 0}, {'samples': True}, {'workers': 0}, {'max_steps': 2401},
                       {'scope': 'unknown'}, {'modes': ()}, {'modes': ('neural', 'neural')}]:
            rejected(lambda: HybridSearch(models['public-0'], **kwargs))
        report['budget_rejection_controls'] = 7
        report['passed'] = True
    finally:
        node.close()
        report['code'] = {name: digest(ROOT / 'ai/strong' / name) for name in
                          ['hybrid_search.py', 'hybrid-continuations.cjs', 'preflight-hybrid-search.py']}
        write(args.output / 'check.json', report)
    print({'passed': report['passed'], 'model_batch_checks': len(report['batch_checks']),
           'search_checks': len(report['search_checks']),
           'usable_search_checks': sum(r['search']['usable'] for r in report['search_checks'].values())}, flush=True)


if __name__ == '__main__':
    main()
