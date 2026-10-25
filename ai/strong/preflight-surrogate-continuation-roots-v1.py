"""Endpoint twin games for fresh root capture; no jobs, gradients or strength claims."""
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
import os
from pathlib import Path
import shutil

from strategic_collection import ROOT, read, write, digest
from hybrid_search import Model
from population_hybrid_policy import PopulationPolicy
from surrogate_continuation_roots_v1 import PROTOCOL, one_game, verify_game

OUT = ROOT/'ai/runs/surrogate-continuation-roots-preflight-v1'
RUNTIME_PROOF = ROOT/'ai/runs/reference-opponent-diagnostic-v2/protocol.json'
MODEL = ROOT/'ai/runs/policy-iteration-trained-8840u-prepared-v2/local-package-frozen-1/policy.onnx'


def main():
    assert not os.environ.get('NODE_OPTIONS')
    p = read(PROTOCOL); frozen = read(RUNTIME_PROOF); runtime = Path(frozen['runtime'])
    assert all(digest(runtime/name) == sha for name, sha in frozen['runtime_hashes'].items())
    assert digest(MODEL) == p['focal_model_sha256']
    files = [Path(__file__), PROTOCOL, ROOT/'ai/strong/surrogate_continuation_roots_v1.py',
             ROOT/'ai/strong/test_surrogate_continuation_roots_v1.py',
             ROOT/'ai/strong/population_hybrid_policy.py', ROOT/'ai/strong/hybrid_search.py',
             ROOT/'ai/strong/strategic_collection.py', ROOT/'ai/infer.py', ROOT/'ai/pool.py']
    code = {str(path.relative_to(ROOT)): digest(path) for path in files}
    OUT.mkdir(parents=True, exist_ok=False)
    tasks = [{'runtime': str(runtime), 'model': str(MODEL), 'output': str(OUT/f'{n}p'),
              'players': n, 'deal': 0, 'seat': n-1, 'rule': 1, 'mode': 'preflight', 'twin': True} for n in (2, 6)]
    status = {'stage': 'running', 'started_at': datetime.now(timezone.utc).isoformat(), 'pid': os.getpid(),
              'code_hashes': code, 'runtime_proof_sha256': digest(RUNTIME_PROOF),
              'runtime_hashes': frozen['runtime_hashes'], 'model_sha256': digest(MODEL), 'tasks': tasks,
              'cases': {}, 'errors': [], 'new_hf_jobs': 0, 'gradient_updates': 0,
              'qualification_eligible': False, 'reserved_final_seeds_used': False,
              'scope': 'Two endpoint Recharged/sealed games at the last focal seat, each with an exact unobserved twin. Other count/rule/phase contexts have canonical input checks, not complete twin games.'}
    write(OUT/'intent.json', status); write(OUT/'status.json', status)
    try:
        with ProcessPoolExecutor(max_workers=2) as pool:
            futures = {pool.submit(one_game, task): task for task in tasks}
            for future in as_completed(futures):
                task = futures[future]
                try:
                    result = future.result(); status['cases'][str(task['players'])] = result
                except Exception as error:
                    status['errors'].append({'task': task, 'error': type(error).__name__+': '+str(error)})
                write(OUT/'status.json', status)
                print({'complete': len(status['cases']), 'planned': 2, 'errors': status['errors']}, flush=True)
        assert not status['errors'] and set(status['cases']) == {'2', '6'}
        policy = PopulationPolicy(Model(MODEL, threads=1), runtime/'ai/strong/population-hybrid-policy.cjs', arm='filter')
        try:
            status['independent_checks'] = {str(n): verify_game(OUT/f'{n}p', policy) for n in (2, 6)}
            bad = OUT/'rejected-duplicate-fixture'; shutil.copytree(OUT/'2p', bad)
            roots = read(bad/'roots.json'); assert roots['eligible']
            roots['eligible'].append(roots['eligible'][0]); write(bad/'roots.json', roots)
            receipt = read(bad/'verified.json'); receipt['files']['roots.json'] = digest(bad/'roots.json')
            receipt['eligible_decisions'] += 1; write(bad/'verified.json', receipt)
            try: verify_game(bad, policy)
            except AssertionError: status['resealed_duplicate_rejected'] = True
            else: raise AssertionError('A resealed duplicate eligible decision was accepted')
        finally: policy.close()
        assert all(digest(ROOT/name) == sha for name, sha in code.items())
        assert all(digest(runtime/name) == sha for name, sha in frozen['runtime_hashes'].items())
        status.update(stage='complete', complete_games=2, paired_executions=4,
            selected_roots=sum(r['selected_roots'] for r in status['cases'].values()),
            eligible_decisions=sum(r['eligible_decisions'] for r in status['cases'].values()),
            caps=0, runtime_unchanged=True)
    except BaseException as error:
        status.update(stage='failed', error=type(error).__name__+': '+str(error)); raise
    finally:
        status['updated_at'] = datetime.now(timezone.utc).isoformat(); write(OUT/'status.json', status)
    print({key: status[key] for key in ('stage', 'complete_games', 'paired_executions', 'selected_roots', 'eligible_decisions', 'caps')}, flush=True)


if __name__ == '__main__': main()
