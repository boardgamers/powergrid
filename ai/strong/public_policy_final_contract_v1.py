"""Frozen execution admission, separate from policy choice and qualification."""
from datetime import datetime
import hashlib
from pathlib import Path

from public_policy_final_audit_v1 import PROTOCOL_SHA, require, same, schedule, validate_identity, integer, read, digest
from public_policy_runtime_v1 import encode, sha256


def object_hash(value):
    return hashlib.sha256(encode(value).encode()).hexdigest()


def timestamp(value):
    require(isinstance(value, str), 'Missing freeze timestamp')
    result = datetime.fromisoformat(value)
    require(result.tzinfo is not None, 'Freeze timestamp needs a timezone')
    return result


def fingerprint(candidate_sha256, identity):
    return object_hash({'candidate_sha256': sha256(candidate_sha256),
                        'protocol_sha256': PROTOCOL_SHA, 'identity': validate_identity(identity)})


def admit(contract, candidate, candidate_sha256, identity):
    """Check an exact job ticket; never create a selection or launch intent."""
    validate_identity(identity)
    require(set(contract) == {'version', 'purpose', 'created_at', 'candidate_sha256', 'protocol_sha256',
                              'identity', 'shard', 'launch_authorization'}, 'Invalid execution contract fields')
    require(type(contract['version']) is int and contract['version'] == 1, 'Unsupported execution contract')
    require(contract['purpose'] in ('engineering', 'final'), 'Unknown execution purpose')
    require(same(contract['identity'], identity) and same(candidate['identity'], identity), 'Wrong complete-policy identity')
    require(contract['candidate_sha256'] == sha256(candidate_sha256), 'Candidate bytes changed')
    require(contract['protocol_sha256'] == candidate['protocol_sha256'] == PROTOCOL_SHA, 'Protocol changed')
    require(set(candidate) == {'status', 'frozen_at', 'identity', 'protocol_sha256', 'selection_evidence'}, 'Invalid candidate fields')
    require(timestamp(candidate['frozen_at']) <= timestamp(contract['created_at']), 'Candidate was frozen after its job contract')
    shard = contract['shard']; reserved = contract['purpose'] == 'final'
    if reserved:
        require(candidate['status'] == 'selected', 'Select and freeze candidate before reserved games')
        evidence = candidate['selection_evidence']
        require(isinstance(evidence, dict) and set(evidence) == {'repo', 'revision', 'archive_path', 'archive_sha256'},
                'Missing immutable candidate-selection evidence')
        require(evidence['repo'] == 'coyotte508/powergrid-ai-germany-v1', 'Unexpected selection repository')
        require(isinstance(evidence['revision'], str) and len(evidence['revision']) == 40
                and all(c in '0123456789abcdef' for c in evidence['revision']), 'Unpinned selection evidence')
        require(isinstance(evidence['archive_path'], str) and evidence['archive_path'].startswith('archives/'), 'Missing selection archive')
        sha256(evidence['archive_sha256'])
        require(shard in schedule(), 'Unknown reserved shard')
        expected = {'stage': 'launch_intent', 'name': shard['name'],
                    'candidate_sha256': candidate_sha256, 'run_fingerprint': fingerprint(candidate_sha256, identity)}
        require(same(contract['launch_authorization'], expected), 'Missing or mismatched launch authorization')
    else:
        require(candidate['status'] == 'engineering' and candidate['selection_evidence'] is None,
                'Engineering execution cannot select a candidate')
        require(contract['launch_authorization'] is None, 'Engineering execution cannot claim final admission')
        require(set(shard) == {'name', 'group', 'players', 'start', 'deals', 'seed', 'opponent', 'opponent_sha256', 'games'},
                'Incomplete engineering schedule')
        require(all(isinstance(shard[key], str) and shard[key] and 'reserved' not in shard[key].lower()
                    for key in ('name', 'group', 'seed')), 'Engineering schedule contains reserved namespace')
        require(type(shard['players']) is int and shard['players'] in range(2, 7), 'Unsupported player count')
        integer(shard['start']); integer(shard['deals'], 1)
        require(shard['opponent'] in ('legacy', 'heuristic', 'economic', 'rush', 'search_geo', 'economic_capacity_v1', 'a260'),
                'Unsupported opponent')
        require(shard['games'] == 4 * shard['players'] * shard['deals'], 'Incomplete paired deal')
        if shard['opponent'] == 'a260':
            sha256(shard['opponent_sha256'])
        else:
            require(shard['opponent_sha256'] is None, 'Unexpected opponent checkpoint')
    return {'reserved': reserved, 'shard': shard,
            'run_fingerprint': fingerprint(candidate_sha256, identity),
            'candidate_sha256': candidate_sha256, 'identity': identity}


def audit_execution_binding(directory, identity, runner_sha256):
    """Recheck saved candidate/contract bytes, independent of an in-memory claim."""
    directory = Path(directory)
    report = read(directory/'evaluation.json')
    candidate, contract = read(directory/'candidate.json'), read(directory/'contract.json')
    expected = {**admit(contract, candidate, digest(directory/'candidate.json'), identity),
                'contract_sha256': digest(directory/'contract.json'),
                'runner_sha256': sha256(runner_sha256), 'purpose': contract['purpose']}
    require(same(report['execution_binding'], expected), 'Saved execution binding differs from frozen documents')
    require(report['reserved_final_seeds_used'] is expected['reserved'], 'Wrong executed seed purpose')
    return expected
