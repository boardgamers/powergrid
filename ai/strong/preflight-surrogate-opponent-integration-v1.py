"""Complete engineering continuations with real focal inference and an untrained surrogate."""
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path

import numpy as np
import torch
from strategic_collection import ROOT, read, write, digest
from hybrid_search import Model, predict_batch
from model_opponent_surrogate_v1 import OpponentSurrogate
from opponent_surrogate_policy_v1 import make_policy, SurrogatePolicy
from surrogate_opponent_continuations_v1 import SurrogateContinuationProbe

STRONG = ROOT/'ai/strong'
OUT = ROOT/'ai/runs/surrogate-opponent-integration-v1'
RUNTIME_PROOF = ROOT/'ai/runs/reference-opponent-diagnostic-v2/protocol.json'


def main():
    assert not os.environ.get('NODE_OPTIONS')
    runtime_proof = read(RUNTIME_PROOF); runtime = Path(runtime_proof['runtime'])
    assert all(digest(runtime/name) == sha for name, sha in runtime_proof['runtime_hashes'].items())
    code = {str(p.relative_to(ROOT)): digest(p) for p in [Path(__file__),
        STRONG/'surrogate-opponent-continuations-v1.cjs', STRONG/'surrogate_opponent_continuations_v1.py',
        STRONG/'opponent_surrogate_policy_v1.py', STRONG/'opponent_surrogate_training_v1.py',
        STRONG/'model_opponent_surrogate_v1.py', STRONG/'export-opponent-surrogate-v1.py',
        STRONG/'reference-opponent-continuations-v2.cjs', STRONG/'reference-search-public-balances-v1.cjs',
        STRONG/'analysis-public-balances-v1.cjs', STRONG/'hybrid_search.py', ROOT/'ai/infer.py', ROOT/'ai/pool.py']}
    os.environ['PG_REFERENCE_RUNTIME'] = str(runtime)
    focal_path = ROOT/'ai/runs/policy-iteration-trained-8840u-prepared-v2/local-package-frozen-1/policy.onnx'
    focal = Model(focal_path, threads=1)
    assert focal.sha256 == '55331f43379e8fe89025d93b1a7a48c88e0ea39b4ebd3a7ef8240d4b62753530'
    OUT.mkdir(parents=True, exist_ok=False)
    status = {'stage': 'preparing', 'started_at': datetime.now(timezone.utc).isoformat(), 'code_hashes': code,
              'runtime_proof_sha256': digest(RUNTIME_PROOF), 'runtime': str(runtime),
              'runtime_hashes': runtime_proof['runtime_hashes'], 'focal_sha256': focal.sha256,
              'surrogate_untrained_fixture': True, 'gradient_updates': 0, 'new_hf_jobs': 0,
              'qualification_eligible': False, 'reserved_final_seeds_used': False}
    write(OUT/'status.json', status)
    torch.set_num_threads(1); torch.manual_seed(17001)
    net = OpponentSurrogate().eval()
    with torch.no_grad(): net.score[-1].weight.normal_(0, .02)
    cp = {'architecture': 'opponent_surrogate_v1', 'model_args': {}, 'feature_revision': '4.3-strategic-correction',
          'state_dim': 1217, 'action_dim': 101, 'max_candidates': 6, 'state_dict': net.state_dict(),
          'random_untrained_fixture': True, 'fixture_initialization_seed': 17001, 'qualification_eligible': False}
    fixture_dir = OUT/'untrained-fixture'; (fixture_dir/'14101').mkdir(parents=True)
    checkpoint = fixture_dir/'14101/random-untrained.pt'; torch.save(cp, checkpoint)
    spec = importlib.util.spec_from_file_location('integration_fixture_exporter', STRONG/'export-opponent-surrogate-v1.py')
    exporter = importlib.util.module_from_spec(spec); spec.loader.exec_module(exporter)
    exporter.export(checkpoint, fixture_dir/'14101/derivative')
    policy = {**make_policy([{'seed': 14101, 'path': '14101/derivative/inference64.onnx',
                             'sha256': digest(fixture_dir/'14101/derivative/inference64.onnx'),
                             'checkpoint_sha256': digest(checkpoint)}]),
              'random_untrained_fixture': True, 'purpose': 'Engineering integration only; never a learned opponent or candidate.'}
    write(fixture_dir/'policy.json', policy)
    surrogate = SurrogatePolicy(policy, fixture_dir)
    probe = SurrogateContinuationProbe(focal, surrogate, workers=2)
    other = None
    try:
        fixtures = [json.loads(line) for line in (runtime/'ai/strong/fixtures/multiplayer-serving-v1.jsonl').read_text().splitlines()]
        cases = {}
        # Select by count/rules/public phase only, before observing any continuation outcome.
        for item in fixtures:
            request = item['request']; state = request['state']; n = len(state['players'])
            sealed = bool(state['options'].get('fastBid')); variant = state['options']['variant']
            key = f'{n}p/{variant}/{"sealed" if sealed else "open"}'
            if key in cases: continue
            wanted = 'Bid' if sealed else 'Build' if n % 2 == 0 else 'ChoosePowerPlant'
            if not any(m['name'] == wanted for m in item['legal']): continue
            root = probe.node.call({**request, 'featureRevision': '4.3-strategic-correction', 'op': 'prepare'})
            if sealed and not root['prior']: continue
            model = predict_batch(focal, [root['observation']])[0]
            if model in root['lossFilter']['forbidden']: model = root['lossFilter']['passIndex']
            alternatives = [a for a in root['options'] if a != model and a not in root['lossFilter']['forbidden']]
            if not alternatives: continue
            cases[key] = {'request': request, 'options': [model, alternatives[0]], 'phase': wanted,
                          'prior_bids': len(root['prior'])}
        assert len(cases) == 20 and {len(c['request']['state']['players']) for c in cases.values()} == {2, 3, 4, 5, 6}
        write(OUT/'cases.json', cases)
        status.update(stage='complete_continuations', cases_sha256=digest(OUT/'cases.json'), completed={})
        write(OUT/'status.json', status)
        for i, (key, case) in enumerate(sorted(cases.items())):
            result = probe.run(case['request'], case['options'], mode='surrogate_opponent_v1', samples=1, max_steps=2400)
            output = OUT/f'case-{i}.json'; write(output, result)
            assert result['usable'] and result['caps'] == 0 and len(result['rows']) == 2
            status['completed'][key] = {'file': output.name, 'sha256': digest(output), 'rows': len(result['rows']),
                                       'seconds': result['seconds'], 'inference_decisions': result['inference_decisions']}
            write(OUT/'status.json', status)
            print({'case': key, 'complete': len(status['completed']), 'total': 20, 'caps': result['caps'],
                   'surrogate_decisions': result['inference_decisions']['surrogate'], 'seconds': result['seconds']}, flush=True)
        # Partition invariance is checked independently, including intentionally capped outcomes.
        case = cases['6p/recharged/sealed']; other = SurrogateContinuationProbe(focal, surrogate, workers=1)
        left = probe.run(case['request'], case['options'], mode='surrogate_opponent_v1', samples=4, max_steps=12)
        right = other.run(case['request'], case['options'], mode='surrogate_opponent_v1', samples=4, max_steps=12)
        write(OUT/'partition-workers-2.json', left); write(OUT/'partition-workers-1.json', right)
        assert left['rows'] == right['rows'] and left['inference_decisions'] == right['inference_decisions']
        assert not left['usable'] and left['outer_caps'] > 0 and left['nested_caps'] == 0
        assert all(digest(ROOT/name) == sha for name, sha in code.items())
        assert all(digest(runtime/name) == sha for name, sha in runtime_proof['runtime_hashes'].items())
        status.update(stage='complete', complete_continuations=40, caps=0, worker_partition_exact=True,
                      intentional_partition_test_caps=left['outer_caps'], runtime_unchanged=True,
                      scope='Complete public-feature/ONNX integration with real frozen focal inference and random untrained surrogate weights. Canonical fixture roots, not fresh strength games. No trained-surrogate fidelity or stronger-policy claim.')
    except BaseException as error:
        status.update(stage='failed', error=type(error).__name__ + ': ' + str(error)); raise
    finally:
        probe.close()
        if other is not None: other.close()
        write(OUT/'status.json', status)
    print({k: status[k] for k in ('stage', 'complete_continuations', 'caps', 'worker_partition_exact')})


if __name__ == '__main__': main()
