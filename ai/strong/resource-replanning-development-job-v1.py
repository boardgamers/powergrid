"""Execute one fixed resource-policy shard; submission requires separate admission."""
import argparse
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import time

from huggingface_hub import hf_hub_download
from strategic_collection import ROOT, read, write, digest
from resource_development_v1 import PROTOCOL, validate
from resource_policy_verification_v1 import verify_evaluation
from policy_iteration_evidence_archive import upload_evidence


def contract(protocol, arm, players, opponent, start, end, runtime_pilot=False):
    validate(protocol)
    assert arm in protocol['arms'] and type(players) is int and players in range(2, 7)
    matches = [cell for cell in protocol['screens'] if cell['players'] == players and cell['opponent'] == opponent]
    assert len(matches) == 1
    cell = matches[0]
    assert type(start) is type(end) is int and 0 <= start < end <= 4
    assert end - start in (1, 2, 4) and start % (end - start) == 0
    assert type(runtime_pilot) is bool
    if runtime_pilot:
        assert players in (2, 6) and arm == 'resource-filter' and opponent == 'search_geo'
        assert (start, end) == (0, 1)
        key = f'resource-replanning-hf-runtime-v1-{players}p-resource-filter'
        seed = protocol['smoke_seed_template'].format(players=players)
    else:
        key = f'resource-replanning-development-v1-{arm}-{players}p-{opponent}-{start}-{end}'
        seed = protocol['seed_template'].format(players=players)
    expected = {'arm': arm, 'players': players, 'opponent': opponent, 'start': start, 'deals': end - start,
                'seed': seed, 'model_sha256': protocol['model_pin']['files']['inference64.onnx'],
                'opponent_sha256': cell.get('sha256'), 'samples': 8, 'workers': 8, 'search_workers': 1,
                'runtime': str(ROOT)}
    if opponent != 'a260':
        expected['opponent_model'] = None
    return key, cell, expected


def run(arm, players, opponent, start, end, runtime_pilot=False):
    protocol = read(PROTOCOL)
    key, cell, expected = contract(protocol, arm, players, opponent, start, end, runtime_pilot)
    assert digest(PROTOCOL) == os.environ['PROTOCOL_SHA256']
    assert not os.environ.get('NODE_OPTIONS') and not os.environ.get('PG_TRACE_PATH')
    for name, sha in protocol['source_overlays'].items():
        assert digest(ROOT / name) == sha
    source_revision, source_sha = os.environ['SOURCE_REVISION'], os.environ['SOURCE_SHA256']
    # Reuse only the pinned passive sampler, not the local pilot's execution loop.
    sampler_path = ROOT / 'ai/strong/resource-replanning-runtime-pilot-v1.py'
    spec = importlib.util.spec_from_file_location('resource_runtime_sampler', sampler_path)
    runtime = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runtime)
    out = ROOT / 'ai/runs' / key
    out.mkdir(parents=True, exist_ok=False)
    status = {'case': key, 'stage': 'running', 'source_revision': source_revision, 'source_sha256': source_sha,
              'protocol_sha256': digest(PROTOCOL), 'model_pin': protocol['model_pin'],
              'runtime_pilot': runtime_pilot, 'expected_config': expected,
              'job_runner_sha256': digest(__file__), 'sampler_sha256': digest(sampler_path),
              'automatic_retries': False, 'gradients': False,
              'qualification_eligible': False, 'reserved_final_seeds_used': False}
    began, sampler = time.perf_counter(), None
    try:
        pin = protocol['model_pin']
        model = hf_hub_download(pin['repo'], pin['prefix'] + '/inference64.onnx', revision=pin['revision'])
        assert digest(model) == expected['model_sha256']
        command = [sys.executable, '-u', 'ai/strong/evaluate-resource-replanning-v1.py',
                   '--model', model, '--runtime', str(ROOT), '--arm', arm, '--players', str(players),
                   '--opponent', opponent, '--seed', expected['seed'], '--start', str(start),
                   '--deals', str(end - start), '--samples', '8', '--workers', '8', '--search-workers', '1',
                   '--output', str(out / 'evaluation')]
        if opponent == 'a260':
            other = hf_hub_download(pin['repo'], cell['model_path'], revision=cell['revision'])
            assert digest(other) == cell['sha256']
            command += ['--opponent-model', other]
        sampler = runtime.MemorySampler()
        sampler.thread.start()
        cpu0, evaluation_start = os.times(), time.perf_counter()
        try:
            with (out / 'evaluation.log').open('x') as log:
                with subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True) as child:
                    for line in child.stdout:
                        log.write(line)
                        log.flush()
                        print(line, end='', flush=True)
                    if child.wait():
                        raise subprocess.CalledProcessError(child.returncode, command)
        finally:
            cpu1 = os.times()
            sampler.stop.set()
            sampler.thread.join()
            measured = {'seconds': time.perf_counter() - evaluation_start,
                        'cpu_seconds': sum(cpu1[:4]) - sum(cpu0[:4]),
                        'sampled_peak_total_rss_bytes': sampler.peak, 'memory_samples': sampler.samples,
                        'memory_sampling_period_seconds': .1}
            write(out / 'runtime.json', measured)
        summary = verify_evaluation(out / 'evaluation', {**expected, 'output': str(out / 'evaluation')})
        assert summary['games'] == (end - start) * 4 * players
        write(out / 'summary.json', summary)
        status.update(stage='complete', games=summary['games'], runtime=measured)
    except BaseException as error:
        status.update(stage='failed', error=type(error).__name__ + ': ' + str(error))
        raise
    finally:
        if sampler is not None and sampler.thread.is_alive():
            sampler.stop.set()
            sampler.thread.join()
        status['seconds'] = time.perf_counter() - began
        write(out / 'resource-check.json', status)
        write(out / 'manifest.json', {str(path.relative_to(out)): digest(path)
                                     for path in sorted(out.rglob('*')) if path.is_file()})
        evidence = upload_evidence(out)
        print({'status': status, 'evidence': evidence}, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('arm')
    parser.add_argument('players', type=int)
    parser.add_argument('opponent')
    parser.add_argument('start', type=int)
    parser.add_argument('end', type=int)
    parser.add_argument('--runtime-pilot', action='store_true')
    args = parser.parse_args()
    run(args.arm, args.players, args.opponent, args.start, args.end, args.runtime_pilot)
