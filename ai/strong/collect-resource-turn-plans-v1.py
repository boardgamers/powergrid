"""Verify saved public proposal receipts and archive this unintegrated prototype."""
import itertools
import json
from pathlib import Path
import shutil
import statistics

from strategic_collection import ROOT,read,write,digest
from policy_iteration_evidence_archive import upload_evidence


def maximum_output(player,stock):
    best = 0
    for chosen in itertools.product([False,True],repeat=len(player['powerPlants'])):
        plants = [p for p,on in zip(player['powerPlants'],chosen) if on]
        demand = [sum(p['cost'] for p in plants if p['type'] == kind) for kind in range(5)]
        if all(demand[i] <= stock[i] for i in range(4)) and demand[4] <= stock[0]+stock[1]-demand[0]-demand[1]:
            best = max(best,sum(p['citiesPowered'] for p in plants))
    return best


def main():
    current = ROOT/'ai/runs/resource-turn-proposals-v2'
    failed = ROOT/'ai/runs/resource-turn-proposals-v1'
    prep = read(current/'preparation.json')
    checks = read(current/'checks/assessment.json')
    assert checks['passed'] and checks['resource_positions'] == 755
    assert checks['bundles'] == 7185 and checks['real_purchases'] == 28177
    assert checks['construction_cases'] == 41 and checks['joint_witnesses'] == 336
    assert checks['preparation_sha256'] == digest(current/'preparation.json')
    assert checks['checker_sha256'] == digest(ROOT/'ai/strong/test-resource-turn-plans-v1.cjs')
    assert prep['proposal_module_sha256'] == digest(ROOT/'ai/strong/resource-turn-plans-v1.cjs')
    original = ROOT/'ai/runs/population-hybrid-development-source-prepared-v1/layout'
    assert prep['unchanged_runtime_files'] == len(prep['runtime_hashes']) == 1463
    for name,sha in prep['runtime_hashes'].items():
        assert digest(current/'runtime'/name) == digest(original/name) == sha
    active = read(ROOT/'ai/strong/population-hybrid-development-plan-v1.json')
    for name,sha in active['dependency_hashes'].items():assert digest(ROOT/name) == sha
    saved = [p for p in (current/'checks').glob('*.json') if p.name != 'assessment.json']
    assert len(saved) == 41
    receipt_bundles,receipt_joints = 0,0
    resources = ['coal','oil','garbage','uranium']
    for path in saved:
        entry = read(path);q,result = entry['request'],entry['result']
        g,p = q['state'],q['state']['players'][q['player']]
        assert result['selectedMove'] is None and result['qualification_eligible'] is False
        assert result['construction']['optimal'] is False
        bundles = {b['id']:b for b in result['bundles']}
        assert len(bundles) == len(result['bundles']) and '0,0,0,0' in bundles
        for bundle in bundles.values():
            counts = bundle['counts']
            assert all(type(n) is int and n >= 0 for n in counts) and len(counts) == 4
            stock = [p[r+'Left']+n for r,n in zip(resources,counts)]
            assert stock == bundle['stock']
            assert max(0,stock[0]-p['coalCapacity'])+max(0,stock[1]-p['oilCapacity']) <= p['hybridCapacity']
            assert stock[2] <= p['garbageCapacity'] and stock[3] <= p['uraniumCapacity']
            cost = 0
            for r,n in zip(resources,counts):
                count,prices = g[r+'Market'],g[r+'Prices']
                assert n <= count
                cost += sum(prices[len(prices)-count:len(prices)-count+n])
            assert cost == bundle['cost'] <= p['money']
            assert bundle['remainingMoney'] == p['money']-cost
            assert maximum_output(p,stock) == bundle['fuelSupportedOutput']
            assert bundle['actions'] == [{'name':'BuyResource','data':{'resource':r}}
                for r,n in zip(resources,counts) for _ in range(n)]
            receipt_bundles += 1
        paths = {row['cities']:row for row in result['construction']['paths']}
        for joint in result['joint']:
            bundle = bundles[joint['bundle']]
            for witness in joint['witnesses']:
                route = paths[witness['cities']]
                assert sum(action['data']['price'] for action in route['actions']) == route['cost']
                assert witness['totalCost'] == bundle['cost']+route['cost'] <= p['money']
                assert witness['remainingMoney'] == p['money']-witness['totalCost']
                assert witness['powered'] == min(witness['cities'],bundle['fuelSupportedOutput'])
                receipt_joints += 1
    assert checks['known_case']['witness'] == {'cities':21,'constructionCost':161,'totalCost':178,
        'remainingMoney':61,'powered':21}
    failure = read(failed/'checks/failure.json')
    assert not failure['report']['passed'] and failure['report']['resource_positions'] == 23
    assert 'pp.type <= 5' in failure['error']
    old_prep = read(failed/'preparation.json')
    assert old_prep['proposal_module_sha256'] == digest(failed/'runtime/ai/strong/resource-turn-plans-v1.cjs')
    evidence = ROOT/'ai/runs/resource-turn-proposal-evidence-v1'
    assert not evidence.exists();evidence.mkdir()
    sources = [p for folder in [current,failed] for p in folder.rglob('*') if p.is_file()
        and 'runtime' not in p.relative_to(folder).parts]
    sources += [failed/'runtime/ai/strong/resource-turn-plans-v1.cjs']
    sources += [ROOT/'ai/strong'/name for name in [
        'resource-turn-plans-v1.cjs','test-resource-turn-plans-v1.cjs','collect-resource-turn-plans-v1.py',
        'population-hybrid-development-source-v1.json','weak-cell-economy-evidence-v1.json',
        'weak-cell-resource-counterfactual-v1.json','policy_iteration_evidence_archive.py']]
    for source in sources:
        destination = evidence/source.relative_to(ROOT)
        destination.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,destination)
    summary = {'revision':'resource-turn-proposals-v1','status':'verified_unintegrated_candidate_generator',
        'public_resource_positions':755,'rule_count_cells':20,'engine_legal_bundles':7185,
        'real_engine_purchase_transitions':28177,'zero_purchase_baselines':755,'secret_invariance_cases':755,
        'construction_cases':41,'conditional_construction_paths':184,'executed_joint_witnesses':336,
        'exhaustively_checked_inventory_states':1870,'minimum_fuel_price_target_checks':422,
        'independent_saved_bundle_checks':receipt_bundles,'independent_joint_budget_checks':receipt_joints,
        'known_omission_recovered_as_proposal':checks['known_case'],
        'unchanged_source_files':1463,'active_screen_dependencies_unchanged':True,
        'source_module_sha256':prep['proposal_module_sha256'],
        'engineering_timings_local_HX370_ms':{
            name:{'samples':len(values),'median':statistics.median(values),'maximum':max(values)}
            for name,values in checks['timing'].items()},
        'preserved_failures':['Initial guard omitted standard free-fuel fusion plant50/type6; fixed and complete suite passed.',
            'An initial v2 test invocation preceded completion of the copy and failed on a missing engine module; its log is retained. The completed package was then checked.'],
        'limits':['No selected move, neural bundle valuation or fresh strength evidence.',
            'Fuel enumeration covers one/two identical-cycle plant requirements, not all possible stockpiles.',
            'Construction witnesses assume no intervening opponent action/deck draw; bounded beam search is not an optimum or impossibility proof.',
            'Local engineering timings are not representative gameplay latency or an AMD8840U benchmark.'],
        'next':'In a separate research adapter, preserve the exact existing model resource turn as an additional baseline, then score complete legal bundles with public sampled worlds and realistic opponent continuations. Keep the running five-arm screen frozen; use fresh paired games before any adoption.',
        'new_strength_games':0,'new_hf_jobs':0,'gradients':False,'qualification_eligible':False,'reserved_final_seeds_used':False}
    write(evidence/'assessment.json',summary)
    write(evidence/'manifest.json',{str(p.relative_to(evidence)):digest(p) for p in evidence.rglob('*') if p.is_file()})
    receipt = upload_evidence(evidence)
    write(ROOT/'ai/strong/resource-turn-proposal-evidence-v1.json',{**summary,**receipt})
    print(json.dumps({**receipt,'bundles':7185,'joint_witnesses':336,
        'engineering_timings_local_HX370_ms':summary['engineering_timings_local_HX370_ms']},indent=2))


if __name__ == '__main__':
    main()
