"""Measure and preserve execution of the unchanged portable development job."""
import argparse
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

import public_policy_development_job_v1 as job

ENTRY = 'public_policy_measured_job_v1.py'


def follow_progress(path, stop):
    """Expose the existing evaluator log without changing its process or policy."""
    offset = 0
    while True:
        if path.exists():
            with path.open() as stream:
                stream.seek(offset)
                for line in stream:
                    print(json.dumps({'game_progress': line.rstrip()}), flush=True)
                offset = stream.tell()
        if stop.wait(.5):
            if path.exists():
                with path.open() as stream:
                    stream.seek(offset)
                    for line in stream: print(json.dumps({'game_progress': line.rstrip()}), flush=True)
            return


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--manifest-sha256', required=True)
    parser.add_argument('--protocol-sha256', required=True)
    parser.add_argument('--job', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source-revision', required=True)
    parser.add_argument('--source-archive-sha256', required=True)
    parser.add_argument('--scope', choices=['runtime', 'development'], required=True)
    parser.add_argument('--upload', action='store_true')
    args = parser.parse_args(); source = args.source.resolve(); output = args.output.resolve()
    child = argparse.Namespace(**{k: getattr(args, k) for k in ('source', 'manifest_sha256', 'job', 'source_revision', 'source_archive_sha256')},
                               output=output/'job', execute=True, upload=False)
    _, artifact, _, _, provenance = job.configuration(child)
    pins = job.read(source/job.MANIFEST)
    assert Path(__file__).resolve() == job.checked(source, ENTRY) and pins[ENTRY] == job.digest(__file__)
    protocol = job.checked(source, 'experiment-protocol.json')
    assert job.digest(protocol) == args.protocol_sha256
    assert args.scope == 'runtime' or 'runtime' not in provenance['shard']['name']
    output.mkdir(parents=True, exist_ok=False)
    sys.path.insert(0, str(artifact/'ai/strong'))
    spec = importlib.util.spec_from_file_location('frozen_memory_sampler', artifact/'ai/strong/surrogate-continuation-roots-job-v1.py')
    resources = importlib.util.module_from_spec(spec); spec.loader.exec_module(resources)
    state = {'stage': 'running', 'started_at': datetime.now(timezone.utc).isoformat(),
             'case': output.name, 'scope': args.scope, 'provenance': provenance,
             'experiment_protocol_sha256': args.protocol_sha256, 'measured_entry_sha256': job.digest(__file__),
             'gradient_updates': 0, 'qualified': False, 'reserved_final_seeds_used': False}
    job.write(output/'measurement.json', state)
    sampler = resources.MemorySampler(); sampler.thread.start()
    stop = threading.Event(); tail = threading.Thread(target=follow_progress, args=(output/'job/evaluation.log', stop), daemon=True)
    tail.start(); started, cpu0 = time.perf_counter(), os.times()
    command = [sys.executable, '-u', '-B', str(source/job.ENTRY), '--source', str(source),
               '--manifest-sha256', args.manifest_sha256, '--job', args.job, '--output', str(output/'job'),
               '--source-revision', args.source_revision, '--source-archive-sha256', args.source_archive_sha256, '--execute']
    try:
        with (output/'job.log').open('x') as log:
            with subprocess.Popen(command, cwd='/tmp', stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True) as process:
                for line in process.stdout:
                    log.write(line); log.flush(); print(line, end='', flush=True)
                if process.wait(): raise subprocess.CalledProcessError(process.returncode, command)
        assert job.configuration(child)[4] == provenance
        result = job.read(output/'job/job-status.json')
        assert result['stage'] == 'complete' and result['provenance'] == provenance
        state.update(stage='complete', games=result['games'], counts=result['counts'],
                     job_status_sha256=job.digest(output/'job/job-status.json'))
    except BaseException as error:
        state.update(stage='failed', failure_type=type(error).__name__); raise
    finally:
        stop.set(); tail.join(); sampler.stop.set(); sampler.thread.join(); cpu1 = os.times()
        state['measurement'] = {'seconds': time.perf_counter()-started, 'cpu_seconds': sum(cpu1[:4])-sum(cpu0[:4]),
            'sampled_peak_total_rss_bytes': sampler.peak, 'memory_samples': sampler.samples,
            'memory_sampling_period_seconds': .2, 'includes_startup_and_validation': True}
        job.write(output/'measurement.json', state)
        job.write(output/'manifest.json', {str(p.relative_to(output)): job.digest(p)
                  for p in sorted(output.rglob('*')) if p.is_file()})
        if args.upload:
            with output.with_suffix('.upload-intent.json').open('x') as stream:
                json.dump({'case': output.name, 'manifest_sha256': job.digest(output/'manifest.json')}, stream)
            from policy_iteration_evidence_archive import upload_evidence
            evidence = upload_evidence(output)
            print(json.dumps({'case': output.name, 'status': state, 'evidence': evidence}), flush=True)
        else:
            print(json.dumps(state), flush=True)


if __name__ == '__main__': main()
