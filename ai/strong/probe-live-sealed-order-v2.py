"""Actual-model integration for an isolated asynchronous sealed-auction adapter."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import time

from hybrid_search import Model
from population_hybrid_policy import PopulationPolicy
from population_policy_verification import verify_decision

ROOT = Path(__file__).resolve().parents[2]


def read(path):
    return json.loads(Path(path).read_text())


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')


def semantic(row):
    return {k: v for k, v in row.items() if k != 'elapsedMs'}


def run(output):
    base = ROOT/'ai/runs/live-sealed-order-repair-v2'
    runtime = base/'runtime'
    provenance = read(base/'source-verification.json')
    for name, sha in provenance['files'].items():
        expected = provenance['replacement_sha256'] if name == provenance['isolated_overlay'] else sha
        assert digest(runtime/name) == expected, name
    contract = read(base/'checks/assessment.json')
    assert contract['passed'] and contract['audit_regressions'] == 446
    assert digest(base/'checks/requests.jsonl') == contract['requests_sha256']
    model_path = ROOT/'ai/runs/policy-iteration-trained-8840u-prepared-v2/local-package-frozen-1/policy.onnx'
    model = Model(model_path, threads=1)
    pin = read(ROOT/'ai/strong/population-hybrid-development-protocol-v1.json')['model_pin']
    assert model.sha256 == pin['files']['inference64.onnx']
    output.mkdir(parents=True, exist_ok=False)
    report = {'source_verification_sha256':digest(base/'source-verification.json'),
        'checker_sha256':digest(__file__), 'request_sha256':contract['requests_sha256'],
        'model_sha256':model.sha256, 'model_positions':0, 'filter_positions':0,
        'search_cases':0, 'rollouts':0, 'caps':0, 'canonical_search_pairs':0,
        'secret_search_pairs':0, 'partition_pairs':0, 'passed':False,
        'qualification_eligible':False, 'reserved_final_seeds_used':False,
        'new_strength_games':0, 'new_hf_jobs':0, 'gradients':False}
    worker = runtime/'ai/strong/population-hybrid-policy.cjs'
    policies = {}
    start = time.perf_counter()
    try:
        policies = {arm:PopulationPolicy(model, worker, arm=arm, samples=8, workers=1)
                    for arm in ['model','filter','combined']}
        selected = {}
        with (base/'checks/requests.jsonl').open() as stream, (output/'model-filter.jsonl').open('x') as results:
            for line in stream:
                entry = json.loads(line)
                q = entry['request']
                choices = {}
                for arm in ['model','filter']:
                    result = policies[arm].choose(q)
                    assert entry['legal'][result['index']] == result['move']
                    verify_decision(result, {'players':len(q['state']['players']), 'arm':arm,
                        'samples':8, 'model_sha256':model.sha256}, q['player'])
                    assert result['search'] is None and not result['filterApplied']
                    choices[arm] = result
                    report[arm+'_positions'] += 1
                assert choices['model']['move'] == choices['filter']['move']
                results.write(json.dumps({'label':entry['label'], 'results':choices}, allow_nan=False)+'\n')
                if entry['family'] != 'subset':
                    continue
                n, variant = len(q['state']['players']), q['state']['options']['variant']
                plan = entry['plan']
                committed = plan['submitted']
                if (len(committed) >= min(2,n-1)
                        and committed != plan['eligible'][:len(committed)]):
                    selected.setdefault(f'{n}p-{variant}-committed',entry)
                if n in [2,6] and variant == 'recharged' and not committed and not plan['canonical']:
                    selected.setdefault(f'{n}p-{variant}-pending',entry)
        assert report['model_positions'] == report['filter_positions'] == 1086
        assert len(selected) == 12
        write(output/'selected-requests.json',selected)
        print({'model_filter_requests':2172,'selected_search_requests':len(selected)},flush=True)

        def search(policy, entry, label, stream):
            raw = policy.choose(entry['request'])
            result = json.loads(json.dumps(raw, allow_nan=False))
            assert result['move'] == entry['legal'][result['index']]
            q = entry['request']
            verify_decision(result, {'players':len(q['state']['players']), 'arm':'combined',
                'samples':8, 'model_sha256':model.sha256}, q['player'])
            detail = result['search']
            assert detail and detail['usable'] and detail['truncated'] == 0
            if 'plan' in entry:
                for world in detail['worlds'].values():
                    assert [bid['actor'] for bid in world['initialBelief']['committed']] == entry['plan']['submitted']
            report['search_cases'] += 1
            report['rollouts'] += detail['evaluations']
            report['caps'] += detail['truncated']
            stream.write(json.dumps({'label':label,'result':result},allow_nan=False)+'\n');stream.flush()
            print({'search_case':label,'rollouts':detail['evaluations'],'seconds':result['elapsedMs']/1000},flush=True)
            return result

        with (output/'search.jsonl').open('x') as stream:
            baseline = {name:search(policies['combined'],entry,name,stream) for name,entry in selected.items()}
            old_worker = ROOT/'ai/runs/population-hybrid-development-source-prepared-v1/layout/ai/strong/population-hybrid-policy.cjs'
            policies['old'] = PopulationPolicy(model,old_worker,arm='combined',samples=8,workers=1)
            controls = read(ROOT/'ai/runs/trained-hybrid-probe-v2/selected-fixtures.json')
            for name in ['2p-bid','6p-bid']:
                entry = controls[name]['fixture']
                a = search(policies['old'],entry,'old-'+name,stream)
                b = search(policies['combined'],entry,'new-'+name,stream)
                assert semantic(a) == semantic(b)
                report['canonical_search_pairs'] += 1
            name = '6p-recharged-committed'
            hidden = deepcopy(selected[name])
            state = hidden['request']['state']
            state['seed'] = 'private-probe-seed'
            state['powerPlantsDeck'] = [{'number':9999}]
            state['hiddenLog'] = [{'private':'must never affect decisions'}]
            state['currentBid'] = 9998
            for player in state['players']:
                player['bid'] = 9997
                player['lastMove'] = {'name':'Bid','data':9996}
            result = search(policies['combined'],hidden,'hidden-'+name,stream)
            assert semantic(result) == semantic(baseline[name])
            report['secret_search_pairs'] += 1
            policies['partition'] = PopulationPolicy(model,worker,arm='combined',samples=8,workers=4)
            result = search(policies['partition'],selected[name],'partition-'+name,stream)
            assert semantic(result) == semantic(baseline[name])
            report['partition_pairs'] += 1
        assert report['search_cases'] == 18 and report['caps'] == 0
        report['passed'] = True
    except BaseException as error:
        report['error'] = type(error).__name__+': '+str(error)
        raise
    finally:
        for policy in policies.values():
            policy.close()
        report['seconds'] = time.perf_counter()-start
        report['scope'] = 'Existing-fixture engineering checks with the actual frozen-1 model. Noncanonical request strength, unknown prior-submission-order calibration, target CPU latency and platform integration remain unqualified.'
        report['files'] = {p.name:digest(p) for p in output.iterdir() if p.is_file()}
        write(output/'assessment.json',report)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--output',type=Path,required=True)
    run(parser.parse_args().output.resolve())
