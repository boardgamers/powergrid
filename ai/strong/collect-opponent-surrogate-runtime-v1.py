"""Collect the original HF calibration handles and verify their full evidence."""
import argparse
import ast
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import re

from huggingface_hub import HfApi, hf_hub_download
from strategic_collection import ROOT, read, write, digest
from population_policy_verification import extract_verified
from opponent_surrogate_verification_v1 import verify_artifacts, replay_public_teachers

STRONG=ROOT/'ai/strong'
spec=importlib.util.spec_from_file_location('surrogate_runtime_launcher',STRONG/'launch-opponent-surrogate-runtime-v1.py')
launcher=importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)
COLLECTED=ROOT/'ai/runs/opponent-surrogate-runtime-collected-v1'
RUNTIME=ROOT/'ai/runs/opponent-surrogate-source-prepared-v1/layout'


def collect(players):
    assert type(players) is int and players in (2,6)
    source,protocol=launcher.prerequisites()
    case=f'opponent-surrogate-runtime-v1-{players}p-0-1'
    guard_path=launcher.GUARDS/(case+'.json');guard=read(guard_path)
    assert guard['stage']=='launched' and guard['case']==case and guard['players']==players
    assert guard['source']==source and guard['plan_sha256']==digest(launcher.PLAN)
    assert guard['qualification_eligible'] is False and re.fullmatch('[a-f0-9]{24}',guard['job_id'])
    code={str(p.relative_to(ROOT)):digest(p) for p in [Path(__file__),STRONG/'opponent_surrogate_verification_v1.py',
          STRONG/'population_policy_verification.py',STRONG/'opponent_surrogate_collection_v1.py']}
    api=HfApi();info=api.inspect_job(job_id=guard['job_id'])
    status={'case':case,'job_id':guard['job_id'],'authoritative_status':info.status.stage,
            'checked_at':datetime.now(timezone.utc).isoformat(),'guard_sha256':digest(guard_path)}
    folder=COLLECTED/case;folder.mkdir(parents=True,exist_ok=True)
    write(folder/'status.json',status)
    if info.status.stage!='COMPLETED':return status
    log='\n'.join(str(line) for line in api.fetch_job_logs(job_id=guard['job_id'],follow=False))
    (folder/'job.log').write_text(log)
    receipts=[]
    for line in log.splitlines():
        if not line.startswith('{'):continue
        try:row=ast.literal_eval(line)
        except (ValueError,SyntaxError):continue
        if isinstance(row,dict) and row.get('status',{}).get('case')==case and 'evidence' in row:receipts.append(row)
    assert len(receipts)==1, 'Missing or ambiguous upload receipt; inspect original job'
    receipt=receipts[0];evidence=receipt['evidence']
    assert evidence['repo']=='coyotte508/powergrid-ai-germany-v1' and evidence['archive_path']==f'archives/{case}.tgz'
    assert re.fullmatch('[a-f0-9]{40}',evidence['revision']) and evidence['remote_archive_verified'] is True
    assert evidence['format']=='tar.gz'
    archive=Path(hf_hub_download(evidence['repo'],evidence['archive_path'],revision=evidence['revision']))
    assert digest(archive)==evidence['archive_sha256']
    artifacts=folder/'artifacts'
    if not artifacts.exists():extract_verified(archive,artifacts)
    assert read(artifacts/'job.json')==receipt['status']
    review=verify_artifacts(artifacts,protocol,source,players,0,1,'runtime',evidence)
    assert review['games']==review['twin_games']==4*players and review['training_eligible'] is False
    assert digest(RUNTIME/'opponent-surrogate-source-manifest.json')==source['manifest_sha256']
    assert all(digest(RUNTIME/name)==sha for name,sha in read(RUNTIME/'opponent-surrogate-source-manifest.json').items())
    replays=replay_public_teachers(artifacts,RUNTIME,folder/'local-public-replays')
    assert sum(r['public_replays'] for r in replays)==review['public_replays']
    assert all(digest(ROOT/name)==sha for name,sha in code.items())
    verified={**status,'verified':True,'source':source,'protocol_sha256':digest(launcher.PROTOCOL),
              'plan_sha256':digest(launcher.PLAN),'evidence':evidence,'review':review,'local_public_replays':replays,
              'collector_code_hashes':code,'gradients':False,'qualification_eligible':False,'reserved_final_seeds_used':False}
    write(folder/'verified.json',verified)
    return verified


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('players',type=int,choices=[2,6]);a=p.parse_args()
    r=collect(a.players)
    print(json.dumps({k:r[k] for k in ('case','job_id','authoritative_status','verified') if k in r}))
    if r.get('verified'):print(json.dumps({k:v for k,v in r['review'].items() if k!='cells'}))
