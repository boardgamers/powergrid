"""Persist read-only CLI validation of real 2/3/5/6-player remaining rows.

Controls are explicitly preflight-only and contain no execution admission.
Never invokes --execute or an evaluator. This is not a production source bundle.
"""
import json
from pathlib import Path
import shutil
import subprocess
import sys

import current_auction_bucket_worker_v3 as w
import manage_current_auction_remaining_v2 as m

OUT=m.ROOT/'ai/runs/current-auction-bucket-worker-preflight-v3'
REPORT=m.STRONG/'current-auction-bucket-worker-preflight-v3.json'


def main():
    w.require(not OUT.exists() and not REPORT.exists(),'Inspect existing preflight; never repeat')
    original,rows=m.plan()
    submitted={r['name'] for r in m.read(m.STRONG/'current-auction-remaining-dispatch-v2.json')['records']}
    chosen=[next(row for row in rows if row['players']==n and row['name'] not in submitted) for n in (2,3,5,6)]
    checks={}
    for file,count in (('current-auction-bucket-checkpoints-v3-tests-first.log',13),
            ('current-auction-bucket-collection-v3-tests-first.log',15),
            ('checkpoint-bucket-archives-v3-tests-first.log',8),
            ('current-auction-bucket-worker-v3-tests-first.log',10),
            ('current-auction-bucket-worker-flow-v3-tests-first.log',2)):
        path=m.ROOT/'ai/runs'/file;text=path.read_text()
        w.require(f'Ran {count} tests' in text and text.rstrip().endswith('OK'),'Incomplete test suite')
        checks[file]={'tests':count,'sha256':w.digest(path)}
    proof=w.read(m.STRONG/'current-auction-bucket-integration-probe-v3.json')
    w.require(proof['passed'] is True and proof['new_games']==proof['new_jobs']==0,'Missing actual storage proof')
    OUT.mkdir();results=[]
    w.save(OUT/'intent.json',{'scope':'read_only_preflight_no_execution_admission',
        'rows':[r['name'] for r in chosen],'new_jobs':0,'new_games':0,'new_inference':0})
    for row in chosen:
        n=row['players'];bundle=OUT/f'bundle-{n}p';bundle.mkdir()
        for name,module in w.CODE.items():shutil.copyfile(module.__file__,bundle/name)
        shutil.copyfile(w.__file__,bundle/w.ENTRY)
        shutil.copyfile(m.STRONG/'current-auction-grid-source-v1.json',bundle/'original-source.json')
        control={'version':3,'scope':'fixed_confirmation_bucket_retention',
            'attempt_id':row['name'].replace('pg-current-confirm-v1-','pg-current-bucket-v3-',1).replace('_','-'),
            'original_name':row['name'],'original_row_sha256':w.base.object_hash(row),
            'prior_failed_attempts':[],'reason':'never_submitted','allocation':w.ALLOCATION,
            'transport':w.TRANSPORT,'source_descriptor_sha256':w.base.SOURCE_SHA}
        decision={'status':'transport_recovery_recorded_execution_not_admitted',
            'strength_outcomes_used_for_decision':False,'reserved_final_seeds_used':False,
            'source_descriptor_sha256':w.base.SOURCE_SHA,'allocation':w.ALLOCATION,'transport':w.TRANSPORT,
            'rows':[{'name':row['name'],**{k:control[k] for k in ('original_row_sha256','reason','prior_failed_attempts','attempt_id')}}],
            'preflight_only':True,'production_execution_admitted':False}
        w.save(bundle/'decision.json',decision);control['decision_sha256']=w.digest(bundle/'decision.json')
        w.save(bundle/'control.json',control)
        w.save(bundle/'manifest.json',{p.name:w.digest(p) for p in sorted(bundle.iterdir())})
        sha=w.digest(bundle/'manifest.json');output=OUT/f'never-created-output-{n}p'
        config=w.inspect(bundle,sha,m.ORIGINAL,output)
        command=[sys.executable,'-u','-B',str(bundle/w.ENTRY),'--bundle',str(bundle),
            '--bundle-manifest-sha256',sha,'--source',str(m.ORIGINAL),'--output',str(output)]
        finished=subprocess.run(command,capture_output=True,text=True,check=True)
        (OUT/f'cli-{n}p.log').write_text(finished.stdout)
        w.require(not finished.stderr and not output.exists(),'Validation unexpectedly wrote an execution output')
        value=json.loads(finished.stdout)
        w.require(value['valid'] is True and value['execute'] is False and value['games']==row['shard']['games'],
            'Actual CLI validation failed')
        try:w.inspect(bundle,sha,m.ORIGINAL,output,execute=True)
        except ValueError as error:
            w.require(str(error)=='Actual prepared bucket worker admission required','Wrong execution rejection')
        else:raise ValueError('Preflight bundle incorrectly admits execution')
        results.append({'name':row['name'],'players':n,'games':row['shard']['games'],
            'bundle_manifest_sha256':sha,'core_files_sha256':config['core_files_sha256'],
            'cli_log_sha256':w.digest(OUT/f'cli-{n}p.log'),'validation_only':True,'missing_admission_rejected':True})
    report={'passed':True,'created_at':m.now(),'scope':'read_only_preflight_no_execution_admission',
        'results':results,'test_logs':checks,'new_tests':sum(r['tests'] for r in checks.values()),
        'storage_proof_sha256':w.digest(m.STRONG/'current-auction-bucket-integration-probe-v3.json'),
        'source_descriptor_sha256':w.base.SOURCE_SHA,'code_sha256':{name:w.digest(module.__file__) for name,module in w.CODE.items()}|{w.ENTRY:w.digest(w.__file__)},
        'new_jobs':0,'new_games':0,'new_inference':0,'production_execution_admitted':False,
        'qualified':False,'reserved_final_seeds_used':False}
    w.save(REPORT,report)
    print(json.dumps({'passed':True,'counts':[r['players'] for r in results],'new_tests':report['new_tests'],'new_jobs':0,'new_games':0}),flush=True)


if __name__=='__main__':main()
