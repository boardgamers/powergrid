"""Guarded whole-game runner using the unchanged standalone public-policy loop.

Default validates only. Execution requires a frozen artifact, candidate and job
contract. Final contracts additionally require a prior launch intent; this runner
does not itself reserve seeds, submit HF jobs, retry games or select a candidate.
"""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import time

import public_policy_arena_v1 as arena
from public_policy_final_audit_v1 import artifact_identity, audit_shard, digest, read, require, same, integer
from public_policy_final_contract_v1 import admit, audit_execution_binding
from public_policy_runtime_v1 import checked_path


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')


def configuration(args):
    root = args.artifact.resolve()
    identity = artifact_identity(root, args.descriptor)
    spec = read(checked_path(root, args.descriptor))
    manifest = read(checked_path(root, spec['runtime_manifest']['path']))
    entry = 'ai/strong/public_policy_final_runner_v1.py'
    require(Path(__file__).resolve() == checked_path(root, entry) and manifest.get(entry) == digest(__file__),
            'Execute final runner from its frozen artifact')
    for name in ('public_policy_final_contract_v1.py', 'public_policy_final_audit_v1.py', 'public_policy_arena_v1.py'):
        require('ai/strong/'+name in manifest, 'Missing execution/audit dependency')
    require(Path(arena.__file__).resolve() == checked_path(root, 'ai/strong/public_policy_arena_v1.py'), 'Wrong game-loop import')
    candidate = read(args.candidate); contract = read(args.contract)
    admission = admit(contract, candidate, digest(args.candidate), identity)
    shard = admission['shard']
    integer(args.workers, 1); require(args.workers <= 32, 'Excessive game concurrency')
    require((shard['opponent'] == 'a260') == bool(args.opponent_model), 'Opponent checkpoint mismatch')
    if args.opponent_model:
        require(digest(args.opponent_model) == shard['opponent_sha256'], 'Wrong opponent checkpoint bytes')
    settings = identity['settings']
    config = {**{k: shard[k] for k in ('players', 'opponent', 'opponent_sha256', 'seed', 'start', 'deals')},
              'artifact': str(root), 'runtime': str(root), 'descriptor': args.descriptor,
              'output': str(args.output.resolve()), 'workers': args.workers,
              'arm': identity['backend'] if identity['backend'] == 'opponent-auction-v1' else settings['arm'],
              'samples': settings['samples'], 'search_workers': settings['workers'],
              'model': str(checked_path(root, spec['model']['path'])), 'model_sha256': identity['modelSha256'],
              'opponent_model': str(args.opponent_model.resolve()) if args.opponent_model else None,
              'reference_artifact': None, 'identity': identity,
              'candidate_path': str(args.candidate.resolve()), 'contract_path': str(args.contract.resolve())}
    binding = {**admission, 'contract_sha256': digest(args.contract),
               'runner_sha256': digest(__file__), 'purpose': contract['purpose']}
    return config, binding


def execute(config, binding):
    output = Path(config['output']); output.mkdir(parents=True, exist_ok=False)
    # Exclusive output creation is deliberate: an observation timeout must not
    # replace an original run, its partial receipts or an ambiguous outcome.
    for name in ('candidate', 'contract'):
        shutil.copyfile(config[name+'_path'], output/(name+'.json'))
        require(digest(output/(name+'.json')) == binding[name+'_sha256'], 'Execution input changed before launch')
    write(output/'intent.json', {'pid': os.getpid(), 'started_at': datetime.now(timezone.utc).isoformat(),
                                'binding': binding, 'config': config})
    shard = binding['shard']; n = shard['players']
    episodes = list(range(shard['start']*4*n, (shard['start']+shard['deals'])*4*n))
    records, errors = [], []; start = time.perf_counter(); failure = None
    try:
        with ProcessPoolExecutor(max_workers=min(config['workers'], len(episodes))) as pool:
            pending = {pool.submit(arena.play, config, episode): episode for episode in episodes}
            for future in as_completed(pending):
                episode = pending[future]
                try:
                    record = future.result(); records.append(record)
                    print(json.dumps({'complete': len(records), 'expected': len(episodes), 'episode': episode}), flush=True)
                except Exception as error:
                    errors.append({'episode': episode, 'error': type(error).__name__+': '+str(error)})
        require(not errors and len(records) == len(episodes), 'Incomplete execution; preserve original receipts')
        require(not any(r['terminal']['truncated'] or r['rollout_caps'] for r in records), 'Capped game/search')
        require(same(artifact_identity(config['artifact'], config['descriptor']), config['identity']), 'Artifact changed during execution')
    except BaseException as error:
        failure = type(error).__name__+': '+str(error)
        raise
    finally:
        report = {'config': config, 'results': sorted(records, key=lambda r: r['episode']),
                  'errors': errors, 'validation_error': failure, 'passed': failure is None,
                  'expected_games': len(episodes), 'completed_games': len(records),
                  'all_complete': len(records) == len(episodes) and not errors,
                  'game_caps': sum(r['terminal']['truncated'] for r in records),
                  'rollout_caps': sum(r['rollout_caps'] for r in records), 'seconds': time.perf_counter()-start,
                  'qualification_eligible': False, 'reserved_final_seeds_used': binding['reserved'],
                  'execution_binding': binding}
        write(output/'evaluation.json', report)
    try:
        audit = audit_shard(output, shard, config['identity'], reserved=binding['reserved'])
        audit['execution_binding'] = audit_execution_binding(output, config['identity'], digest(__file__))
        write(output/'audit.json', audit)
    except BaseException as error:
        report.update(passed=False, validation_error=type(error).__name__+': '+str(error))
        write(output/'evaluation.json', report)
        raise
    print(json.dumps({'complete': True, 'games': len(records), 'counts': audit['counts'],
                      'reserved_final_seeds_used': binding['reserved'], 'qualified': False}), flush=True)


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--artifact', type=Path, required=True)
    parser.add_argument('--descriptor', default='policy.json')
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--contract', type=Path, required=True)
    parser.add_argument('--opponent-model', type=Path)
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args(); config, binding = configuration(args)
    if args.execute:
        execute(config, binding)
    else:
        print(json.dumps({'valid_contract': True, 'execute': False, 'binding': binding}), flush=True)


if __name__ == '__main__':
    main()
