"""Independently audit one first-recovery envelope and every retained pair.

No job dispatch, rerun, policy inference, survivor-only analysis or qualification.
The manager must first bind the actual HF handle/configuration and download hash.
"""
from datetime import datetime
from pathlib import Path
import re

import collect_current_auction_originals_after_timeout_v1 as original
import current_auction_resource_job_v2 as worker

read, digest, require = worker.read, worker.digest, worker.require
REMOTE_SOURCE = Path('/workspace/source')
REMOTE_OUTPUT = Path('/workspace/recovery-output')/worker.ATTEMPT


def reference_configuration(bundle, bundle_sha, source):
    config = worker.inspect(bundle, bundle_sha, source, REMOTE_OUTPUT, execute=True)
    # This is the frozen Python image/interpreter and original source location
    # used by the reviewed bootstrap, not caller-selected arbitrary commands.
    for key in ('command', 'dry_command'):
        config[key] = ['/usr/local/bin/python' if i == 0 else value.replace(str(Path(source).resolve()), str(REMOTE_SOURCE))
            for i,value in enumerate(config[key])]
    return config


def checked_evidence(evidence, name):
    require(evidence['repo'] == worker.retention.REPO and evidence['remote_archive_verified'] is True,
        'Unverified or foreign evidence')
    require(evidence['archive_path'] == 'archives/'+name+'.tgz', 'Wrong unique attempt archive')
    for key,size in (('revision',40),('archive_sha256',64),('manifest_sha256',64)):
        require(re.fullmatch('[a-f0-9]{'+str(size)+'}', evidence[key]) is not None, 'Unpinned evidence')


def audit_envelope(folder, evidence, bundle, bundle_sha, source, checkpoint_reader):
    """checkpoint_reader downloads/checks a receipt's archive and returns its tree."""
    folder = Path(folder).resolve(); checked_evidence(evidence, worker.ATTEMPT+'-final')
    worker.tree(folder,'manifest.json',evidence['manifest_sha256'])
    expected = reference_configuration(bundle,bundle_sha,source)
    require(read(folder/'attempt.json') == expected, 'Attempt/source/control/command binding differs')
    status = read(folder/'run-status.json'); supervisor = folder/'supervisor'
    require(status['stage'] == 'child_complete_pending_independent_audit'
        and status['attempt_id'] == worker.ATTEMPT and status['original_name'] == worker.FAILED_NAME
        and status['original_failed_handle'] == worker.FAILED_HANDLE, 'Original recovery did not complete')
    require(status['qualified'] is False and status['reserved_final_seeds_used'] is False
        and status['automatic_retries'] is False, 'Invalid recovery purpose')
    result = read(supervisor/'supervisor-result.json')
    require(status['supervisor'] == result and result['stage'] == 'child_exited'
        and result['attempt_id'] == worker.ATTEMPT
        and result['child_returncode'] == 0 and result['raw_audited'] is False
        and result['qualified'] is False and result['automatic_retries'] is False, 'Failed or changed original child')
    row = expected['row']; shard = row['shard']; n = row['players']
    episodes = set(range(shard['start']*4*n,(shard['start']+shard['deals'])*4*n))
    require(len(episodes) == result['expected_episodes'] == 16
        and result['retained_episodes'] == sorted(episodes), 'Missing/duplicated retained coverage')
    require(read(supervisor/'context.json') == expected['context'], 'Retention context differs')
    receipts = sorted(supervisor.glob('*.receipt.json'))
    intents = sorted(supervisor.glob('*.upload-intent.json'))
    require(len(receipts) == len(intents) == result['checkpoints'] and receipts, 'Incomplete/ambiguous checkpoint operations')
    require({p.name.removesuffix('.receipt.json') for p in receipts}
        == {p.name.removesuffix('.upload-intent.json') for p in intents}, 'Checkpoint operation identities differ')
    transports = read(folder/'checkpoint-transports.json')
    require(len(transports) == len(receipts), 'Missing transport observations')
    indexed = {item['directory']:item for item in transports}
    require(len(indexed) == len(transports), 'Duplicate checkpoint transport')
    require(any(t['child_live_before_upload'] is True and t['child_live_after_upload'] is True for t in transports),
        'No verified checkpoint while original child stayed live')
    retained = set(); checkpoint_reports = []
    raw = folder/'raw'; evaluation = raw/'job/evaluation'
    for receipt_file in receipts:
        name = receipt_file.name.removesuffix('.receipt.json')
        require(re.fullmatch(re.escape(worker.ATTEMPT)+r'-checkpoint-[0-9]{4}',name) is not None, 'Foreign checkpoint name')
        receipt = read(receipt_file); checkpoint_evidence = receipt['evidence']
        checked_evidence(checkpoint_evidence,name)
        require(receipt['context_sha256'] == digest(supervisor/'context.json')
            and receipt['raw_audited'] is False and receipt['qualified'] is False, 'Changed receipt context/purpose')
        require(name in indexed, 'Checkpoint lacks transport record'); transport=indexed[name]
        require(transport['evidence'] == checkpoint_evidence
            and transport['manifest_sha256'] == checkpoint_evidence['manifest_sha256'], 'Transport receipt differs')
        before,after = (datetime.fromisoformat(transport[k]) for k in ('started_at','finished_at'))
        require(before.tzinfo is not None and after.tzinfo is not None and before <= after, 'Invalid upload timing')
        intent = read(supervisor/(name+'.upload-intent.json'))
        require(intent == {'manifest_sha256':checkpoint_evidence['manifest_sha256'],'automatic_retries':False}, 'Checkpoint intent differs')
        checkpoint = Path(checkpoint_reader(checkpoint_evidence)).resolve()
        pins = worker.tree(checkpoint,'manifest.json',checkpoint_evidence['manifest_sha256'])
        metadata = read(checkpoint/'checkpoint.json')
        require(metadata['version'] == 2 and metadata['context'] == expected['context']
            and metadata['raw_audited'] is False and metadata['execution_complete'] is False
            and metadata['qualified'] is False, 'Checkpoint control/purpose changed')
        batch = metadata['episodes']
        require(batch == receipt['episodes'] and batch == sorted(set(batch)) and batch
            and all(type(ep) is int and ep in episodes and ep not in retained for ep in batch), 'Missing/duplicate/foreign checkpoint games')
        require(set(metadata['pair_hashes']) == {str(ep) for ep in batch}, 'Incomplete checkpoint hashes')
        wanted = {'checkpoint.json'}
        for ep in batch:
            names = {f'game-{ep}.json',f'decisions-{ep}.jsonl'}; wanted.update(names)
            hashes = metadata['pair_hashes'][str(ep)]; require(set(hashes) == names, 'Unexpected checkpoint pair')
            for filename,sha in hashes.items():
                require(pins[filename] == sha == digest(evaluation/filename), 'Checkpoint and final original bytes differ')
        require(set(pins) == wanted, 'Unexpected checkpoint contents')
        retained.update(batch); checkpoint_reports.append({'evidence':checkpoint_evidence,'episodes':batch})
    require(retained == episodes, 'Incomplete original retention')
    # The existing full verifier rechecks every raw game, public decision, search
    # receipt, legal move, exact candidate/contract and original execution identity.
    raw_evidence = {**evidence,'manifest_sha256':digest(raw/'manifest.json')}
    review = original.m.base.verify_artifacts(raw,expected['original_source'],row,raw_evidence)
    require(review['games'] == 16, 'Wrong independently audited game count')
    return {'verified':True,'games':16,'original_name':worker.FAILED_NAME,
        'original_failed_handle':worker.FAILED_HANDLE,'attempt_id':worker.ATTEMPT,
        'envelope_evidence':evidence,'bundle_manifest_sha256':bundle_sha,
        'admission_sha256':expected['admission_sha256'],'raw_manifest_sha256':raw_evidence['manifest_sha256'],
        'review':review,'checkpoint_archives':checkpoint_reports,
        'retained_episodes':sorted(retained),'original_failure_preserved':True,
        'qualification_eligible':False,'qualified':False,'reserved_final_seeds_used':False}
