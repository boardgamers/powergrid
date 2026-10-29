"""Archive existing first-batch preparation and launch metadata; no execution."""
import json
from pathlib import Path
import shutil

from huggingface_hub import HfApi
import manage_current_auction_remaining_v2 as m

OUT = m.ROOT/'ai/runs/current-auction-remaining-launch-evidence-v2'
DESCRIPTOR = m.STRONG/'current-auction-remaining-launch-evidence-v2.json'


def main():
    m.require(not OUT.exists() and not DESCRIPTOR.exists() and not OUT.with_suffix('.tgz').exists(),
        'Inspect existing archive intent/outcome before retry')
    source = m.source_checked(); _, rows = m.plan()
    state = m.read(m.OUT/'state.json')
    m.require(state['submitted'] == 64 and state['remaining_unsubmitted'] == 259
        and sum(state['stages'].values()) == 64 and state['qualified'] is False, 'Wrong initial batch state')
    register = m.STRONG/'current-auction-remaining-dispatch-v2.json'
    record = m.read(register)
    m.require(record['submitted_jobs'] == 64 and record['submitted_games'] == 1280
        and record['source_descriptor_sha256'] == m.digest(m.SOURCE), 'Initial register differs')
    api = HfApi(); repo = m.worker.base.retention.REPO
    m.require(api.model_info(repo).private, 'Evidence repo must be private')
    m.require(not api.file_exists(repo,'archives/'+OUT.name+'.tgz'), 'Inspect prior remote archive')
    paths = {Path(__file__), Path(m.__file__), Path(m.collection.__file__), m.SOURCE, m.PREP_EVIDENCE,
        m.PREFLIGHT, m.GATE, m.first.RESULT, m.first.SOURCE, register,
        m.ROOT/'ai/CURRENT-AUCTION-REMAINING-DISPATCH-2026-10-29.md',
        m.PRE/'prepared.json', m.PRE/'evidence-upload-intent.json', m.PRE/'evidence-upload-receipt.json',
        m.PRE/'source-upload-intent.json', m.PRE/'source-upload-receipt.json', m.OUT/'state.json'}
    paths.update(m.PRE.joinpath('bundle').iterdir()); paths.update(m.tests_checked())
    paths.update(m.OUT.joinpath('cycles').glob('*.json'))
    paths.update(m.ROOT.joinpath('ai/runs').glob('current-auction-remaining-*-v2-first.log'))
    for row in rows:
        directory = m.OUT/'jobs'/m.worker.attempt_name(row['name'])
        if not directory.exists(): continue
        m.checked_guard(directory,source,row)
        paths.update((directory/'launch-intent.json',directory/'launch.json'))
        paths.update(directory.joinpath('checks').glob('*.json'))
        for name in ('terminal.json','review.json'):
            if (directory/name).exists(): paths.add(directory/name)
    OUT.mkdir()
    for path in sorted(paths):
        m.require(path.is_file() and not path.is_symlink(), 'Invalid metadata file')
        target = OUT/path.relative_to(m.ROOT); target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(path,target); m.require(m.digest(path)==m.digest(target),'Concurrent metadata change')
    m.save(OUT/'manifest.json',{str(p.relative_to(OUT)):m.digest(p) for p in sorted(OUT.rglob('*')) if p.is_file()})
    m.durable(OUT.with_suffix('.intent.json'),{'created_at':m.now(),'manifest_sha256':m.digest(OUT/'manifest.json'),'automatic_retries':False})
    evidence = m.first.upload_evidence(OUT)
    m.durable(DESCRIPTOR,{'archive':evidence,'source_descriptor_sha256':m.digest(m.SOURCE),
        'initial_register_sha256':m.digest(register),'snapshot_sha256':m.digest(m.OUT/'state.json'),
        'submitted_jobs':64,'submitted_games':1280,'first_recovery_result_sha256':m.FIRST_RESULT_SHA,
        'new_jobs_during_archiving':0,'new_games_during_archiving':0,'qualified':False,'reserved_final_seeds_used':False})
    print(json.dumps({'archive':evidence,'new_jobs_during_archiving':0}),flush=True)


if __name__ == '__main__': main()
