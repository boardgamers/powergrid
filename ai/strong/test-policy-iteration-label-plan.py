"""Coverage and runtime-admission contracts; never launches jobs or trains."""
from collections import Counter
import copy
import importlib.util

from strategic_collection import ROOT, read, write, digest


def module(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT/'ai/strong'/file)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def rejected(fn):
    try:
        fn()
    except AssertionError:
        return
    raise AssertionError('Invalid plan input was accepted')


def main():
    planner = module('full_label_planner', 'prepare-policy-iteration-labels.py')
    manager = module('full_label_manager', 'manage-policy-iteration-labels.py')
    index = read(ROOT/'ai/runs/policy-iteration-selected-v2/selected-index.json')
    old = read(ROOT/'ai/strong/policy-iteration-teacher-protocol-v2.json')
    pilot = {r['rootId'] for r in old['pilot_roots']}
    costs = {(n, mode): float(n*100) for n in range(2, 7) for mode in old['modes']}
    shards = planner.partition(index, pilot, costs)
    assignments = Counter((rid, s['mode']) for s in shards for rid in s['root_ids'])
    expected = {(r['rootId'], m) for r in index for m in old['modes']} - {(rid, m) for rid in pilot for m in old['modes']}
    assert set(assignments) == expected and set(assignments.values()) == {1} and len(expected) == 33840
    assert shards == planner.partition(list(reversed(index)), pilot, costs)
    changed = copy.deepcopy(index)
    for row in changed:
        row['outcome'] = 'adverse'
        row['teacher_gain'] = -1
    assert shards == planner.partition(changed, pilot, costs), 'Outcome fields changed selection'
    assert len(manager.first_wave({'shards': shards})) == 60
    first = [s for s in shards if s['id'] in manager.first_wave({'shards': shards})]
    assert {(s['players'], s['behavior'], s['opponent'], s['mode']) for s in first} == {
        (n, b, o, m) for n in range(2, 7) for b in old['behaviors'] for o in old['opponents'] for m in old['modes']}
    for bad in [0., -1., float('nan'), float('inf'), 1e9]:
        rejected(lambda: planner.partition(index, pilot, {k: bad for k in costs}))
    rejected(lambda: planner.partition(index + [index[0]], pilot, costs))
    rejected(lambda: planner.partition(index, pilot | {'missing'}, costs))
    write(ROOT/'ai/strong/policy-iteration-label-plan-contracts-v2.json', {
        'passed': True, 'new_root_mode_pairs': 33840, 'reuse_pairs': 720,
        'first_wave_strata': 60, 'order_and_outcome_independent': True,
        'invalid_runtime_duplicate_and_missing_id_rejections': 7,
        'synthetic_runtime_only': True, 'jobs_launched': 0, 'gradients': False,
        'code': {file: digest(ROOT/'ai/strong'/file) for file in ['prepare-policy-iteration-labels.py', 'manage-policy-iteration-labels.py', 'test-policy-iteration-label-plan.py']},
        'qualification_eligible': False})
    print({'passed': True, 'new_root_mode_pairs': 33840, 'first_wave_strata': 60})


if __name__ == '__main__':
    main()
