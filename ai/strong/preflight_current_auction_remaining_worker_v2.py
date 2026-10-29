"""Validate actual remaining source/commands while execution stays unadmitted."""
from collections import Counter
import json
from pathlib import Path
import shutil
import subprocess
import sys

import current_auction_remaining_resource_job_v2 as w
import manage_current_auction_resource_recovery_v2 as first

OUT=first.ROOT/'ai/runs/current-auction-remaining-worker-preflight-v2'
REPORT=first.STRONG/'current-auction-remaining-worker-preflight-v2.json'


def main():
    require=w.require
    require(not OUT.exists() and not REPORT.exists(),'Inspect existing remaining preflight')
    first.prepared();require(not first.RESULT.exists(),'First result appeared; review it before changing preparation state')
    original=w.read(first.STRONG/'current-auction-grid-source-v1.json')
    decision=w.read(first.STRONG/'current-auction-resource-recovery-decision-v2.json')
    require(w.digest(first.STRONG/'current-auction-grid-source-v1.json')==w.base.SOURCE_SHA
        and w.digest(first.STRONG/'current-auction-resource-recovery-decision-v2.json')==w.base.DECISION_SHA,'Original inputs differ')
    rows=[w.remaining_row(original,decision,r['name']) for r in decision['fixed_recovery_rows'] if r['reason']=='never_submitted']
    require(len(rows)==323 and sum(r['shard']['games'] for r in rows)==7100,'Wrong remaining grid')
    source=first.ORIGINAL;source_pins=w.base.tree(source,'source-manifest.json',original['source_manifest_sha256'])
    for row in rows:w.original_job_controls(source,original,row,source_pins)
    require(len({w.attempt_name(r['name']) for r in rows})==323,'Attempt namespace collision')
    tests=first.ROOT/'ai/runs/current-auction-remaining-worker-tests-v2-first.log'
    require('Ran 10 tests' in tests.read_text() and tests.read_text().rstrip().endswith('OK'),'Worker tests incomplete')
    OUT.mkdir();bundle=OUT/'bundle';bundle.mkdir()
    files={w.ENTRY:Path(w.__file__),w.base.ENTRY:Path(w.base.__file__),w.base.CORE:Path(w.base.retention.__file__),
        'original-source.json':first.STRONG/'current-auction-grid-source-v1.json',
        'decision.json':first.STRONG/'current-auction-resource-recovery-decision-v2.json',
        'first-recovery-source.json':first.SOURCE}
    for name,path in files.items():shutil.copyfile(path,bundle/name)
    w.save(bundle/'manifest.json',{p.name:w.digest(p) for p in sorted(bundle.iterdir())})
    bundle_sha=w.digest(bundle/'manifest.json')
    w.save(OUT/'intent.json',{'purpose':'remaining actual-source validation only; first audit missing',
        'bundle_manifest_sha256':bundle_sha,'new_games':0,'new_hf_jobs':0})
    checked=[]
    for n in (2,3,5,6):
        row=next(r for r in rows if r['players']==n);output=OUT/('NEVER-EXECUTED-'+str(n))
        config=w.inspect(bundle,bundle_sha,source,output,row['name'])
        require(not config['first_recovery_gate_verified'],'Missing first audit cannot be passed')
        command=[sys.executable,'-u','-B',str(bundle/w.ENTRY),'--bundle',str(bundle),'--bundle-manifest-sha256',bundle_sha,
            '--source',str(source),'--output',str(output),'--name',row['name']]
        with (OUT/f'worker-validation-{n}p.log').open('x') as log:
            subprocess.run(command,cwd='/tmp',stdout=log,stderr=subprocess.STDOUT,check=True)
        # This entry validates by default; the measured original entry executes by
        # design and is deliberately never called by this preflight.
        original_command=[sys.executable,'-u','-B',str(source/'public_policy_development_job_v1.py'),
            '--source',str(source),'--manifest-sha256',original['source_manifest_sha256'],'--job',row['job'],
            '--output',str(Path(config['raw_output'])/'job'),'--source-revision',original['revision'],
            '--source-archive-sha256',original['sha256']]
        require('--execute' not in original_command and '--upload' not in original_command,'Validation may not execute')
        with (OUT/f'original-validation-{n}p.log').open('x') as log:
            subprocess.run(original_command,cwd='/tmp',stdout=log,stderr=subprocess.STDOUT,check=True)
        try:w.inspect(bundle,bundle_sha,source,output,row['name'],execute=True)
        except ValueError as error:rejection=str(error)
        else:raise AssertionError('Actual remaining execution admitted before first recovery audit')
        require(rejection=='Complete independently audited first recovery is required before any remaining game',
            'Wrong execution rejection')
        require(not output.exists(),'Validation created game output')
        checked.append({'players':n,'name':row['name'],'original_row_sha256':w.base.object_hash(row),
            'original_runner_validation_only':True,'worker_validation_only':True,'execution_rejected':rejection,
            'output_created':False})
    first.prepared()
    report={'passed':True,'tests':10,'positive_controls':'first-recovery metadata is synthetic in unit tests; no positive actual first-audit claim',
        'actual_source_manifest_sha256':original['source_manifest_sha256'],'actual_specs_policies_contracts_checked':323,
        'actual_remaining_games':7100,'actual_rows_by_player_count':dict(Counter(r['players'] for r in rows)),
        'actual_validation_commands':checked,'bundle_manifest_sha256':bundle_sha,
        'worker_sha256':w.digest(w.__file__),'preflight_sha256':w.digest(__file__),
        'test_sha256':w.digest(first.STRONG/'test_current_auction_remaining_resource_job_v2.py'),'test_log_sha256':w.digest(tests),
        'validation_hashes':{str(p.relative_to(first.ROOT)):w.digest(p) for p in sorted(OUT.glob('*.log'))},
        'original_source_sha256':w.base.SOURCE_SHA,'decision_sha256':w.base.DECISION_SHA,
        'first_recovery_handle':w.FIRST_HANDLE,'first_recovery_result_available':False,
        'source_published':False,'remaining_execution_admitted':False,'new_hf_jobs':0,'new_games':0,'new_inference':0,
        'candidate_selected':False,'qualified':False,'reserved_final_seeds_used':False,
        'previous_goal_turn_classification':'progress','current_goal_turn_classification':'progress','goal_status':'active'}
    w.save(REPORT,report)
    print(json.dumps({k:report[k] for k in ('passed','tests','actual_specs_policies_contracts_checked','actual_remaining_games',
        'actual_rows_by_player_count','first_recovery_result_available','source_published','new_games')}),flush=True)


if __name__=='__main__':main()
