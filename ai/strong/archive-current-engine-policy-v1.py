"""Archive public-model current-menu diagnostics and verify exact menu indexes."""
from datetime import datetime,timezone
import json
from pathlib import Path

from huggingface_hub import HfApi
from policy_iteration_evidence_archive import upload_evidence
from public_policy_development_job_v1 import digest,read

ROOT=Path(__file__).resolve().parents[2]
RUN=ROOT/'ai/runs/current-engine-policy-v1'
NAME='current-engine-policy-evidence-v1'
OUT=ROOT/'ai/runs'/NAME
RESULT=ROOT/'ai/strong'/(NAME+'.json')


def save(path,value):
    with path.open('x') as stream:json.dump(value,stream,indent=2,allow_nan=False);stream.write('\n')


def main():
    for p in (OUT,OUT.with_suffix('.tgz'),OUT.with_suffix('.intent.json'),RESULT):
        assert not p.exists(),'Inspect prior archive intent/outcome before retrying'
    report_path=ROOT/'ai/strong/current-engine-policy-results-v1.json';report=read(report_path)
    design=read(RUN/'design.json');inputs=read(RUN/'inputs.json')
    records=[json.loads(line) for line in (RUN/'decisions.jsonl').read_text().splitlines()]
    assert report['completed'] and report['public_interface_compatible_on_fixtures'] and not report['errors']
    assert report['actual_policy_requests']==len(inputs)==len(records)==30
    assert report['recorded_controls_exact']==report['recorded_controls']==10
    assert report['rollouts']==report['new_hf_jobs']==report['new_full_games']==report['new_gradients']==0
    assert report['qualification_eligible'] is report['reserved_final_seeds_used'] is False
    assert report['design_sha256']==digest(RUN/'design.json') and report['inputs_sha256']==digest(RUN/'inputs.json')
    assert report['receipts_sha256']==digest(RUN/'decisions.jsonl') and report['description_sha256']==digest(RUN/'description.json')
    assert all(digest(ROOT/n)==v for n,v in design['recorded_inputs'].items())
    assert design['python_checker_sha256']==digest(ROOT/'ai/strong/check-current-engine-policy-v1.py')
    assert design['node_checker_sha256']==digest(ROOT/'ai/strong/check-current-engine-policy-v1.cjs')
    indexes=[]
    for fixture,row in zip(inputs,records):
        assert row['request']==fixture['request'] and row['kind']==fixture['kind']
        response=row['response'];decision=response['decision'];legal=fixture['legal']
        assert response['requestId']==fixture['request']['requestId'] and response['revision']==fixture['request']['revision']
        assert type(decision['index']) is int and 0<=decision['index']<len(legal)
        assert legal[decision['index']]==decision['move']==response['move']
        assert type(decision['modelProposal']) is int and 0<=decision['modelProposal']<len(legal)
        assert decision['search'] is None and decision['modelSha256']=='55331f43379e8fe89025d93b1a7a48c88e0ea39b4ebd3a7ef8240d4b62753530'
        assert decision['featureRevision']=='4.3-strategic-correction'
        if fixture['kind']=='recorded-control':
            clean=lambda value:{k:v for k,v in value.items() if k!='elapsedMs'}
            assert clean(decision)==clean(fixture['originalDecision'])
        if fixture['kind']=='discount-money-one':
            assert decision['index']==1 and len(legal)==2 and legal[0]['name']=='ChoosePowerPlant'
            assert not fixture['frozenMenu'].get('ChoosePowerPlant')
        indexes.append({'requestId':response['requestId'],'kind':fixture['kind'],
            'offered_actions':len(legal),'selected_index':decision['index'],'model_proposal':decision['modelProposal']})
    sources={Path(__file__).resolve(),report_path}
    sources.update(p for p in RUN.rglob('*') if p.is_file())
    sources.update(ROOT/n for n in ('ai/strong/check-current-engine-policy-v1.py','ai/strong/check-current-engine-policy-v1.cjs',
        'ai/strong/current-engine-compatibility-evidence-v1.json','ai/strong/resource-runtime-preflight-evidence-v2.json',
        'ai/strong/policy_iteration_evidence_archive.py','ai/strong/strategic_collection.py',
        'ai/runs/current-engine-policy-v1.log','ai/CURRENT-ENGINE-POLICY-2026-10-28.md','ai/RESUME.md',
        'ai/runs/conservative-auction-development-attempts-coordinator-v1/state.json'))
    api=HfApi();repo='coyotte508/powergrid-ai-germany-v1'
    assert api.model_info(repo).private and not api.file_exists(repo,'archives/'+NAME+'.tgz')
    OUT.mkdir();hashes={}
    for p in sorted(sources):
        assert p.is_file() and not p.is_symlink()
        name=str(p.relative_to(ROOT));target=OUT/name;target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(p.read_bytes());hashes[name]=digest(target)
    save(OUT/'menu-index-audit.json',{'passed':True,'requests':30,'rows':indexes,'new_inference':0})
    hashes['menu-index-audit.json']=digest(OUT/'menu-index-audit.json');save(OUT/'manifest.json',hashes)
    intent={'created_at':datetime.now(timezone.utc).isoformat(),'stage':'prepared_for_upload',
        'archive_path':'archives/'+NAME+'.tgz','manifest_sha256':digest(OUT/'manifest.json')}
    save(OUT.with_suffix('.intent.json'),intent)
    print(json.dumps({'stage':'uploading','files':len(hashes)+1}),flush=True)
    archive=upload_evidence(OUT)
    save(RESULT,{'status':'filtered_model_current_menu_fixtures_legal_not_strength_validated',
        'report_sha256':digest(report_path),'design_sha256':report['design_sha256'],'inputs_sha256':report['inputs_sha256'],
        'receipts_sha256':report['receipts_sha256'],'menu_index_audit_sha256':digest(OUT/'menu-index-audit.json'),
        'actual_policy_requests':30,'recorded_controls_exact':10,'counterfactual_requests':20,
        'rollouts':0,'new_hf_jobs':0,'new_full_games':0,'new_gradients':0,
        'qualification_eligible':False,'reserved_final_seeds_used':False,'archive':archive})
    OUT.with_suffix('.intent.json').write_text(json.dumps({**intent,'stage':'uploaded_download_verified',
        'archive':archive,'descriptor_sha256':digest(RESULT)},indent=2)+'\n')
    print(json.dumps(archive),flush=True)


if __name__=='__main__':main()
