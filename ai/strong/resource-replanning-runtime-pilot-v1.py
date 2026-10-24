"""Complete paired endpoint pilots from a pinned package; no strength estimates."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import threading
import time

from strategic_collection import ROOT, read, write, digest
from resource_development_v1 import PROTOCOL, validate
from resource_policy_verification_v1 import verify_evaluation
from hybrid_search import Model, Node, model_revision, public_seed

PLAN = ROOT / 'ai/strong/resource-replanning-runtime-plan-v1.json'
OUT = ROOT / 'ai/runs/resource-replanning-runtime-v1'


def validate_source(source_path, allow_unuploaded=False):
    source = read(source_path)
    assert source['remote_archive_verified'] or (allow_unuploaded and source['revision'] == 'layout-preflight')
    assert source['protocol_sha256'] == digest(PROTOCOL)
    assert source['runtime_plan_sha256'] == digest(PLAN)
    assert digest(ROOT / 'resource-runtime-manifest.json') == source['manifest_sha256']
    manifest = read(ROOT / 'resource-runtime-manifest.json')
    assert all(digest(ROOT / name) == sha for name, sha in manifest.items())
    protocol = read(PROTOCOL)
    # The host admission checks all current research/reporting dependencies.
    # Inside the package, the original runtime is immutable; reporting-only
    # tools may deliberately be older than those on the admission host.
    validate(protocol)
    for name, sha in {**protocol['source_overlays'], **protocol['evidence_hashes']}.items():
        assert digest(ROOT / name) == sha
    assert digest(ROOT / 'ai/strong/population-hybrid-development-plan-v1.json') == protocol['current_hybrid_plan_sha256']
    assert digest(ROOT / 'ai/strong/population-hybrid-development-protocol-v1.json') == protocol['current_hybrid_protocol_sha256']
    assert digest(ROOT / 'ai/strong/final-protocol-multiplayer.json') == protocol['final_protocol_sha256']
    assert source['base'] == protocol['base_source']
    plan = read(PLAN)
    assert plan['protocol_sha256'] == digest(PROTOCOL)
    assert plan['games'] == 64 and plan['samples'] == 8 and plan['search_workers'] == 1
    assert plan['workers'] == 8 and plan['game_max_steps'] == 1600 and plan['rollout_max_steps'] == 2400
    assert plan['cells'] == [{'players': n, 'arm': arm, 'games': 4 * n,
                              'replay_episodes': list(range(4 * (n - 1), 4 * n))}
                             for n in (2, 6) for arm in ('filter', 'resource-filter')]
    assert plan['new_strength_games'] == 0 and plan['reserved_final_seeds_used'] is False
    return source, protocol, plan


def command(protocol, plan, cell, model, output):
    return [sys.executable, '-u', str(ROOT / 'ai/strong/evaluate-resource-replanning-v1.py'),
            '--model', str(model), '--runtime', str(ROOT), '--arm', cell['arm'],
            '--players', str(cell['players']), '--opponent', 'search_geo',
            '--seed', protocol['smoke_seed_template'].format(players=cell['players']),
            '--start', '0', '--deals', '1', '--samples', str(plan['samples']),
            '--workers', str(plan['workers']), '--search-workers', str(plan['search_workers']),
            '--output', str(output)]


def expected(protocol, plan, cell):
    return {'arm': cell['arm'], 'players': cell['players'], 'opponent': 'search_geo',
            'seed': protocol['smoke_seed_template'].format(players=cell['players']),
            'start': 0, 'deals': 1, 'samples': plan['samples'], 'workers': plan['workers'],
            'search_workers': plan['search_workers'],
            'model_sha256': protocol['model_pin']['files']['inference64.onnx'],
            'opponent_model': None, 'opponent_sha256': None, 'runtime': str(ROOT)}


class MemorySampler:
    """Sample the process tree's summed RSS; shared pages can be counted twice."""
    def __init__(self):
        self.stop = threading.Event()
        self.peak = 0
        self.samples = 0
        self.thread = threading.Thread(target=self.run, daemon=True)

    def run(self):
        while not self.stop.is_set():
            pending, seen, rss = [os.getpid()], set(), 0
            while pending:
                pid = pending.pop()
                if pid in seen:
                    continue
                seen.add(pid)
                try:
                    status = Path(f'/proc/{pid}/status').read_text()
                    rss += int(next(line.split()[1] for line in status.splitlines() if line.startswith('VmRSS:'))) * 1024
                    pending.extend(map(int, Path(f'/proc/{pid}/task/{pid}/children').read_text().split()))
                except (FileNotFoundError, ProcessLookupError, PermissionError, StopIteration):
                    continue
            self.peak = max(self.peak, rss)
            self.samples += 1
            self.stop.wait(.1)


def replay_one(task):
    folder, episode, model_path = Path(task['folder']), task['episode'], Path(task['model'])
    report = read(folder / 'evaluation/evaluation.json')
    config = report['config']
    reference = next(row for row in report['results'] if row['episode'] == episode)
    receipt = folder / f'evaluation/decisions-{episode}.jsonl'
    assert digest(receipt) == reference['decision_receipt_sha256']
    model = Model(model_path, threads=1)
    assert model.sha256 == config['model_sha256']
    bridge = Node(str(ROOT / 'ai/strong/public-arena-bridge.cjs'))
    prepare = Node(str(ROOT / 'ai/strong/population-hybrid-policy.cjs'))
    start = time.perf_counter()
    count = resources = 0
    try:
        response = bridge.call({'op': 'reset', 'n': 1, 'offset': episode,
                                'arenaSeed': config['seed'], 'playerCount': config['players'],
                                'mode': 'search_geo', 'featureRevisions': {'learner': model_revision(model)}})
        with receipt.open() as stream:
            for line in stream:
                row = json.loads(line)
                observation = response['observations'][0]
                assert observation is not None and row['decision'] == count + 1
                assert observation['seat'] == reference['terminal']['seat']
                assert observation['round'] == row['round']
                request = observation['request']
                state = request['state']
                assert state['seed'] == 'secret' and state['powerPlantsDeck'] == []
                assert not state.get('hiddenLog') and 'powerPlantDeckAfterStep3' not in state
                if state['options']['fastBid']:
                    assert all(player['bid'] == 0 for player in state['players'])
                prepared = prepare.call({**request, 'op': 'prepare', 'featureRevision': model_revision(model)})
                assert prepared['observation']['state'] == observation['state']
                assert prepared['observation']['actions'] == observation['actions']
                assert prepared['moves'][row['index']] == row['move']
                assert model.predict(observation['state'], observation['actions'])[0] == row['modelProposal']
                if row.get('resourcePlan') is not None:
                    resources += 1
                    assert row['resourcePlan']['firstMove'] == row['move']
                    assert row['search']['seed'] == public_seed(prepared)
                response = bridge.call({'op': 'step', 'actions': [row['index']]})
                count += 1
        assert response['observations'] == [None] and len(response['ended']) == 1
        actual = response['ended'][0]
        terminal = reference['terminal']
        assert all(actual[key] == value for key, value in terminal.items() if key not in ('seat', 'win'))
        assert count == reference['decisions']
        if config['arm'] == 'resource-filter':
            assert resources > 0
        result = {'episode': episode, 'exact_terminal_replay': True, 'learner_decisions': count,
                  'resource_decisions': resources, 'all_model_proposals_exact': True,
                  'all_legal_moves_exact': True, 'all_public_inputs_checked': True,
                  'reference_receipt_sha256': digest(receipt), 'seconds': time.perf_counter() - start,
                  'qualification_eligible': False}
        write(folder / f'replay-{episode}.json', result)
        return result
    finally:
        bridge.close()
        prepare.close()


def run(source_path, model, check_layout=False):
    source, protocol, plan = validate_source(source_path, allow_unuploaded=check_layout)
    assert not os.environ.get('NODE_OPTIONS') and not os.environ.get('PG_TRACE_PATH')
    assert digest(model) == protocol['model_pin']['files']['inference64.onnx']
    if check_layout:
        assert model_revision(Model(model, threads=1)) == protocol['model_pin']['feature_revision']
        spec = importlib.util.spec_from_file_location('resource_arena_layout', ROOT / 'ai/strong/evaluate-resource-replanning-v1.py')
        arena = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(arena)
        assert arena.arena_module().PopulationPolicy.__name__ == 'ResourceReplanningPolicy'
        print(json.dumps({'layout_verified': True, 'games': 0, 'jobs': 0,
                          'commands': [command(protocol, plan, cell, model, OUT / str(i))
                                       for i, cell in enumerate(plan['cells'])]}))
        return
    OUT.mkdir(parents=True, exist_ok=False)
    processor = next(line.split(':', 1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines()
                     if line.startswith('model name'))
    status = {'stage': 'running', 'pid': os.getpid(), 'started_at': datetime.now(timezone.utc).isoformat(),
              'source': source, 'source_descriptor_sha256': digest(source_path),
              'protocol_sha256': digest(PROTOCOL), 'runtime_plan_sha256': digest(PLAN),
              'processor': processor, 'host': platform.node(), 'cpu_count': os.cpu_count(),
              'cells': {}, 'new_strength_games': 0, 'new_hf_jobs': 0, 'gradients': False,
              'automatic_retries': False, 'qualification_eligible': False, 'reserved_final_seeds_used': False}
    def save():
        status['updated_at'] = datetime.now(timezone.utc).isoformat()
        temporary = OUT / 'status.tmp.json'
        write(temporary, status)
        temporary.replace(OUT / 'status.json')
    save()
    try:
        for cell in plan['cells']:
            key = f"{cell['players']}p-{cell['arm']}"
            folder = OUT / key
            folder.mkdir()
            status.update(stage='evaluating', current_cell=key)
            save()
            sampler = MemorySampler()
            sampler.thread.start()
            cpu0, started = os.times(), time.perf_counter()
            try:
                with (folder / 'evaluation.log').open('x') as log:
                    with subprocess.Popen(command(protocol, plan, cell, model, folder / 'evaluation'),
                                          cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT) as child:
                        status['evaluation_pid'] = child.pid
                        save()
                        for line in child.stdout:
                            log.write(line)
                            log.flush()
                            print(key + ' ' + line, end='', flush=True)
                        if child.wait():
                            raise subprocess.CalledProcessError(child.returncode, child.args)
            finally:
                cpu1 = os.times()
                sampler.stop.set()
                sampler.thread.join()
                measured = {'seconds': time.perf_counter() - started,
                            'cpu_seconds': sum(cpu1[:4]) - sum(cpu0[:4]),
                            'sampled_peak_total_rss_bytes': sampler.peak, 'memory_samples': sampler.samples,
                            'memory_sampling_period_seconds': .1}
                write(folder / 'runtime.json', measured)
            summary = verify_evaluation(folder / 'evaluation', expected(protocol, plan, cell))
            assert summary['games'] == cell['games'] and not summary['counts'].get('rollout_caps', 0)
            write(folder / 'verified.json', summary)
            status['cells'][key] = {'complete': True, 'summary': summary, 'runtime': measured}
            save()
        status.update(stage='replaying', evaluation_pid=None)
        save()
        tasks = [{'folder': str(OUT / f"{cell['players']}p-{cell['arm']}"), 'episode': episode, 'model': str(model)}
                 for cell in plan['cells'] for episode in cell['replay_episodes']]
        replays = []
        with ProcessPoolExecutor(max_workers=4) as pool:
            futures = {pool.submit(replay_one, task): task for task in tasks}
            for future in as_completed(futures):
                replays.append(future.result())
                print(json.dumps({'replays_complete': len(replays), 'expected': len(tasks)}), flush=True)
        assert len(replays) == 16 and sum(row['summary']['games'] for row in status['cells'].values()) == 64
        validate_source(source_path)
        status.update(stage='complete', games=64, replays=16,
                      replayed_learner_decisions=sum(row['learner_decisions'] for row in replays),
                      replayed_resource_decisions=sum(row['resource_decisions'] for row in replays))
        save()
    except BaseException as error:
        status.update(stage='stopped_for_review', error=type(error).__name__ + ': ' + str(error))
        save()
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--model', type=Path, required=True)
    parser.add_argument('--check-layout', action='store_true')
    args = parser.parse_args()
    run(args.source.resolve(), args.model.resolve(), args.check_layout)
