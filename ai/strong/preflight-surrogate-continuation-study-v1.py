"""Real captured engineering roots and all three modes; surrogate remains untrained."""
from datetime import datetime, timezone
import os
from pathlib import Path

from strategic_collection import ROOT, read, write, digest
from hybrid_search import Model
from opponent_surrogate_policy_v1 import SurrogatePolicy
from surrogate_continuation_study_v1 import code_hashes, run_chunk, verify_chunk, paired_root, MODES

OUT = ROOT/'ai/runs/surrogate-continuation-study-preflight-v1'
REAL = ROOT/'ai/runs/surrogate-continuation-roots-runtime-collected-v1/surrogate-continuation-runtime-v1-2p-0-1'
FIXTURE = ROOT/'ai/runs/surrogate-opponent-integration-v1/untrained-fixture'


def main():
    assert not os.environ.get('NODE_OPTIONS')
    runtime_proof = ROOT/'ai/runs/reference-opponent-diagnostic-v2/protocol.json'
    proof = read(runtime_proof); runtime = Path(proof['runtime'])
    assert all(digest(runtime/name) == sha for name, sha in proof['runtime_hashes'].items())
    os.environ['PG_REFERENCE_RUNTIME'] = str(runtime)
    verified = read(REAL/'verified.json'); assert verified['verified'] and verified['review']['games'] == 8
    artifacts = REAL/'artifacts'; manifest = read(artifacts/'manifest.json')
    assert digest(artifacts/'manifest.json') == verified['evidence']['manifest_sha256']
    assert all(digest(artifacts/name) == sha for name, sha in manifest.items())
    selected = read(artifacts/'games/game-0/roots.json')['roots']
    roots = {phase: selected[phase] for phase in ('plant', 'bid')}
    assert roots['plant']['prior_actors'] == [] and roots['bid']['prior_actors']
    # Fixed game and phases, before running any continuation. This source deal
    # has a separate runtime prefix and is excluded from the scientific study.
    assert all(root['identity']['mode'] == 'runtime' for root in roots.values())
    focal = Model(ROOT/'ai/runs/policy-iteration-trained-8840u-prepared-v2/local-package-frozen-1/policy.onnx', threads=1)
    surrogate_pin = digest(FIXTURE/'policy.json'); policy = read(FIXTURE/'policy.json')
    assert policy['random_untrained_fixture'] is True
    surrogate = SurrogatePolicy(policy, FIXTURE)
    OUT.mkdir(parents=True, exist_ok=False)
    hashes = code_hashes()
    status = {'stage': 'running', 'started_at': datetime.now(timezone.utc).isoformat(),
              'code_hashes': hashes, 'preflight_sha256': digest(__file__),
              'runtime_proof_sha256': digest(runtime_proof), 'runtime': str(runtime),
              'runtime_hashes': proof['runtime_hashes'], 'source_verified_sha256': digest(REAL/'verified.json'),
              'surrogate_policy_sha256': surrogate_pin, 'surrogate_untrained_fixture': True,
              'gradient_updates': 0, 'new_hf_jobs': 0, 'cases': {},
              'qualification_eligible': False, 'reserved_final_seeds_used': False}
    write(OUT/'roots.json', roots); write(OUT/'status.json', status)
    try:
        for phase, root in roots.items():
            results = {}
            for mode in MODES:
                # Exercise actual sample partitioning without repeating any worlds.
                parts = [(0, 4), (4, 4)] if mode == 'neural_population' else [(0, 8)]
                results[mode] = []
                for begin, count in parts:
                    folder = OUT/f'{phase}-{mode}-{begin}-{count}'
                    use_surrogate = mode == 'surrogate_opponent_v1'
                    outcome = run_chunk(root, mode, begin, count, focal, surrogate if use_surrogate else None,
                                        folder, workers=2, surrogate_sha256=surrogate_pin if use_surrogate else None)
                    assert outcome['stage'] == 'complete' and outcome['caps'] == 0
                    result = verify_chunk(folder, root, surrogate_sha256=surrogate_pin if use_surrogate else None)
                    results[mode].append(result)
                    status['cases'][folder.name] = {'status_sha256': digest(folder/'status.json'),
                        'result_sha256': digest(folder/'result.json'), 'rows': len(result['rows']),
                        'wall_seconds': outcome['wall_seconds'], 'caps': result['caps']}
                    write(OUT/'status.json', status)
                    print({'case': folder.name, 'rows': len(result['rows']), 'seconds': outcome['wall_seconds'], 'caps': result['caps']}, flush=True)
            joined = paired_root(root, results); assert joined['complete'] and joined['caps'] == 0
            write(OUT/f'{phase}-paired.json', joined)
        assert hashes == code_hashes()
        assert all(digest(runtime/name) == sha for name, sha in proof['runtime_hashes'].items())
        status.update(stage='complete', complete_continuations=96, caps=0, runtime_unchanged=True,
                      paired_worlds_exact=True, source_cases=2,
                      scope='Actual HF-captured runtime roots, real frozen focal inference, reference search, original mixture and explicitly untrained surrogate. Engineering integration only; not trained-surrogate fidelity, HF runtime admission or playing strength.')
    except BaseException as error:
        status.update(stage='failed', error=type(error).__name__+': '+str(error)); raise
    finally: write(OUT/'status.json', status)
    print({k: status[k] for k in ('stage', 'complete_continuations', 'caps', 'paired_worlds_exact')})


if __name__ == '__main__': main()
