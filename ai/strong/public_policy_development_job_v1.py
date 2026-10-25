"""Portable HF development job around an unchanged standalone policy artifact.

The source bundle pins the artifact, controls and this external wrapper. Default
execution validates only. This entry point cannot admit reserved/final games or
select a candidate. An interrupted run retains its exclusive output directory.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time


MANIFEST = 'source-manifest.json'
ENTRY = 'public_policy_development_job_v1.py'


def require(value, message):
    if not value:
        raise ValueError(message)


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def checked(root, name, directory=False):
    require(isinstance(name, str) and name and not Path(name).is_absolute(), 'Expected relative source path')
    require(all(part not in ('.', '..') for part in name.split('/')), 'Noncanonical source path')
    target = root/name
    require(target.resolve().is_relative_to(root), 'Source path escapes bundle')
    require(not any(p.is_symlink() for p in (target, *target.parents) if p != root.parent), 'Symlink in source path')
    require(target.is_dir() if directory else target.is_file(), 'Missing source path: '+name)
    return target


def configuration(args):
    root = args.source.resolve()
    require(re.fullmatch('[a-f0-9]{64}', args.manifest_sha256) is not None, 'Invalid source manifest pin')
    manifest = checked(root, MANIFEST)
    require(digest(manifest) == args.manifest_sha256, 'Source manifest changed')
    pins = read(manifest)
    require(isinstance(pins, dict) and pins and MANIFEST not in pins, 'Invalid source manifest')
    actual = {str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()}
    require(actual == set(pins)|{MANIFEST}, 'Source file set changed')
    for name, sha in pins.items():
        require(isinstance(sha, str) and re.fullmatch('[a-f0-9]{64}', sha) is not None, 'Invalid source file pin')
        require(digest(checked(root, name)) == sha, 'Source bytes changed: '+name)
    require(Path(__file__).resolve() == checked(root, ENTRY), 'Execute the pinned bundle entry point')
    spec = read(checked(root, args.job))
    require(set(spec) == {'version', 'artifact', 'descriptor', 'candidate', 'contract', 'workers', 'opponent_model'},
            'Unexpected job specification')
    require(type(spec['version']) is int and spec['version'] == 1, 'Unsupported job specification')
    require(type(spec['workers']) is int and 1 <= spec['workers'] <= 32, 'Invalid game concurrency')
    artifact = checked(root, spec['artifact'], directory=True)
    checked(artifact, spec['descriptor'])
    candidate_path, contract_path = (checked(root, spec[key]) for key in ('candidate', 'contract'))
    candidate, contract = read(candidate_path), read(contract_path)
    require(contract['purpose'] == 'engineering' and candidate['status'] == 'engineering'
            and candidate['selection_evidence'] is None and contract['launch_authorization'] is None,
            'This job admits development execution only; final games require separate admission')
    require(digest(candidate_path) == contract['candidate_sha256'], 'Candidate bytes changed')
    require(candidate['identity'] == contract['identity'], 'Policy identity mismatch')
    output = args.output.resolve()
    require(not output.is_relative_to(root) and not root.is_relative_to(output), 'Outputs must be outside the frozen source')
    runner = checked(artifact, 'ai/strong/public_policy_final_runner_v1.py')
    command = [sys.executable, '-u', '-B', str(runner), '--artifact', str(artifact),
               '--descriptor', spec['descriptor'], '--candidate', str(candidate_path),
               '--contract', str(contract_path), '--workers', str(spec['workers']),
               '--output', str(output/'evaluation')]
    if spec['opponent_model'] is not None:
        command += ['--opponent-model', str(checked(root, spec['opponent_model']))]
    provenance = {'source_manifest_sha256': args.manifest_sha256, 'job_spec_sha256': digest(root/args.job),
                  'entry_sha256': digest(root/ENTRY), 'candidate_sha256': digest(candidate_path),
                  'contract_sha256': digest(contract_path), 'identity': candidate['identity'],
                  'shard': contract['shard'], 'source_revision': args.source_revision,
                  'source_archive_sha256': args.source_archive_sha256}
    if args.source_revision is not None or args.source_archive_sha256 is not None or args.upload:
        require(isinstance(args.source_revision, str) and re.fullmatch('[a-f0-9]{40}', args.source_revision) is not None,
                'Missing immutable source revision')
        require(isinstance(args.source_archive_sha256, str)
                and re.fullmatch('[a-f0-9]{64}', args.source_archive_sha256) is not None, 'Missing source archive hash')
    require(not args.upload or args.execute, 'Validation-only mode cannot upload game evidence')
    return root, artifact, output, command, provenance


def run(args):
    root, artifact, output, command, provenance = configuration(args)
    # The frozen runner checks the real manifest, full identity, exact paired deal
    # and controls before this wrapper creates any execution directory.
    subprocess.run(command, cwd=artifact, check=True)
    if not args.execute:
        print(json.dumps({'valid_job': True, 'execute': False, 'provenance': provenance}), flush=True)
        return
    require(configuration(args)[4] == provenance, 'Source changed during admission')
    output.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(root/MANIFEST, output/MANIFEST)
    shutil.copyfile(root/args.job, output/'job-spec.json')
    started = time.perf_counter()
    status = {'stage': 'running', 'started_at': datetime.now(timezone.utc).isoformat(),
              'provenance': provenance, 'qualified': False, 'reserved_final_seeds_used': False,
              'gradient_updates': 0, 'automatic_retries': False}
    write(output/'job-status.json', status)
    try:
        with (output/'evaluation.log').open('x') as log:
            subprocess.run([*command, '--execute'], cwd=artifact, stdout=log, stderr=subprocess.STDOUT, check=True)
        require(configuration(args)[4] == provenance, 'Source changed during execution')
        report = read(output/'evaluation/evaluation.json')
        audit = read(output/'evaluation/audit.json')
        require(report['passed'] and report['all_complete'] and not report['errors'], 'Incomplete games')
        require(report['completed_games'] == provenance['shard']['games'], 'Wrong game count')
        require(not report['game_caps'] and not report['rollout_caps'], 'Capped execution')
        binding = audit['execution_binding']
        require(binding == report['execution_binding'] and binding['identity'] == provenance['identity']
                and binding['candidate_sha256'] == provenance['candidate_sha256']
                and binding['contract_sha256'] == provenance['contract_sha256']
                and binding['shard'] == provenance['shard'] and binding['reserved'] is False,
                'Execution binding changed')
        status.update(stage='complete', games=report['completed_games'], counts=audit['counts'],
                      evaluation_sha256=digest(output/'evaluation/evaluation.json'),
                      audit_sha256=digest(output/'evaluation/audit.json'))
    except BaseException as error:
        status.update(stage='failed', failure_type=type(error).__name__)
        raise
    finally:
        status['seconds'] = time.perf_counter()-started
        write(output/'job-status.json', status)
        write(output/'manifest.json', {str(p.relative_to(output)): digest(p)
              for p in sorted(output.rglob('*')) if p.is_file()})
        if args.upload:
            # Persist upload intent outside the sealed evidence directory. An
            # ambiguous upload must be reconciled, never execute games again.
            receipt = output.with_suffix('.upload.json')
            with receipt.open('x') as stream:
                json.dump({'stage': 'upload_intent', 'evidence_manifest_sha256': digest(output/'manifest.json')}, stream)
            sys.path.insert(0, str(artifact/'ai/strong'))
            from policy_iteration_evidence_archive import upload_evidence
            evidence = upload_evidence(output)
            write(receipt, {'stage': 'uploaded', 'evidence': evidence})
            print(json.dumps({'evidence': evidence}), flush=True)
        print(json.dumps(status), flush=True)


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--manifest-sha256', required=True)
    parser.add_argument('--job', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source-revision')
    parser.add_argument('--source-archive-sha256')
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--upload', action='store_true')
    run(parser.parse_args())


if __name__ == '__main__':
    main()
