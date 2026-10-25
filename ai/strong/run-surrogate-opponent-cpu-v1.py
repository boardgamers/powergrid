"""Offline target-CPU component benchmark against the original HF receipts.

Uses the exact frozen selected-cost runner, 24 existing runtime roots and learned
opponent ensemble. No fresh scientific roots, training, model selection or jobs.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')


def run(package, output, required_cpu):
    sys.path.insert(0, str(package/'ai/strong'))
    from strategic_collection import digest
    import surrogate_continuation_selected_cost_v1 as cost
    from surrogate_continuation_job_v1 import source_check, validate_inputs, MEMBERS
    from surrogate_continuation_study_v1 import policy_digest
    from hybrid_search import Model
    from opponent_surrogate_policy_v1 import SurrogatePolicy
    import numpy, onnxruntime, huggingface_hub

    manifest = read(package/'benchmark-manifest.json')
    assert Path(__file__).resolve() == package/'benchmark.py'
    assert all(digest(package/name) == sha for name, sha in manifest['files'].items())
    assert not os.environ.get('NODE_OPTIONS')
    os.environ['PG_REFERENCE_RUNTIME'] = str(package)
    source_hashes = source_check()
    roots = cost.runtime_roots(); _, _, _, selected = validate_inputs()
    assert policy_digest(selected) == manifest['surrogate_policy_sha256']
    assert len(roots) == 24 and all(r['identity']['mode'] == 'runtime' for r in roots.values())
    reference = cost.verify(package/'hf-reference', roots, policy_digest(selected))
    assert reference['complete'] and reference['continuations'] == 384 and reference['caps'] == 0
    processor = next(line.split(':', 1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines()
                     if line.startswith('model name'))
    assert required_cpu and required_cpu in processor
    output.mkdir(parents=True, exist_ok=False)
    state = {'stage': 'running', 'pid': os.getpid(), 'started_at': datetime.now(timezone.utc).isoformat(),
        'host': platform.node(), 'processor': processor, 'required_cpu': required_cpu,
        'python': platform.python_version(), 'numpy': numpy.__version__, 'onnxruntime': onnxruntime.__version__,
        'huggingface_hub': huggingface_hub.__version__,
        'node': subprocess.check_output(['node', '--version'], text=True).strip(),
        'manifest_sha256': digest(package/'benchmark-manifest.json'), 'runner_sha256': digest(__file__),
        'source_manifest_sha256': manifest['source']['manifest_sha256'],
        'surrogate_policy_sha256': policy_digest(selected), 'workers': 8, 'inference_threads': 1,
        'gradients': False, 'qualification_eligible': False, 'reserved_final_seeds_used': False,
        'new_hf_jobs': 0, 'fresh_scientific_continuations': 0,
        'scope': '24 existing two/six-player runtime positions, all rules and plant/bid/building phases, two fixed actions and eight worlds. Learned-opponent continuation component only; not whole-hybrid latency, representative gameplay timing or playing strength.'}
    write(output/'status.json', state); started = time.perf_counter()
    try:
        before = time.perf_counter(); focal = Model(package/'focal.onnx', threads=1)
        state['focal_load_ms'] = 1000*(time.perf_counter()-before)
        assert focal.sha256 == manifest['focal_model_sha256']
        before = time.perf_counter(); surrogate = SurrogatePolicy(selected, MEMBERS, threads=1)
        state['surrogate_ensemble_load_ms'] = 1000*(time.perf_counter()-before)
        write(output/'status.json', state)
        cost.execute(roots, focal, surrogate, output/'continuations', scope='local_engineering_fixture',
            provenance={'kind': 'actual-8840u-component-benchmark', 'manifest_sha256': state['manifest_sha256'],
                        'hf_reference_evidence': manifest['hf_reference_evidence']})
        checked = cost.verify(output/'continuations', roots, policy_digest(selected))
        assert checked['complete'] and checked['caps'] == 0
        cases = {}
        for key in sorted(roots):
            actual = read(output/'continuations'/key/'result.json')
            expected = read(package/'hf-reference'/key/'result.json')
            # Only a top-level wall time differs. Compare every sampled world,
            # initial bid, inference count, terminal and credit without rounding.
            assert {k: v for k, v in actual.items() if k != 'seconds'} == {
                k: v for k, v in expected.items() if k != 'seconds'}, 'HF/8840U continuation differs: '+key
            cases[key] = {'exact': True, 'continuations': len(actual['rows']),
                          'result_sha256': digest(output/'continuations'/key/'result.json'),
                          'reference_sha256': digest(package/'hf-reference'/key/'result.json'),
                          'inference_decisions': actual['inference_decisions']}
        assert source_hashes == source_check()
        assert all(digest(package/name) == sha for name, sha in manifest['files'].items())
        write(output/'comparison.json', cases)
        state.update(stage='completed', passed=True, roots=24, continuations=384, caps=0,
                     full_continuation_receipts_exact=True, measurements=checked['measurements'])
    except BaseException as error:
        state.update(stage='failed', passed=False, error=type(error).__name__+': '+str(error))
        raise
    finally:
        state.update(seconds=time.perf_counter()-started, finished_at=datetime.now(timezone.utc).isoformat())
        state['output_hashes'] = {str(p.relative_to(output)): digest(p) for p in output.rglob('*')
                                  if p.is_file() and p != output/'status.json'}
        write(output/'status.json', state)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--package', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--require-cpu', required=True)
    args = parser.parse_args(); run(args.package.resolve(), args.output.resolve(), args.require_cpu)
