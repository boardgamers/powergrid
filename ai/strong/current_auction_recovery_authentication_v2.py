"""Authenticate explicit recovery receipts before complete-study raw re-auditing.

No remote API, collection, execution, model calls, analysis or candidate selection.
Missing coverage rejects before review/outcome loading. Authentication preserves
the original failed handle and never rewrites the old owner's completion state.
"""
from collections import Counter
from pathlib import Path
import json

import current_auction_recovery_coverage_v2 as coverage
import manage_current_auction_remaining_v2 as remaining

first = remaining.first
ROOT = remaining.ROOT
read, digest, require = remaining.read, remaining.digest, remaining.require
object_hash = remaining.worker.base.object_hash


def locations(name):
    if name == first.worker.FAILED_NAME:
        return {'kind':'failed_original_recovery', 'folder':first.OUT, 'review':first.RESULT,
            'source':first.SOURCE, 'bundle':first.PRE/'bundle', 'collector':first.collection,
            'manager':first, 'log':first.OUT/'original-recovery.log'}
    folder = remaining.OUT/'jobs'/remaining.worker.attempt_name(name)
    return {'kind':'first_execution', 'folder':folder, 'review':folder/'review.json',
        'source':remaining.SOURCE, 'bundle':remaining.PRE/'bundle', 'collector':remaining.collection,
        'manager':remaining, 'log':folder/'original.log'}


def inventory(plan):
    """Read only launch/terminal metadata and hash review bytes, without parsing them."""
    available, missing = [], []
    slots = {s['name']:s for s in plan['slots'] if s['kind'] != 'preserved_original'}
    for name in plan['fixed_recovery_order']:
        slot = slots[name]; paths = locations(name); folder = paths['folder']
        required = [folder/'launch.json', folder/'terminal.json', paths['review']]
        if not all(path.is_file() for path in required):
            missing.append({'name':name, 'kind':slot['kind'],
                'missing':[str(p.relative_to(ROOT)) for p in required if not p.is_file()]})
            continue
        guard, terminal = read(required[0]), read(required[1])
        require(guard['job_id'] == terminal['job_id'], 'Launch and terminal handles differ')
        require(terminal['stage'] == 'COMPLETED' and terminal['public_configuration_verified'] is True,
            'Recovery review must belong to a completed, bound HF job')
        available.append({'name':name, 'original_row_sha256':slot['original_row_sha256'],
            'original_failed_handle':first.worker.FAILED_HANDLE if slot['kind']=='failed_original_recovery' else None,
            'job_id':guard['job_id'], 'attempt_id':guard['attempt_id'], 'stage':'COMPLETED',
            'verified':True, 'review_sha256':digest(paths['review'])})
    return {'available':available, 'missing':missing, 'required':len(slots),
        'complete':not missing, 'review_contents_loaded':False, 'statistics_admitted':False}


def final_receipt(log):
    receipts = []
    for line in log.splitlines():
        try: value = json.loads(line)
        except (ValueError,TypeError): continue
        if isinstance(value,dict) and 'recovery_final_evidence' in value: receipts.append(value)
    require(len(receipts)==1, 'Missing/ambiguous original final receipt')
    return receipts[0]


def terminal_binding(terminal, guard, expected_environment, bootstrap):
    require(terminal['job_id'] == guard['job_id'] and terminal['attempt_id'] == guard['attempt_id']
        and terminal['stage'] == 'COMPLETED' and terminal['public_configuration_verified'] is True,
        'Unbound or incomplete HF terminal')
    require(terminal['timeout_seconds'] == 86400 and terminal['flavor'] == 'cpu-upgrade'
        and terminal['image'] == first.IMAGE, 'Changed effective HF allocation')
    require(terminal['bootstrap_sha256'] == first.sha_text(bootstrap)
        and terminal['environment_sha256'] == object_hash(expected_environment), 'Changed effective HF source/command')


def receipt_binding(reference, row, review, guard, terminal, receipt, expected, controls):
    """Pure metadata binding. This is not a raw-game or playing-strength audit."""
    require(reference['original_row_sha256'] == object_hash(row) and reference['name'] == row['name'], 'Wrong canonical row')
    require(reference['stage'] == 'COMPLETED' and reference['verified'] is True, 'Unverified recovery reference')
    require(review['job_id'] == reference['job_id'] == guard['job_id']
        and review['attempt_id'] == reference['attempt_id'] == guard['attempt_id'] == expected['context']['attempt_id']
        and review['original_name'] == row['name'] == expected['row']['name']
        and review['original_failed_handle'] == reference['original_failed_handle'] == guard['original_failed_handle'],
        'Review/launch/reference identity differs')
    require(guard['source'] == controls['source'] and guard['allocation'] == first.worker.ALLOCATION
        and guard['automatic_retries'] is False, 'Launch source/allocation differs')
    terminal_binding(terminal, guard, controls['environment'], controls['bootstrap'])
    require(review['terminal'] == terminal and review['source_descriptor_sha256'] == controls['source_sha256']
        and review['collector_sha256'] == controls['collector_sha256'] and review['manager_sha256'] == controls['manager_sha256'],
        'Review does not bind admitted collection')
    require(review['bundle_manifest_sha256'] == controls['source']['manifest_sha256'] == expected['bundle_manifest_sha256']
        and review['admission_sha256'] == expected['admission_sha256'], 'Review preparation differs')
    require(review['verified'] is True and review['games'] == row['shard']['games']
        and review['retained_episodes'] == coverage.episodes(row)
        and review['qualification_eligible'] is False and review['qualified'] is False
        and review['reserved_final_seeds_used'] is False, 'Wrong coverage or premature qualification')
    audit = review['review']['audit']
    require(review['review']['games'] == row['shard']['games'] and audit['identity'] == row['identity']
        and audit['expected'] == row['shard'] and audit['all_receipts_verified'] is True
        and audit['counts']['rollout_caps'] == 0 and audit['reserved_final_seeds_used'] is False, 'Wrong/incomplete original raw review')
    require(receipt['attempt_id'] == guard['attempt_id'] and receipt['recovery_final_evidence'] == review['envelope_evidence'],
        'Original log does not bind reviewed final archive')
    require(receipt['status']['stage'] == 'child_complete_pending_independent_audit'
        and receipt['status']['original_name'] == row['name']
        and receipt['status']['original_failed_handle'] == reference['original_failed_handle'], 'Original child did not complete')
    first.collection.checked_evidence(review['envelope_evidence'], guard['attempt_id']+'-final')


def context():
    """Frozen preparation checks only; no outcomes or current remote observations."""
    first_source = first.source_checked(); remaining_source = remaining.source_checked()
    plan = coverage.actual_plan(); original = read(first.STRONG/'current-auction-grid-source-v1.json')
    require(plan['first_recovery']['job_id'] == remaining.worker.FIRST_HANDLE, 'First recovery substitution')
    return {'plan':plan, 'original_source':original,
        'sources':{'failed_original_recovery':first_source, 'first_execution':remaining_source}}


def authenticate(reference, current):
    """Authenticate one existing raw-review receipt without rerunning its audit."""
    rows = {r['name']:r for r in current['original_source']['rows']}
    name = reference['name']; require(name in current['plan']['fixed_recovery_order'], 'Not a fixed recovery row')
    row = rows[name]; paths = locations(name); folder = paths['folder']; source = current['sources'][paths['kind']]
    require(digest(paths['review']) == reference['review_sha256'], 'Review bytes changed')
    guard = read(folder/'launch.json'); terminal = read(folder/'terminal.json'); review = read(paths['review'])
    if paths['kind'] == 'failed_original_recovery':
        require(reference['job_id'] == remaining.worker.FIRST_HANDLE and reference['attempt_id'] == first.worker.ATTEMPT
            and reference['original_failed_handle'] == first.worker.FAILED_HANDLE
            and reference['review_sha256'] == remaining.FIRST_RESULT_SHA, 'First recovery identity changed')
        remaining.worker.first_recovery_gate(review,current['original_source'],source)
        expected = first.collection.reference_configuration(paths['bundle'],source['manifest_sha256'],first.ORIGINAL)
        env = first.public_environment(source); bootstrap = first.bootstrap()
        intent = read(first.OUT/'launch-intent.json')
        require(all(intent[k] == guard[k] for k in ('attempt_id','source','allocation','original_failed_handle','automatic_retries')),
            'First launch intent differs')
    else:
        require(reference['original_failed_handle'] is None, 'First execution invented a prior failure')
        require(remaining.checked_guard(folder,source,row) == guard, 'Remaining launch changed')
        require(remaining.result_checked(folder,source,row) == review, 'Remaining collector binding differs')
        expected = remaining.collection.reference_configuration(paths['bundle'],source['manifest_sha256'],first.ORIGINAL,name)
        env = remaining.public_environment(source,row); bootstrap = remaining.bootstrap()
    controls = {'source':source, 'source_sha256':digest(paths['source']), 'collector_sha256':digest(paths['collector'].__file__),
        'manager_sha256':digest(paths['manager'].__file__), 'environment':env, 'bootstrap':bootstrap}
    require(terminal['log_sha256'] == digest(paths['log']), 'Original terminal log changed')
    receipt = final_receipt(paths['log'].read_text())
    receipt_binding(reference,row,review,guard,terminal,receipt,expected,controls)
    artifacts = folder/'artifacts'; manifest = artifacts/'manifest.json'; raw_manifest = artifacts/'raw/manifest.json'
    require(digest(manifest) == review['envelope_evidence']['manifest_sha256'], 'Final envelope manifest changed')
    pins = read(manifest)
    for filename in ('attempt.json','run-status.json','raw/manifest.json'):
        require(pins[filename] == digest(artifacts/filename), 'Final envelope control bytes changed')
    require(read(artifacts/'attempt.json') == expected and read(artifacts/'run-status.json') == receipt['status'],
        'Final envelope execution differs from prepared command or log')
    require(digest(raw_manifest) == review['raw_manifest_sha256'], 'Raw manifest differs from collected review')
    require(digest(paths['review']) == reference['review_sha256'], 'Review changed during authentication')
    return review


def authenticate_complete(current=None, loader=None):
    plan = coverage.actual_plan() if current is None else current['plan']
    available = inventory(plan)
    # The existing coverage gate checks completeness and all identities before
    # it calls any loader. This never treats a partial inventory as evidence.
    def lazy_authenticate(ref):
        nonlocal current
        if current is None: current = context()
        return authenticate(ref,current)
    result = coverage.require_complete_assignments(plan,available['available'],lazy_authenticate if loader is None else loader)
    require(result['coverage_complete'] is True and result['recovery_shards'] == 324
        and result['recovery_games'] == 7116, 'Actual recovery coverage differs')
    return {**result, 'authenticated_recovery_receipts':True,
        'assignment_hash':object_hash(available['available']), 'statistics_admitted':False,
        'raw_reaudit_required':True, 'candidate_selected':False}


def current_inventory_summary(current=None):
    values = inventory(coverage.actual_plan() if current is None else current['plan'])
    return {'required_recovery_receipts':values['required'], 'available_recovery_receipts':len(values['available']),
        'missing_recovery_receipts':len(values['missing']), 'complete':values['complete'],
        'missing_by_kind':dict(Counter(v['kind'] for v in values['missing'])),
        'review_contents_loaded':False, 'statistics_admitted':False}
