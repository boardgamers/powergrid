"""Assemble portable final-job controls without selecting or executing a policy.

This is an offline source builder, not launch admission. Its caller must supply
the separately frozen candidate and game-worker allocation. Source publication
and dispatch still require complete confirmation, selection and technical proof.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

from public_policy_final_audit_v1 import (
    PROTOCOL_SHA, artifact_identity, digest, read, require, same, schedule,
)
from public_policy_final_contract_v1 import admit, fingerprint, timestamp
from public_policy_runtime_v1 import checked_path

ROOT = Path(__file__).resolve().parents[2]
ENTRY = 'public_policy_selected_final_job_v1.py'
OPPONENT = 'final-opponent-a260.onnx'


def save(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def controls(candidate_bytes, identity, descriptor, workers, created_at):
    """Serialize every unchanged reserved shard; never instantiate a game."""
    candidate = json.loads(candidate_bytes)
    candidate_sha = hashlib.sha256(candidate_bytes).hexdigest()
    require(candidate['status'] == 'selected', 'A separately selected candidate is required')
    require(same(candidate['identity'], identity), 'Complete policy identity differs')
    timestamp(created_at)
    require(isinstance(descriptor, str) and descriptor and not Path(descriptor).is_absolute()
            and all(part not in ('', '.', '..') for part in descriptor.split('/')),
            'Descriptor must be a canonical relative file')
    shards = schedule()
    require(set(workers) == {s['name'] for s in shards}, 'Missing or extra worker allocation')
    files, rows = {}, []
    for shard in shards:
        name = shard['name']
        require(type(workers[name]) is int and 1 <= workers[name] <= 32, 'Invalid game-worker allocation')
        contract = {'version': 1, 'purpose': 'final', 'created_at': created_at,
            'candidate_sha256': candidate_sha, 'protocol_sha256': PROTOCOL_SHA,
            'identity': identity, 'shard': shard,
            'launch_authorization': {'stage': 'launch_intent', 'name': name,
                'candidate_sha256': candidate_sha, 'run_fingerprint': fingerprint(candidate_sha, identity)}}
        require(admit(contract, candidate, candidate_sha, identity)['reserved'], 'Wrong contract purpose')
        contract_path, job_path = f'controls/{name}.contract.json', f'controls/{name}.job.json'
        job = {'version': 1, 'artifact': 'artifact', 'descriptor': descriptor,
            'candidate': 'candidate.json', 'contract': contract_path, 'workers': workers[name],
            'opponent_model': f'artifact/{OPPONENT}' if shard['opponent'] == 'a260' else None}
        files[contract_path], files[job_path] = contract, job
        rows.append({'name': name, 'job': job_path, 'contract': contract_path,
            'shard': shard, 'workers': workers[name]})
    require(len(rows) == 320 and sum(r['shard']['games'] for r in rows) == 20160,
            'Final evaluation coverage changed')
    return files, rows


def source_files(root):
    """No symlink dereference or undeclared file can enter the portable source."""
    root = Path(root)
    require(root.is_dir() and not root.is_symlink(), 'Invalid source directory')
    paths = list(root.rglob('*'))
    require(not any(p.is_symlink() for p in paths), 'Source contains a symlink')
    require(all(p.is_file() or p.is_dir() for p in paths), 'Source contains a special file')
    return {str(p.relative_to(root)): digest(p) for p in sorted(paths) if p.is_file()}


def build(artifact, descriptor, candidate_path, workers, output, *, created_at=None):
    """Create one exclusive bundle; a failure leaves its intent/partial files."""
    artifact, candidate_path, output = map(lambda p: Path(p).absolute(), (artifact, candidate_path, output))
    require(not output.exists(), 'Inspect existing source preparation; do not overwrite')
    require(not output.resolve().is_relative_to(artifact.resolve())
            and not artifact.resolve().is_relative_to(output.resolve())
            and not candidate_path.resolve().is_relative_to(output.resolve()), 'Overlapping input/output paths')
    original_files = source_files(artifact)
    identity = artifact_identity(artifact, descriptor)
    require(digest(checked_path(artifact, 'ai/strong/final-protocol-multiplayer.json')) == PROTOCOL_SHA,
            'Artifact final protocol changed')
    opponent_hashes = {s['opponent_sha256'] for s in schedule() if s['opponent'] == 'a260'}
    require(opponent_hashes == {digest(checked_path(artifact, OPPONENT))}, 'Missing or wrong learned opponent')
    candidate_bytes = candidate_path.read_bytes()
    created_at = created_at or datetime.now(timezone.utc).isoformat()
    files, rows = controls(candidate_bytes, identity, descriptor, workers, created_at)
    entry = ROOT/'ai/strong'/ENTRY
    inputs = {'artifact_files': original_files, 'candidate_sha256': digest(candidate_path),
              'entry_sha256': digest(entry), 'builder_sha256': digest(__file__)}
    output.mkdir(parents=True, exist_ok=False)
    save(output/'intent.json', {'stage': 'preparing_source_only', 'created_at': created_at,
        'inputs': inputs, 'jobs_submitted': 0, 'games_executed': 0, 'reserved_final_seeds_used': False})
    bundle = output/'source'
    shutil.copytree(artifact, bundle/'artifact')
    shutil.copyfile(entry, bundle/ENTRY)
    with (bundle/'candidate.json').open('xb') as stream:
        stream.write(candidate_bytes)
    (bundle/'controls').mkdir()
    for name, value in files.items():
        save(bundle/name, value)
    plan = {'version': 1, 'candidate_sha256': inputs['candidate_sha256'], 'identity': identity,
        'protocol_sha256': PROTOCOL_SHA, 'run_fingerprint': fingerprint(inputs['candidate_sha256'], identity),
        'rows': rows, 'jobs': 320, 'games': 20160}
    save(bundle/'final-plan.json', plan)
    require(source_files(artifact) == original_files == source_files(bundle/'artifact'), 'Artifact bytes changed')
    require(digest(candidate_path) == digest(bundle/'candidate.json') == inputs['candidate_sha256'], 'Candidate changed')
    require(digest(entry) == digest(bundle/ENTRY) == inputs['entry_sha256'], 'Job entry changed')
    require(digest(__file__) == inputs['builder_sha256'], 'Builder changed')
    manifest = source_files(bundle)
    save(bundle/'source-manifest.json', manifest)
    result = {'prepared': True, 'source_manifest_sha256': digest(bundle/'source-manifest.json'),
        'plan_sha256': digest(bundle/'final-plan.json'), 'inputs': inputs,
        'jobs': 320, 'games': 20160, 'identity': identity, 'rows': rows,
        'jobs_submitted': 0, 'games_executed': 0, 'candidate_selected_by_builder': False,
        'launch_admitted': False, 'qualified': False, 'reserved_final_seeds_used': False,
        'remaining': 'Independently verify real selection/technical evidence and measured resource allocation before immutable HF publication and original-only launch.'}
    save(output/'prepared.json', result)
    return result
