"""Profile one existing trained hybrid fixture; no new games, jobs or gradients.

Compare one and four ORT threads in ABBA order. Instrumentation is process-local;
the frozen engine and the active development pipeline are never edited.
"""
import argparse
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import platform
import time

import hybrid_search as hybrid

ROOT = Path(__file__).resolve().parents[2]


def read(path):
    return json.loads(Path(path).read_text())


def write(path, data):
    Path(path).write_text(json.dumps(data, indent=2)+'\n')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@contextmanager
def measured(model):
    original_predict, original_pool, original_node = hybrid.predict_batch, hybrid.EnginePool, hybrid.Node
    original_session = model.session
    trace = hashlib.sha256()
    stats = {k: 0 for k in ['policy_seconds', 'onnx_seconds', 'engine_ipc_json_seconds',
        'prepare_seconds', 'pool_start_seconds', 'policy_calls', 'policy_rows',
        'onnx_calls', 'onnx_rows', 'legal_action_slots', 'padded_action_slots']}

    class Session:
        def __getattr__(self, name):
            return getattr(original_session, name)

        def run(self, outputs, inputs):
            started = time.perf_counter()
            result = original_session.run(outputs, inputs)
            stats['onnx_seconds'] += time.perf_counter() - started
            stats['onnx_calls'] += 1
            stats['onnx_rows'] += inputs['mask'].shape[0]
            stats['legal_action_slots'] += int(inputs['mask'].sum())
            stats['padded_action_slots'] += int(inputs['mask'].size)
            return result

    def predict(model, rows, batch_size=64):
        started = time.perf_counter()
        choices = original_predict(model, rows, batch_size)
        stats['policy_seconds'] += time.perf_counter() - started
        stats['policy_calls'] += 1
        stats['policy_rows'] += len(rows)
        trace.update(json.dumps(choices, separators=(',', ':')).encode() + b'\n')
        return choices

    class Pool(original_pool):
        def __init__(self, *args, **kwargs):
            started = time.perf_counter()
            super().__init__(*args, **kwargs)
            stats['pool_start_seconds'] += time.perf_counter() - started

        def call(self, request):
            started = time.perf_counter()
            result = super().call(request)
            stats['engine_ipc_json_seconds'] += time.perf_counter() - started
            return result

    class Node(original_node):
        def call(self, request):
            started = time.perf_counter()
            result = super().call(request)
            stats['prepare_seconds'] += time.perf_counter() - started
            return result

    model.session = Session()
    hybrid.predict_batch, hybrid.EnginePool, hybrid.Node = predict, Pool, Node
    try:
        yield stats
    finally:
        model.session = original_session
        hybrid.predict_batch, hybrid.EnginePool, hybrid.Node = original_predict, original_pool, original_node
        stats['choice_transcript_sha256'] = trace.hexdigest()


def comparable(result):
    return {k: v for k, v in result.items() if k != 'elapsedMs'}


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--require-cpu', help='Reject a benchmark on an unintended CPU before running it')
    args = parser.parse_args()
    processor = next(line.split(':', 1)[1].strip() for line in
        Path('/proc/cpuinfo').read_text().splitlines() if line.startswith('model name'))
    if args.require_cpu:
        assert args.require_cpu in processor, (args.require_cpu, processor)
    previous = ROOT/'ai/runs/trained-hybrid-probe-v2'
    probe = read(previous/'assessment.json')
    assert probe['contracts_passed'] and probe['all_searches_usable']
    runtime = previous/'runtime'
    hashes = {ROOT/name: sha for name, sha in probe['code_hashes'].items()}
    hashes.update({runtime/name: sha for name, sha in probe['frozen_runtime_hashes'].items()})
    hashes[runtime/'ai/strong/hybrid-continuations.cjs'] = digest(ROOT/'ai/strong/hybrid-continuations.cjs')
    hashes[Path(__file__)] = digest(Path(__file__))
    assert all(digest(p) == sha for p, sha in hashes.items())
    hybrid.WORKER = str(runtime/'ai/strong/hybrid-continuations.cjs')
    prepared = ROOT/'ai/runs/policy-iteration-trained-8840u-prepared-v2'
    manifest = read(prepared/'manifest.json')
    assert digest(prepared/'manifest.json') == probe['trained_manifest_sha256']
    key, cell = 'public-0', '6p-building'
    model_path = prepared/('local-package-'+key)/'policy.onnx'
    assert digest(model_path) == probe['models'][key] == manifest['models'][key]['pin']['files']['inference64.onnx']
    selected = read(previous/'selected-fixtures.json')[cell]
    reference = next(r['result'] for r in probe['search_checks'] if r['model'] == key
        and r['players'] == 6 and r['phase'] == 'building' and r['samples_per_mode'] == 8)
    assert selected['fixture_index'] == probe['selected_fixtures'][cell]
    args.output.mkdir(parents=True, exist_ok=False)
    write(args.output/'fixture.json', selected)
    report = {'passed': False, 'model': key, 'model_sha256': digest(model_path),
        'fixture_index': selected['fixture_index'], 'fixture_sha256': digest(args.output/'fixture.json'),
        'source_probe_sha256': digest(previous/'assessment.json'),
        'trained_manifest_sha256': digest(prepared/'manifest.json'),
        'source_probe_archive': read(ROOT/'ai/strong/trained-hybrid-probe-evidence-v2.json'),
        'code_hashes': {str(p.relative_to(ROOT)): sha for p, sha in hashes.items()},
        'host': platform.node(), 'processor': processor, 'required_cpu': args.require_cpu,
        'thread_order': [1, 4, 4, 1], 'workers': 4, 'samples_per_mode': 8, 'max_steps': 2400,
        'records': [], 'gradients': False, 'hf_jobs_submitted': 0, 'candidate_selected': False,
        'qualification_eligible': False, 'reserved_final_seeds_used': False,
        'scope': 'Repeated existing six-player Recharged/sealed building fixture on the recorded CPU host. '
            'No fresh strength, representative latency distribution or default thread change. '
            'Policy time includes ONNX; engine time includes IPC, JSON and simulator work.'}
    transcript = None
    try:
        for threads in report['thread_order']:
            load_started = time.perf_counter()
            model = hybrid.Model(model_path, threads=threads)
            load_seconds = time.perf_counter() - load_started
            with measured(model) as stats:
                with hybrid.HybridSearch(model, samples=8, workers=4) as search:
                    result = search.choose(selected['fixture']['request'])
            assert comparable(result) == comparable(reference)
            assert result['search']['truncated'] == 0
            if transcript is not None:
                assert stats['choice_transcript_sha256'] == transcript, 'An internal policy decision changed'
            transcript = stats['choice_transcript_sha256']
            stats['policy_preparation_seconds'] = stats['policy_seconds'] - stats['onnx_seconds']
            stats['other_seconds'] = result['elapsedMs']/1000 - sum(stats[k] for k in
                ['policy_seconds', 'engine_ipc_json_seconds', 'prepare_seconds', 'pool_start_seconds'])
            assert stats['other_seconds'] >= 0 and stats['policy_preparation_seconds'] >= 0
            record = {'threads': threads, 'model_load_seconds': load_seconds, 'stats': stats, 'result': result}
            report['records'].append(record)
            write(args.output/'profile.json', report)
            print({'threads': threads, 'elapsed_seconds': result['elapsedMs']/1000, **stats}, flush=True)
            del model
        assert all(digest(p) == sha for p, sha in hashes.items())
        report['passed'] = True
        report['all_internal_choices_and_terminal_outcomes_identical'] = True
    finally:
        write(args.output/'profile.json', report)
    print({'passed': report['passed'], 'runs': len(report['records'])}, flush=True)


if __name__ == '__main__':
    main()
