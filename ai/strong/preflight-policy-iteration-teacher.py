"""Frozen controls for all decision types and 96-world/worker-offset parity."""
import gzip, hashlib, json, time
from policy_iteration_teacher import ROOT, PROTOCOL, read, write, digest, get_model, Node, prepare, evaluate, REVISION
from strategic_teacher import evaluate as old_evaluate


def terminals(rows):
    return sorted([{k: v for k, v in r.items() if k != 'initialBelief'} for r in rows], key=lambda r: r['env'])


def main():
    p = read(PROTOCOL); path = ROOT/p['roots']['file']; assert digest(path) == p['roots']['sha256']
    with gzip.open(path, 'rt') as f: roots = list(map(json.loads, f))
    out = ROOT/'ai/runs/policy-iteration-teacher-preflight-v2'; out.mkdir(exist_ok=False)
    model = get_model(p); node = Node('strong/sealed-belief-continuations.cjs')
    trace = Node('strong/policy-iteration-belief-traces.cjs'); results = []; start = time.monotonic()
    try:
        choices = []
        for n in [2, 6]:
            for kind, variant, sealed, affected in [('nomination', 'original', False, False),
                ('building', 'recharged', True, False), ('bid', 'recharged', False, False), ('bid', 'original', True, True)]:
                candidates = sorted((r for r in roots if r['players'] == n and r['decision'] == kind and r['variant'] == variant and r['sealed'] == sealed),
                                    key=lambda r: hashlib.sha256(('teacher-v2-preflight:' + r['rootId']).encode()).hexdigest())
                for r in candidates:
                    prep = node.call({'op': 'prepare', **r['request'], 'featureRevision': REVISION})
                    if bool(prep['prior']) == affected: choices.append(r); break
                else: raise AssertionError('Missing plumbing stratum')
        with gzip.open(out/'controls.jsonl.gz', 'wt') as f:
            for root in choices:
                proposals = prepare(node, model, root)
                options = [root['model_proposal'], next(i for i in proposals if i != root['model_proposal'])]
                prep = node.call({'op': 'prepare', **root['request'], 'featureRevision': REVISION})
                for mode in p['modes']:
                    old = old_evaluate(model, root, options, mode, 'a', 2, 4)
                    control = evaluate(model, root, options, mode, 'a', 2, 4, belief='uniform_control')
                    policy = evaluate(model, root, options, mode, 'a', 2, 4, belief='policy')
                    assert all(r['usable'] and len(r['rollouts']) == 4 for r in [old, control, policy])
                    assert terminals(old['rollouts']) == terminals(control['rollouts'])
                    for k in ['sample_outcomes', 'paired_advantages_over_proposal', 'options', 'seed']:
                        assert old[k] == control[k]
                    if not prep['prior']: assert terminals(old['rollouts']) == terminals(policy['rollouts'])
                    q = {**root['request'], 'samples': 48, 'seed': policy['seed'], 'mode': mode,
                         'neuralBeliefs': policy['neural_beliefs']}
                    expected = node.call({'op': 'belief-traces', **q, 'belief': 'policy'})['traces']
                    all_traces = trace.call({**q, 'samples': 96})['traces']
                    assert len(all_traces) == 96 and all_traces[:48] == expected
                    f.write(json.dumps({'root': root['rootId'], 'old': old, 'control': control, 'policy': policy})+'\n'); f.flush()
                    results.append({'rootId': root['rootId'], 'players': root['players'], 'decision': root['decision'],
                                    'mode': mode, 'rollouts': 12, 'affected': bool(prep['prior']), 'trace_checks': 96})
                    print(results[-1], flush=True)
            # Verify the larger batch itself, including worker offsets >48 and
            # exact first-two-world agreement with the small runtime probe.
            late = sorted((r for r in roots if r['players'] == 6 and r['decision'] == 'bid' and r['sealed']),
                          key=lambda r: (-r['round'], r['rootId']))
            root = next(r for r in late if node.call({'op': 'prepare', **r['request'], 'featureRevision': REVISION})['prior'])
            options = prepare(node, model, root)
            options = [root['model_proposal'], next(i for i in options if i != root['model_proposal'])]
            for mode in p['modes']:
                small = evaluate(model, root, options, mode, 'b', 2, 4, belief='policy')
                large = evaluate(model, root, options, mode, 'b', 96, 24, belief='policy')
                assert small['usable'] and large['usable'] and len(large['rollouts']) == 192
                assert terminals([r for r in large['rollouts'] if r['sample'] < 2]) == terminals(small['rollouts'])
                traces = trace.call({**root['request'], 'samples': 96, 'seed': large['seed'], 'mode': mode,
                                     'neuralBeliefs': large['neural_beliefs']})['traces']
                for r in large['rollouts']:
                    assert r['initialBelief'] == {'kind': 'policy', 'committed': traces[r['sample']]}
                f.write(json.dumps({'root': root['rootId'], 'small': small, 'large': large})+'\n'); f.flush()
                results.append({'rootId': root['rootId'], 'players': 6, 'decision': 'bid', 'mode': mode,
                                'rollouts': 196, 'batch_and_offset_parity': True, 'trace_checks': 192})
                print(results[-1], flush=True)
    finally: node.close(); trace.close()
    report = {'passed': True, 'protocol_sha256': digest(PROTOCOL), 'root_sha256': p['roots']['sha256'],
              'model_sha256': model.sha256, 'cases': results, 'rollouts': sum(r['rollouts'] for r in results),
              'seconds': time.monotonic()-start, 'artifacts': {'controls.jsonl.gz': digest(out/'controls.jsonl.gz')},
              'gradients': False, 'qualification_eligible': False}
    assert report['rollouts'] == 584
    write(out/'preflight.json', report); print({'passed': True, 'rollouts': report['rollouts']}, flush=True)


if __name__ == '__main__': main()
