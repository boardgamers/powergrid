"""Profile a fixed resource root with JSON-equivalent comparison and preserved output."""
import argparse
from collections import Counter
from contextlib import contextmanager
import cProfile
from datetime import datetime, timezone
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import platform
import pstats
import subprocess
import sys
import time


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def semantic(row):
    # JSON object keys are strings; preserve that wire format on both sides.
    row = json.loads(json.dumps(row, allow_nan=False))
    result = {key: value for key, value in row.items() if key not in ('decision', 'round', 'elapsedMs')}
    result['resourcePlan'] = {key: value for key, value in result['resourcePlan'].items() if key != 'elapsedMs'}
    return result


class TimedSession:
    def __init__(self, session):
        self.session, self.seconds, self.calls = session, 0., 0

    def __getattr__(self, name):
        return getattr(self.session, name)

    def run(self, *args, **kwargs):
        began = time.perf_counter()
        result = self.session.run(*args, **kwargs)
        self.seconds += time.perf_counter() - began
        self.calls += 1
        return result


@contextmanager
def profile_nodes(directory):
    from hybrid_search import Node, EnginePool
    original_popen, original_node_close, original_pool_close = subprocess.Popen, Node.close, EnginePool.close
    children = []
    def spawn(command, *args, **kwargs):
        assert command[0] == 'node', 'Only expected Node workers may be profiled'
        child = original_popen([command[0], '--cpu-prof', '--cpu-prof-dir=' + str(directory), *command[1:]], *args, **kwargs)
        children.append({'pid': child.pid, 'command': command, 'process': child})
        return child
    def finish(child):
        # Graceful EOF lets V8 write profiles; all policy computation is finished.
        child.stdin.close()
        assert child.wait(timeout=15) == 0
        child.stdout.close()
    def node_close(self):
        finish(self.proc)
    def pool_close(self):
        for child in self.processes:
            finish(child)
        self.executor.shutdown()
    subprocess.Popen, Node.close, EnginePool.close = spawn, node_close, pool_close
    try:
        yield children
    finally:
        subprocess.Popen, Node.close, EnginePool.close = original_popen, original_node_close, original_pool_close
        for child in children:
            proc = child['process']
            if proc.poll() is None:
                proc.terminate()
                proc.wait(timeout=15)


def summarize_v8(path):
    profile = read(path)
    nodes = {row['id']: row['callFrame'] for row in profile['nodes']}
    samples = profile['samples']
    assert len(samples) == len(profile['timeDeltas'])
    weighted, counts = Counter(), Counter()
    for node, delta in zip(samples, profile['timeDeltas']):
        frame = nodes[node]
        key = (frame['functionName'], frame['url'], frame['lineNumber'])
        weighted[key] += delta
        counts[key] += 1
    functions = [{'function': key[0], 'url': key[1], 'line_zero_based': key[2],
                  'sample_weight_seconds': value / 1e6, 'samples': counts[key]}
                 for key, value in weighted.most_common()]
    return {'file': path.name, 'sha256': digest(path), 'total_samples': len(samples),
            'sampled_duration_seconds': sum(profile['timeDeltas']) / 1e6, 'functions': functions,
            'scope': 'Sampled V8 self time, including startup/idle/GC. Weights are sampling intervals, not exact CPU accounting.'}


def run(package, output):
    manifest = read(package / 'manifest.json')
    assert all(digest(package / name) == sha for name, sha in manifest['files'].items())
    selected = read(package / 'slow-roots.json')
    case = '2p-original-open-economic'
    entry = selected[case]
    assert manifest['samples'] == 4 and manifest['max_steps'] == 2400
    output.mkdir(parents=True, exist_ok=False)
    sys.path.insert(0, str(package / 'ai/strong'))
    from hybrid_search import Model
    from resource_replanning_policy_v1 import ResourceReplanningPolicy
    spec = importlib.util.spec_from_file_location('existing_resource_benchmark', package / 'benchmark.py')
    benchmark = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(benchmark)
    status = {'stage': 'running', 'started_at': datetime.now(timezone.utc).isoformat(),
              'case': case, 'host': platform.node(), 'manifest_sha256': digest(package / 'manifest.json'),
              'runner_sha256': digest(__file__), 'threads': 1, 'workers': 1, 'samples': 4,
              'new_arena_games': 0, 'new_hf_jobs': 0, 'gradients': False,
              'qualification_eligible': False, 'reserved_final_seeds_used': False}
    write(output / 'status.json', status)
    policy, profiler = None, cProfile.Profile()
    try:
        model = Model(package / 'policy.onnx', threads=1)
        assert model.sha256 == manifest['model_sha256']
        timed = TimedSession(model.session)
        model.session = timed
        with profile_nodes(output) as children:
            policy = ResourceReplanningPolicy(model, package / 'ai/strong/population-hybrid-policy.cjs',
                arm='resource-filter', samples=4, workers=1, max_steps=2400)
            with benchmark.observe() as timing:
                began = time.perf_counter()
                profiler.enable()
                result = policy.choose(entry['request'])
                profiler.disable()
                elapsed = time.perf_counter() - began
            write(output / 'result.json', result)
            assert semantic(result) == semantic(entry['reference'])
            assert result['search']['usable'] and result['search']['truncated'] == 0
            policy.close()
            policy = None
            process_records = [{key: value for key, value in row.items() if key != 'process'} for row in children]
        profiler.dump_stats(output / 'python.pstats')
        stream = io.StringIO()
        pstats.Stats(profiler, stream=stream).sort_stats('tottime').print_stats(60)
        (output / 'python-self-time.txt').write_text(stream.getvalue())
        stream = io.StringIO()
        pstats.Stats(profiler, stream=stream).sort_stats('cumulative').print_stats(60)
        (output / 'python-cumulative-time.txt').write_text(stream.getvalue())
        profiles = [summarize_v8(path) for path in sorted(output.glob('*.cpuprofile'))]
        assert len(profiles) == len(process_records) == 3
        write(output / 'result.json', result)
        write(output / 'v8-summary.json', profiles)
        assert all(digest(package / name) == sha for name, sha in manifest['files'].items())
        status.update(stage='complete', exact_recorded_result=True, rollouts=result['search']['evaluations'],
            neural_decisions=result['search']['neuralDecisions'], wall_seconds=elapsed,
            outer_call_timing=timing, onnx_run_seconds=timed.seconds, onnx_run_calls=timed.calls,
            node_processes=process_records, v8_profiles=len(profiles),
            limitations='One already-selected four-world stress root on the shared local HX370, under profiling overhead. Not representative serving latency, a new strength sample, or an AMD8840U benchmark.')
    except BaseException as error:
        status.update(stage='failed', error=type(error).__name__ + ': ' + str(error))
        raise
    finally:
        profiler.disable()
        if policy is not None:
            policy.close()
        status['finished_at'] = datetime.now(timezone.utc).isoformat()
        status['output_hashes'] = {path.name: digest(path) for path in output.iterdir() if path.is_file() and path.name != 'status.json'}
        write(output / 'status.json', status)
    print(json.dumps({key: status[key] for key in ('stage', 'exact_recorded_result', 'rollouts', 'neural_decisions',
        'wall_seconds', 'onnx_run_seconds', 'onnx_run_calls', 'outer_call_timing', 'v8_profiles')}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--package', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.package.resolve(), args.output.resolve())
