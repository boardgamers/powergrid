"""Collect originals and dispatch only unsubmitted shards of an admitted final.

No policy selection, training, replacements, automatic failure recovery or
qualification. Admission must already bind complete confirmation and target
proof. A completed collection still needs a separate full independent audit.
"""
import argparse
from contextlib import contextmanager
import fcntl
import json
from pathlib import Path
import re
import shutil

from huggingface_hub import HfApi, get_token, hf_hub_download
import prepare_selected_public_policy_final_v1 as preparation
from public_policy_final_audit_v1 import digest, read, require, same
from public_policy_final_contract_v1 import object_hash
from selected_public_policy_final_dispatch_v1 import dispatch_once, durable_write, validate_release
from selected_public_policy_final_streaming_v1 import audit_archive

ROOT = preparation.ROOT
OUT = ROOT/'ai/runs/selected-public-policy-final-hf-v1'
ACTIVE = {'SCHEDULING', 'RUNNING'}


def admission():
    """Read-only; unfinished confirmation fails before network/output creation."""
    preparation.selection.completed_owner(read(ROOT/preparation.selection.OWNER))
    local = preparation.OUT
    prepared = read(local/'prepared.json')
    ready = preparation.readiness(ROOT/prepared['readiness']['review_path'])
    source, source_pins, plan = preparation.checked_preparation(prepared, ready)
    accepted = read(local/'admission.json'); release = read(local/'release.json')
    bootstrap = (local/'bootstrap.sh').read_text()
    require(bootstrap == preparation.bootstrap_text(), 'Final bootstrap differs from verified setup')
    validate_release(release, bootstrap)
    require(release['admission_sha256'] == digest(local/'admission.json')
            and same(release['plan'], plan) and same(release['allocation'], ready['resources']['allocation']),
            'Release differs from reviewed admission/plan/allocation')
    require(accepted['version'] == 1 and accepted['original_only'] is True
            and accepted['automatic_retries'] is False and accepted['max_active_jobs'] == 64
            and accepted['jobs_submitted'] == 0 and accepted['qualified'] is False
            and accepted['reserved_final_seeds_used'] is False, 'Invalid initial launch admission')
    require(accepted['candidate_sha256'] == prepared['candidate_sha256']
            and accepted['prepared_sha256'] == digest(local/'prepared.json')
            and same(accepted['selection_archive'], prepared['selection_archive'])
            and same(accepted['resources'], ready['resources']), 'Admission changed candidate or measured resources')
    for key in ('selection', 'input_hashes', 'review_path', 'resources'):
        require(same(accepted['readiness'][key], ready[key]), 'Admission evidence changed: '+key)
    require(same(accepted['source'], release['source'])
            and same(read(local/'source-upload-receipt.json'), release['source']), 'Immutable source receipt differs')
    ref = release['source']
    downloaded = hf_hub_download(ref['repo'], ref['archive'], repo_type='dataset', revision=ref['revision'])
    require(digest(downloaded) == ref['sha256'] == digest(local/preparation.SOURCE_NAME), 'Published source archive differs')
    selected = prepared['selection_archive']
    downloaded = hf_hub_download(selected['repo'], selected['archive_path'], revision=selected['revision'])
    require(digest(downloaded) == selected['archive_sha256'], 'Original selection archive differs')
    paths = [local/n for n in ('prepared.json', 'admission.json', 'release.json', 'candidate.json',
        'source-upload-receipt.json', 'bootstrap.sh', 'bundle/prepared.json')]
    paths += [source/n for n in (*source_pins, 'source-manifest.json')]
    paths += [ROOT/'ai/strong'/n for n in ('manage_selected_public_policy_final_v1.py',
        'selected_public_policy_final_dispatch_v1.py', 'selected_public_policy_final_streaming_v1.py',
        'selected_public_policy_final_collection_v1.py', 'public_policy_final_audit_v1.py',
        'public_policy_final_contract_v1.py', 'public_policy_runtime_v1.py', 'population_policy_verification.py')]
    pins = dict(ready['input_hashes'])
    for path in paths:
        name = str(path.relative_to(ROOT)); sha = digest(path)
        require(name not in pins or pins[name] == sha, 'Conflicting manager input pin')
        pins[name] = sha
    context = {'version': 1, 'release': release, 'bootstrap': bootstrap,
        'source_root': str(source), 'input_hashes': pins, 'max_active_jobs': 64,
        'automatic_retries': False, 'qualified': False}
    check_pins(context)
    return context


def check_pins(context):
    preparation.selection.pinned_files(ROOT, context['input_hashes'])


def originals(context):
    """Reject every ambiguous receipt before inspecting or launching anything."""
    release = context['release']; rows = validate_release(release, context['bootstrap'])
    directory = OUT/'dispatch'; jobs = directory/'jobs'
    if not directory.exists(): return {}
    require(not directory.is_symlink() and not jobs.is_symlink(), 'Symlink in original ledger')
    require(same(read(directory/'release.json'), release), 'Original ledger belongs to another release')
    require(not list(jobs.glob('*.pending')), 'Inspect incomplete original receipt write')
    saved = {}
    for path in sorted(jobs.glob('*.json')):
        require(not path.is_symlink(), 'Symlink in original receipt')
        launch = read(path); name = path.stem
        require(name in rows and launch['name'] == name and launch['stage'] == 'launched'
                and re.fullmatch('[a-f0-9]{24}', launch.get('job_id', '')) is not None,
                'Uncertain original submission; inspect without retry')
        require(launch['release_sha256'] == object_hash(release) and same(launch['row'], rows[name]),
                'Original launch binding changed')
        saved[name] = launch
    require(len({v['job_id'] for v in saved.values()}) == len(saved), 'Duplicate original handles')
    return saved


def status(api, launch):
    stage = api.inspect_job(job_id=launch['job_id']).status.stage
    require(isinstance(stage, str), 'Invalid original status response')
    value = {'checked_at': preparation.now(), 'name': launch['name'], 'job_id': launch['job_id'], 'stage': stage}
    directory = OUT/'originals'/launch['name']; directory.mkdir(parents=True, exist_ok=True)
    durable_write(directory/'status.json', value)
    return value


def evidence_from_log(log, name):
    receipts = []
    for line in log.splitlines():
        if not line.startswith('{'): continue
        try: value = json.loads(line)
        except json.JSONDecodeError: continue
        if isinstance(value, dict) and set(value) == {'evidence'}: receipts.append(value['evidence'])
    require(len(receipts) == 1, 'Missing or ambiguous original evidence receipt')
    evidence = receipts[0]
    require(evidence['repo'] == 'coyotte508/powergrid-ai-germany-v1'
            and evidence['archive_path'] == 'archives/'+name+'.tgz'
            and re.fullmatch('[a-f0-9]{40}', evidence['revision']) is not None
            and evidence['remote_archive_verified'] is True and evidence['format'] == 'tar.gz',
            'Wrong or unpinned original evidence')
    require(re.fullmatch('[a-f0-9]{64}', evidence['archive_sha256']) is not None, 'Invalid evidence digest')
    return evidence


def collected(context, launch):
    directory = OUT/'originals'/launch['name']; path = directory/'collected.json'
    if not path.exists(): return None
    saved = read(path); receipt = directory/'review.json'
    require(saved['release_sha256'] == object_hash(context['release'])
            and saved['launch_sha256'] == object_hash(launch) and saved['job_id'] == launch['job_id']
            and saved['name'] == launch['name'] and saved['receipt_sha256'] == digest(receipt),
            'Collected original binding changed')
    audit = read(receipt); review = audit['review']
    require(saved['qualified'] is False and audit['qualified'] is False and review['qualified'] is False
            and audit['purpose'] == 'initial_collection' and audit['review_sha256'] == object_hash(review)
            and audit['release_sha256'] == saved['release_sha256'] and audit['launch_sha256'] == saved['launch_sha256'],
            'Original audit receipt changed')
    require(review['verified'] is True and review['original_hf_stage'] == 'COMPLETED'
            and review['job_id'] == launch['job_id'] and review['name'] == launch['name']
            and review['games'] == saved['games'] == launch['row']['shard']['games']
            and same(review['identity'], context['release']['plan']['identity'])
            and same(audit['evidence'], review['evidence']) and same(saved['evidence'], audit['evidence']),
            'Original collection is incomplete or for another policy')
    archive = directory/'original.tgz'
    require(archive.is_file() and not archive.is_symlink() and archive.stat().st_size == saved['archive_bytes']
            and audit['original_archive_sha256'] == saved['evidence']['archive_sha256'], 'Original archive missing or changed size')
    # Raw bytes are hashed during initial and separate final audits. Polling
    # rechecks receipt bindings, not every multi-GB archive on every cycle.
    return saved


def collect_one(context, api, launch, observed):
    name = launch['name']; directory = OUT/'originals'/name
    require(observed['job_id'] == launch['job_id'] and observed['stage'] not in ACTIVE, 'Wrong/nonterminal original')
    require(not (directory/'collection-intent.json').exists(), 'Inspect interrupted original collection; do not replay automatically')
    durable_write(directory/'collection-intent.json', {'created_at': preparation.now(), 'status': observed,
        'release_sha256': object_hash(context['release']), 'launch_sha256': object_hash(launch),
        'automatic_retries': False}, exclusive=True)
    try:
        log = '\n'.join(str(line) for line in api.fetch_job_logs(job_id=launch['job_id'], follow=False))
        with (directory/'job.log').open('x') as stream: stream.write(log)
        evidence = evidence_from_log(log, name)
        durable_write(directory/'evidence.json', evidence, exclusive=True)
        original = Path(hf_hub_download(evidence['repo'], evidence['archive_path'], revision=evidence['revision']))
        require(digest(original) == evidence['archive_sha256'], 'Downloaded original archive mismatch')
        archive = directory/'original.tgz'
        with original.open('rb') as src, archive.open('xb') as dst: shutil.copyfileobj(src, dst)
        require(digest(archive) == evidence['archive_sha256'], 'Local original archive mismatch')
        require(observed['stage'] == 'COMPLETED', 'Original job failed; retained evidence must be inspected without replacement')
        audit_archive(archive, context['source_root'], context['release'], launch, evidence, context['bootstrap'],
            hf_stage=observed['stage'], scratch_root=OUT/'scratch', receipt=directory/'review.json', purpose='initial_collection')
        check_pins(context)
        saved = {'name': name, 'job_id': launch['job_id'], 'games': launch['row']['shard']['games'],
            'release_sha256': object_hash(context['release']), 'launch_sha256': object_hash(launch),
            'receipt_sha256': digest(directory/'review.json'), 'evidence': evidence,
            'archive_bytes': archive.stat().st_size, 'qualified': False}
        durable_write(directory/'collected.json', saved, exclusive=True)
        return collected(context, launch)
    except BaseException as error:
        durable_write(directory/'failure.json', {'stage': 'stopped_for_inspection', 'original_status': observed,
            'failure_type': type(error).__name__, 'original_evidence_preserved': True, 'automatic_retries': False}, exclusive=True)
        raise


def cycle(context, api, *, execute=False, token=None):
    """Caller holds the operation lock. Finish audits before any new launch."""
    check_pins(context)
    require(not (OUT/'STOP').exists() and not (OUT/'halt.json').exists(), 'Stopped final run requires inspection')
    launches = originals(context); done = {}; active = []
    for name, launch in launches.items():
        saved = collected(context, launch)
        if saved is not None: done[name] = saved; continue
        observed = status(api, launch)
        if observed['stage'] in ACTIVE: active.append(launch)
        else: done[name] = collect_one(context, api, launch, observed)
    # Completion during collection defers dispatch until the next collection
    # cycle. It never permits an unaudited terminal job to be replaced by work.
    awaiting = []
    for launch in active:
        observed = status(api, launch)
        if observed['stage'] not in ACTIVE: awaiting.append(launch['name'])
    check_pins(context)
    release = context['release']; rows = release['plan']['rows']
    pending = [r for r in rows if r['name'] not in launches]
    newly_submitted = 0
    require(len(active) <= context['max_active_jobs'] <= 64, 'Final concurrency allowance exceeded')
    if execute and not awaiting:
        slots = max(0, context['max_active_jobs']-len(active))
        if pending and slots:
            token = token or get_token(); require(bool(token), 'Missing job credential')
        for row in pending[:slots]:
            require(not (OUT/'STOP').exists(), 'Respect explicit stop')
            check_pins(context)
            launch = dispatch_once(api, OUT/'dispatch', release, row['name'], token, context['bootstrap'])
            launches[row['name']] = launch; newly_submitted += 1
    check_pins(context)
    complete = len(done) == 320
    games = sum(v['games'] for v in done.values())
    require(not complete or games == 20160, 'Complete final collection has wrong game count')
    report = {'checked_at': preparation.now(), 'complete': complete, 'verified_jobs': len(done),
        'completed_games': games, 'submitted_jobs': len(launches), 'expected_jobs': 320, 'expected_games': 20160,
        'newly_submitted': newly_submitted, 'awaiting_collection': awaiting,
        'release_sha256': object_hash(release), 'context_sha256': object_hash(context),
        'originals': done, 'qualified': False, 'reserved_execution_attempted': bool(launches),
        'remaining': 'Separate full independent archive audit and unchanged strength assessment; technical/admission bindings must also pass.'}
    durable_write(OUT/'collection-state.json', report)
    if complete and not (OUT/'collection-results.json').exists():
        durable_write(OUT/'collection-results.json', report, exclusive=True)
    return {k: report[k] for k in ('complete', 'verified_jobs', 'completed_games', 'submitted_jobs', 'newly_submitted', 'awaiting_collection', 'qualified')}


@contextmanager
def operation(context):
    require(not OUT.is_symlink(), 'Invalid final output directory')
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT/'.operation.lock').open('a') as owner:
        fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
        require(not (OUT/'STOP').exists() and not (OUT/'halt.json').exists(), 'Stopped final run requires inspection')
        path = OUT/'admitted-context.json'
        if path.exists(): require(same(read(path), context), 'Existing final context changed')
        else:
            require(not (OUT/'dispatch').exists() and not (OUT/'originals').exists(), 'Original run missing its admission context')
            durable_write(path, context, exclusive=True)
        try:
            yield
        except BaseException as error:
            if not (OUT/'halt.json').exists():
                durable_write(OUT/'halt.json', {'stage': 'stopped_for_inspection', 'created_at': preparation.now(),
                    'failure_type': type(error).__name__, 'context_sha256': object_hash(context),
                    'automatic_retries': False, 'qualified': False}, exclusive=True)
            raise


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('operation', choices=('check', 'collect', 'advance'))
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    require(args.execute == (args.operation == 'advance'), 'Only advance requires and permits --execute')
    context = admission()
    if args.operation == 'check':
        print(json.dumps({'admitted': True, 'jobs': 320, 'games': 20160, 'jobs_submitted': 0, 'qualified': False})); return
    with operation(context):
        print(json.dumps(cycle(context, HfApi(), execute=args.execute)), flush=True)


if __name__ == '__main__': main()
