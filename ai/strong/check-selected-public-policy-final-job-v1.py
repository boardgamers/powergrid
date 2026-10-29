"""Validate the final job transport against the real frozen hybrid, without games.

All candidate/launch documents below are explicitly synthetic contract fixtures.
No candidate is selected, no HF source/job is created, and no reserved deal is
executed. The existing confirmation source and policy artifact stay unchanged.
"""
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from public_policy_development_job_v1 import read, digest
from public_policy_final_audit_v1 import artifact_identity, schedule, PROTOCOL_SHA
from public_policy_final_contract_v1 import fingerprint

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'ai/runs/selected-public-policy-final-job-preflight-v1'
ENTRY = 'public_policy_selected_final_job_v1.py'
BASE = ROOT/'ai/runs/current-auction-grid-prepared-v1/source/artifact'
RESULT = ROOT/'ai/strong/selected-public-policy-final-job-preflight-v1.json'


def save(path, value):
    with path.open('x') as stream:
        json.dump(value,stream,indent=2,allow_nan=False);stream.write('\n')


def now(): return datetime.now(timezone.utc).isoformat()


def main():
    assert not OUT.exists() and not RESULT.exists(), 'Inspect original preflight outcome; do not repeat'
    tests = ROOT/'ai/runs/selected-public-policy-final-job-tests-v1-first.log'
    assert 'Ran 12 tests' in tests.read_text() and tests.read_text().rstrip().endswith('OK')
    base_manifest = read(BASE/'manifest.json')
    assert all(digest(BASE/n)==h for n,h in base_manifest.items())
    identity = artifact_identity(BASE,'policies/conservative_population.json')
    source_path = ROOT/'ai/strong/current-auction-grid-source-v1.json'
    source = read(source_path)
    assert identity == next(r['identity'] for r in source['rows'] if r['arm']=='conservative_population')
    OUT.mkdir()
    pins = {str(p.relative_to(ROOT)):digest(p) for p in (Path(__file__),ROOT/'ai/strong'/ENTRY,
        ROOT/'ai/strong/test_public_policy_selected_final_job_v1.py',tests,source_path,
        ROOT/'ai/strong/public_policy_final_contract_v1.py',ROOT/'ai/strong/public_policy_final_runner_v1.py',
        ROOT/'ai/strong/final-protocol-multiplayer.json')}
    save(OUT/'intent.json',{'started_at':now(),'input_hashes':pins,'synthetic_contract_fixtures_only':True,
        'candidate_selected':False,'new_games':0,'new_hf_jobs':0,'reserved_final_seeds_used':False})
    cases = [('valid_hybrid',None),('wrong_fingerprint','launch authorization'),
        ('wrong_reserved_shard','Unknown reserved shard'),('changed_search_budget','complete-policy identity'),
        ('dropped_search','complete-policy identity')]
    results=[]
    for name,error in cases:
        folder=OUT/name;folder.mkdir();bundle=folder/'source'
        artifact=bundle/'artifact';shutil.copytree(BASE,artifact,copy_function=os.link)
        shutil.copyfile(ROOT/'ai/strong'/ENTRY,bundle/ENTRY)
        chosen=deepcopy(identity)
        if name=='changed_search_budget':chosen['settings']['samples']=16
        candidate={'status':'selected','frozen_at':now(),'identity':chosen,'protocol_sha256':PROTOCOL_SHA,
            'selection_evidence':{'repo':'coyotte508/powergrid-ai-germany-v1','revision':'1'*40,
                'archive_path':'archives/synthetic-final-job-contract-fixture.tgz','archive_sha256':'2'*64}}
        save(bundle/'synthetic-candidate.json',candidate);candidate_sha=digest(bundle/'synthetic-candidate.json')
        shard=deepcopy(schedule()[0])
        if name=='wrong_reserved_shard':shard['start']=1
        authorization={'stage':'launch_intent','name':shard['name'],'candidate_sha256':candidate_sha,
            'run_fingerprint':fingerprint(candidate_sha,chosen)}
        if name=='wrong_fingerprint':authorization['run_fingerprint']='3'*64
        contract={'version':1,'purpose':'final','created_at':now(),'candidate_sha256':candidate_sha,
            'protocol_sha256':PROTOCOL_SHA,'identity':chosen,'shard':shard,'launch_authorization':authorization}
        save(bundle/'synthetic-contract.json',contract)
        descriptor='policies/filter.json' if name=='dropped_search' else 'policies/conservative_population.json'
        spec={'version':1,'artifact':'artifact','descriptor':descriptor,'candidate':'synthetic-candidate.json',
            'contract':'synthetic-contract.json','workers':4,'opponent_model':None}
        save(bundle/'job.json',spec)
        manifest={str(p.relative_to(bundle)):digest(p) for p in bundle.rglob('*') if p.is_file()}
        save(bundle/'source-manifest.json',manifest)
        command=[sys.executable,'-u','-B',str(bundle/ENTRY),'--source',str(bundle),
            '--manifest-sha256',digest(bundle/'source-manifest.json'),'--job','job.json',
            '--output',str(folder/'must-not-exist')]
        assert '--execute' not in command and '--upload' not in command
        with (folder/'validation.log').open('x') as log:
            process=subprocess.run(command,cwd='/tmp',stdout=log,stderr=subprocess.STDOUT)
        text=(folder/'validation.log').read_text()
        assert not (folder/'must-not-exist').exists(), 'Validation created an execution directory'
        if error is None:
            assert process.returncode==0,text
            outputs=[json.loads(line) for line in text.splitlines()]
            assert len(outputs)==2 and all(r['execute'] is False for r in outputs)
            assert outputs[0]['valid_contract'] and outputs[0]['binding']['identity']==identity
            assert outputs[0]['binding']['purpose']=='final' and outputs[1]['valid_job']
            assert outputs[1]['provenance']['source_revision'] is None
        else:
            assert process.returncode!=0 and error in text,text
        assert all(digest(bundle/n)==h for n,h in manifest.items())
        results.append({'case':name,'expected_rejection':error,'returncode':process.returncode,
            'passed':True,'source_manifest_sha256':digest(bundle/'source-manifest.json'),
            'validation_log_sha256':digest(folder/'validation.log'),'execution_directory_created':False})
        print(json.dumps(results[-1]),flush=True)
    assert all(digest(ROOT/n)==h for n,h in pins.items())
    assert all(digest(BASE/n)==h for n,h in base_manifest.items())
    report={'passed':True,'created_at':now(),'tests':12,'real_artifact_validation_cases':results,
        'identity':identity,'input_hashes':pins,'original_source_unchanged':True,
        'reference_source':{k:source[k] for k in ('repo','revision','archive','sha256','source_manifest_sha256')},
        'new_policy_calls':0,'new_games':0,'new_hf_jobs':0,'candidate_selected':False,
        'qualification_eligible':False,'reserved_final_seeds_used':False,
        'remaining':['complete confirmation and candidate selection','immutable final source/launch admission',
            'full selected-policy export/serving/8840U qualification','reserved strength evaluation and final audit'],
        'scope':'Final job transport validation only. Synthetic selection/authorization documents must never authorize a real launch.'}
    save(RESULT,report)
    print(json.dumps({'passed':True,'validation_cases':len(results),'new_games':0,'new_hf_jobs':0}),flush=True)


if __name__=='__main__':main()
