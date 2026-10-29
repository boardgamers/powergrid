"""Read-only verification of one returned, separately admitted final HF job.

No API calls, extraction, execution, selection, retries or qualification. The
caller supplies the original launch receipt, immutable source and downloaded
archive. Real admission and a complete independently audited grid remain separate.
"""
import hashlib
from pathlib import Path
import re
import tarfile

from public_policy_final_audit_v1 import (
    artifact_identity, audit_shard, digest, finite, read, require, same,
)
from public_policy_final_contract_v1 import admit, audit_execution_binding, object_hash
from public_policy_runtime_v1 import checked_path, sha256
from selected_public_policy_final_dispatch_v1 import validate_release

ENTRY = 'public_policy_selected_final_job_v1.py'


def checked_tree(root, manifest_name, expected_sha256):
    root = Path(root).absolute()
    require(root.is_dir() and not root.is_symlink(), 'Invalid evidence/source directory')
    paths = list(root.rglob('*'))
    require(not any(p.is_symlink() for p in paths), 'Symlink in evidence/source')
    require(all(p.is_file() or p.is_dir() for p in paths), 'Special file in evidence/source')
    manifest = root / manifest_name
    require(digest(manifest) == sha256(expected_sha256), 'Manifest hash mismatch')
    pins = read(manifest)
    require(isinstance(pins, dict) and pins and manifest_name not in pins, 'Invalid manifest')
    for name, value in pins.items():
        require(isinstance(name, str) and name and not Path(name).is_absolute()
                and all(p not in ('', '.', '..') for p in name.split('/')), 'Noncanonical manifest path')
        require(digest(checked_path(root, name)) == sha256(value), 'File hash mismatch: ' + name)
    require({str(p.relative_to(root)) for p in paths if p.is_file()} == set(pins) | {manifest_name},
            'Evidence/source file set differs from manifest')
    return root, pins


def checked_archive(archive, evidence, name, pins):
    require(evidence['repo'] == 'coyotte508/powergrid-ai-germany-v1'
            and re.fullmatch('[a-f0-9]{40}', evidence['revision']) is not None,
            'Unpinned evidence repository/revision')
    require(evidence['archive_path'] == f'archives/{name}.tgz'
            and evidence['format'] == 'tar.gz' and evidence['remote_archive_verified'] is True,
            'Wrong original evidence archive')
    expected = {**pins, 'manifest.json': sha256(evidence['manifest_sha256'])}
    require(evidence['archived_files'] == len(expected), 'Wrong archive file count')
    require(digest(archive) == sha256(evidence['archive_sha256']), 'Archive hash mismatch')
    with tarfile.open(archive, 'r:gz') as bundle:
        entries = bundle.getmembers()
        require(len(entries) == len(expected) and {e.name for e in entries} == set(expected),
                'Missing, duplicate or unexpected archive members')
        for entry in entries:
            require(entry.isfile(), 'Non-regular archive member')
            with bundle.extractfile(entry) as stream:
                require(hashlib.file_digest(stream, 'sha256').hexdigest() == expected[entry.name],
                        'Archive member differs from extracted evidence')


def verify_artifacts(folder, source_root, release, launch, evidence, archive, bootstrap, *, hf_stage):
    """Independently verify all raw decisions and exact source/launch bindings.

    Does not verify the substantive selection/admission archive: the real final
    manager must do that separately. Reject failed jobs; preserve them unchanged.
    """
    require(hf_stage == 'COMPLETED', 'Original HF job not completed; preserve without retry')
    rows = validate_release(release, bootstrap)
    name = launch['name']
    require(name in rows and launch['stage'] == 'launched'
            and re.fullmatch('[a-f0-9]{24}', launch['job_id']) is not None,
            'Missing unambiguous original launch handle')
    row = rows[name]
    require(launch['release_sha256'] == object_hash(release) and same(launch['row'], row),
            'Original launch belongs to another release/shard')
    source, source_pins = checked_tree(source_root, 'source-manifest.json',
                                      release['source']['source_manifest_sha256'])
    require(same(read(source / 'final-plan.json'), release['plan']), 'Source final plan differs from release')
    spec = read(source / row['job'])
    require(set(spec) == {'version', 'artifact', 'descriptor', 'candidate', 'contract', 'workers', 'opponent_model'},
            'Unexpected original job specification')
    require(type(spec['version']) is int and spec['version'] == 1
            and spec['artifact'] == 'artifact' and spec['candidate'] == 'candidate.json'
            and spec['contract'] == row['contract'] and same(spec['workers'], row['workers']),
            'Source job configuration changed')
    identity = release['plan']['identity']
    artifact = source / spec['artifact']
    require(same(artifact_identity(artifact, spec['descriptor']), identity), 'Wrong complete-policy artifact')
    opponent = 'artifact/final-opponent-a260.onnx' if row['shard']['opponent'] == 'a260' else None
    require(spec['opponent_model'] == opponent, 'Wrong opponent model path')
    if opponent:
        require(digest(checked_path(source, opponent)) == row['shard']['opponent_sha256'], 'Wrong learned opponent')
    candidate_path, contract_path = source / spec['candidate'], source / spec['contract']
    candidate_sha, contract_sha = digest(candidate_path), digest(contract_path)
    require(candidate_sha == release['plan']['candidate_sha256'], 'Selected candidate bytes changed')
    contract = read(contract_path)
    admission = admit(contract, read(candidate_path), candidate_sha, identity)
    require(admission['reserved'] and same(admission['shard'], row['shard']), 'Wrong final contract')
    provenance = {'source_manifest_sha256': release['source']['source_manifest_sha256'],
                  'job_spec_sha256': digest(source / row['job']), 'entry_sha256': digest(source / ENTRY),
                  'candidate_sha256': candidate_sha, 'contract_sha256': contract_sha,
                  'identity': identity, 'shard': row['shard'],
                  'source_revision': release['source']['revision'],
                  'source_archive_sha256': release['source']['sha256']}
    folder, evidence_pins = checked_tree(folder, 'manifest.json', evidence['manifest_sha256'])
    checked_archive(archive, evidence, name, evidence_pins)
    status = read(folder / 'job-status.json')
    require(status['stage'] == 'complete' and same(status['provenance'], provenance), 'Incomplete or wrong original job')
    require(status['qualified'] is False and status['candidate_selected_by_wrapper'] is False
            and status['reserved_final_seeds_used'] is True and status['reserved_execution_attempted'] is True
            and status['gradient_updates'] == 0 and status['automatic_retries'] is False,
            'Unexpected final execution flags')
    finite(status['seconds'])
    require(digest(folder / 'source-manifest.json') == provenance['source_manifest_sha256']
            and digest(folder / 'job-spec.json') == provenance['job_spec_sha256'], 'Saved source provenance changed')
    evaluation = folder / 'evaluation'
    require(digest(evaluation / 'candidate.json') == candidate_sha
            and digest(evaluation / 'contract.json') == contract_sha, 'Executed candidate/contract bytes differ')
    require(digest(evaluation / 'evaluation.json') == status['evaluation_sha256']
            and digest(evaluation / 'audit.json') == status['audit_sha256'], 'Saved evaluation/audit changed')
    config = read(evaluation / 'evaluation.json')['config']
    require(same(config['workers'], row['workers']) and config['descriptor'] == spec['descriptor'],
            'Executed worker allocation or descriptor changed')
    audit = audit_shard(evaluation, row['shard'], identity, reserved=True)
    runner_sha = digest(artifact / 'ai/strong/public_policy_final_runner_v1.py')
    binding = audit_execution_binding(evaluation, identity, runner_sha)
    require(binding['reserved'] is True and binding['purpose'] == 'final'
            and binding['candidate_sha256'] == candidate_sha and binding['contract_sha256'] == contract_sha,
            'Executed final binding changed')
    require(same(read(evaluation / 'audit.json'), {**audit, 'execution_binding': binding}),
            'Independent raw audit differs from saved audit')
    require(same(status['counts'], audit['counts']) and status['games'] == row['shard']['games'],
            'Wrong final counters or game count')
    # Detect changes during the independent audit, without modifying any input.
    require(checked_tree(source, 'source-manifest.json', provenance['source_manifest_sha256'])[1] == source_pins,
            'Source changed during audit')
    require(checked_tree(folder, 'manifest.json', evidence['manifest_sha256'])[1] == evidence_pins,
            'Evidence changed during audit')
    require(digest(archive) == evidence['archive_sha256'], 'Archive changed during audit')
    return {'verified': True, 'name': name, 'job_id': launch['job_id'], 'games': status['games'],
            'original_hf_stage': hf_stage,
            'release_sha256': object_hash(release), 'launch_sha256': object_hash(launch),
            'identity': identity, 'provenance': provenance, 'evidence': evidence,
            'audit': audit, 'execution_binding': binding, 'seconds': status['seconds'],
            'verifier_sha256': digest(__file__), 'qualified': False,
            'selection_and_launch_admission_verified_by_this_function': False}
