"""Guarded HF pilot, immutable artifact collection, and paired label diagnostics."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
from datetime import datetime,timezone
import fcntl,gzip,hashlib,json,os,re,subprocess,sys,tarfile
from pathlib import Path
from huggingface_hub import HfApi,get_token,hf_hub_download
from strategic_collection import ROOT,read,write,digest

PROTOCOL=ROOT/'ai/strong/sealed-belief-pilot-protocol-v1.json'
SOURCE=ROOT/'ai/strong/sealed-belief-pilot-source-v1.json'
GUARDS=ROOT/'ai/runs/sealed-belief-pilot-launches-v1'
VERIFIED=ROOT/'ai/runs/sealed-belief-pilot-verified-v1'
name=lambda n,f,m:f'{n}p-{f}-{m}'
prefix=lambda case:'runs/sealed-belief-pilot-v1-'+case


def plan():
    p=read(PROTOCOL);return [(n,f,m) for n in reversed(p['players']) for f in p['source_modes'] for m in p['modes']]


def launch(execute):
    s,p=read(SOURCE),read(PROTOCOL);check=read(ROOT/'ai/strong/sealed-belief-pilot-preflight-v1.json')
    assert check['passed'] and check['source']==s and check['controls']['rollouts']==192 and check['archived_reference']['passed']
    assert digest(PROTOCOL)==s['protocol_sha256'] and all(digest(ROOT/file)==sha for file,sha in s['overlays'].items())
    GUARDS.mkdir(exist_ok=True)
    with (GUARDS/'.launch.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);pending=[]
        for case in plan():
            path=GUARDS/(name(*case)+'.json')
            if path.exists():
                old=read(path);assert old['stage']=='launched' and re.fullmatch('[a-f0-9]{24}',old['job_id']), 'Inspect ambiguous handle; never duplicate it'
                assert old['case']==list(case) and old['source']==s
            else:pending.append(case)
        print({'execute':execute,'new_jobs':len(pending),'existing_jobs':20-len(pending)},flush=True)
        if not execute:return
        env=os.environ.copy();env['HF_TOKEN']=get_token() or env.get('HF_TOKEN') or '';assert env['HF_TOKEN']
        for case in pending:
            n,f,m=case;path=GUARDS/(name(*case)+'.json');record={'stage':'launch_intent','case':list(case),
                'source':s,'protocol_sha256':digest(PROTOCOL),'timeout_hours':4,'created_at':datetime.now(timezone.utc).isoformat(),'qualification_eligible':False}
            with path.open('x') as out:json.dump(record,out,indent=2)
            command=['hf','jobs','run','--detach','--flavor','cpu-performance','--timeout','4h','--secrets','HF_TOKEN',
                '--label','project=powergrid-ai','--label','stage=sealed-belief-pilot-v1-'+name(*case)]
            for k,v in {'SOURCE_ARCHIVE':s['archive'],'SOURCE_REVISION':s['revision'],'SOURCE_SHA256':s['sha256'],
                'PLAYERS':str(n),'ROOT_SOURCE':f,'MODE':m,'HF_HUB_DISABLE_PROGRESS_BARS':'1'}.items():command+=['--env',k+'='+v]
            command+=['--','python:3.11-slim-bookworm','bash','-lc','''
set -euo pipefail
apt-get update -qq
apt-get install -y --no-install-recommends libstdc++6 libgomp1 ca-certificates >/dev/null
python -m pip install --quiet --timeout 120 --retries 5 huggingface_hub==2.0.0 onnxruntime==1.30.0 numpy==2.4.6
mkdir -p /workspace
python - <<'INNER'
import urllib.request,tarfile,os,hashlib
from pathlib import Path
from huggingface_hub import hf_hub_download
urllib.request.urlretrieve('https://nodejs.org/dist/v24.14.0/node-v24.14.0-linux-x64.tar.xz','/tmp/node.tar.xz')
with tarfile.open('/tmp/node.tar.xz') as bundle:bundle.extractall('/opt')
p=hf_hub_download('coyotte508/powergrid-ai-training-v1',os.environ['SOURCE_ARCHIVE'],repo_type='dataset',revision=os.environ['SOURCE_REVISION'])
assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==os.environ['SOURCE_SHA256']
with tarfile.open(p) as bundle:bundle.extractall('/workspace',filter='data')
INNER
export PATH=/opt/node-v24.14.0-linux-x64/bin:$PATH
cd /workspace
python -u ai/strong/sealed_belief_pilot.py "$PLAYERS" "$ROOT_SOURCE" "$MODE" ai/runs/belief-pilot --upload
''']
            try:
                result=subprocess.run(command,cwd=ROOT,env=env,capture_output=True,text=True,check=True)
                path.with_suffix('.log').write_text(result.stdout+result.stderr)
                ids=set(re.findall(r'\b[a-f0-9]{24}\b',result.stdout));assert len(ids)==1
                record.update(stage='launched',job_id=ids.pop())
            except BaseException as e:record.update(stage='launch_unknown',error=type(e).__name__+': '+str(e));raise
            finally:write(path,record)
            print({'case':name(*case),'job_id':record['job_id']},flush=True)


def status():
    api=HfApi()
    def inspect(path):
        row=read(path);assert row['stage']=='launched'
        job=api.inspect_job(job_id=row['job_id']);return {**row,'guard':str(path.relative_to(ROOT)),
            'authoritative_status':job.status.stage,'message':job.status.message,'started_at':str(job.started_at),'finished_at':str(job.finished_at)}
    with ThreadPoolExecutor(max_workers=8) as pool:jobs=list(pool.map(inspect,sorted(GUARDS.glob('*.json'))))
    result={'checked_at':datetime.now(timezone.utc).isoformat(),'artifact_revision':api.model_info(read(PROTOCOL)['repo']).sha,
        'jobs':jobs,'status_counts':dict(Counter(r['authoritative_status'] for r in jobs)),'qualification_eligible':False}
    write(ROOT/'ai/strong/sealed-belief-pilot-status-v1.json',result);print({k:v for k,v in result.items() if k!='jobs'})


def collect():
    s,p=read(SOURCE),read(PROTOCOL);snapshot=read(ROOT/'ai/strong/sealed-belief-pilot-status-v1.json')
    archive=Path(hf_hub_download('coyotte508/powergrid-ai-training-v1',s['archive'],repo_type='dataset',revision=s['revision']))
    assert digest(archive)==s['sha256'];runtime=ROOT/'ai/runs/sealed-belief-collector-runtime-v1'
    if not runtime.exists():
        runtime.mkdir()
        with tarfile.open(archive) as bundle:bundle.extractall(runtime,filter='data')
    with tarfile.open(archive) as bundle:
        for member in bundle.getmembers():
            if member.isfile():assert digest(runtime/member.name)==hashlib.sha256(bundle.extractfile(member).read()).hexdigest()
    VERIFIED.mkdir(exist_ok=True)
    def one(job):
        case=name(*job['case']);out=VERIFIED/case
        if out.exists():
            intent=read(out/'collection-intent.json');assert intent['case']==job['case'] and intent['source']==s
        else:
            out.mkdir();intent={'case':job['case'],'source':s,'revision':snapshot['artifact_revision']};write(out/'collection-intent.json',intent)
        revision=intent['revision'];assert re.fullmatch('[a-f0-9]{40}',revision)
        def fetch(file):
            assert Path(file).name==file
            data=Path(hf_hub_download(p['repo'],prefix(case)+'/'+file,revision=revision)).read_bytes()
            if (out/file).exists():assert (out/file).read_bytes()==data
            else:(out/file).write_bytes(data)
        fetch('pilot-check.json');check=read(out/'pilot-check.json');assert check['status']=='complete'
        assert check['source_revision']==s['revision'] and check['source_sha256']==s['sha256']
        for file,sha in check['artifacts'].items():fetch(file);assert digest(out/file)==sha
        command=[sys.executable,str(runtime/'ai/strong/sealed_belief_pilot.py'),*map(str,job['case']),str(out),'--verify']
        result=subprocess.run(command,cwd=runtime,capture_output=True,text=True)
        (out/'independent-check.log').write_text(result.stdout+result.stderr);result.check_returncode()
        summary=json.loads(result.stdout);assert summary==check['summary']
        write(out/'verified.json',{'verified':True,'case':job['case'],'source':s,'revision':revision,'prefix':prefix(case),
            'summary':summary,'artifacts':{x.name:digest(x) for x in out.iterdir() if x.is_file()},'qualification_eligible':False})
        return {'case':case,**summary}
    jobs=[j for j in snapshot['jobs'] if j['authoritative_status']=='COMPLETED' and not (VERIFIED/name(*j['case'])/'verified.json').exists()]
    print({'collecting':len(jobs)},flush=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        for result in pool.map(one,jobs):print(result,flush=True)


def compare():
    import numpy as np
    p,s=read(PROTOCOL),read(SOURCE);bank={};pending=[];provenance=[];total=0
    for case in plan():
        out=VERIFIED/name(*case)
        if not (out/'verified.json').exists():pending.append(name(*case));continue
        v=read(out/'verified.json');assert v['verified'] and v['source']==s
        for file,sha in v['artifacts'].items():assert digest(out/file)==sha
        total+=v['summary']['rollouts'];provenance.append({'case':name(*case),'revision':v['revision'],'prefix':v['prefix'],'verified_sha256':digest(out/'verified.json')})
        with gzip.open(out/'labels.jsonl.gz','rt') as f:
            for row in map(json.loads,f):
                key=(row['rootId'],row['mode'],row['belief'],row['batch']);assert key not in bank;bank[key]=row
    records=[]
    for meta in p['selected']:
        rid=meta['rootId'];needed=[(rid,m,b,batch) for m in p['modes'] for b in p['beliefs'] for batch in p['batches']]
        if not all(key in bank for key in needed):continue
        options=bank[needed[0]]['options'];means={}
        for belief in p['beliefs']:
            for batch in p['batches']:
                # Equal opponent-mode mixture; fixed original public menu order
                # resolves ties. Never select and evaluate on the same A/B batch.
                vectors=np.mean([[bank[rid,m,belief,batch]['paired_advantages_over_proposal'][str(i)] for i in options] for m in p['modes']],axis=0)
                means[belief,batch]=vectors.mean(axis=1)
        directions=[]
        for train,test in [('a','b'),('b','a')]:
            old=int(means['uniform_control',train].argmax());new=int(means['policy',train].argmax())
            directions.append({'selection_batch':train,'evaluation_batch':test,
                'old_action':options[old],'policy_action':options[new],'different':old!=new,
                'old_choice_gain_under_policy_belief':float(means['policy',test][old]),
                'policy_choice_gain_under_policy_belief':float(means['policy',test][new]),
                'difference_under_policy_belief':float(means['policy',test][new]-means['policy',test][old])})
        records.append({**meta,'directions':directions})
    summary={}
    groups={'all':records}
    for n in p['players']:groups[str(n)+'p']=[r for r in records if r['players']==n]
    for k in ['source','split','variant']:
        field='mode' if k=='source' else k
        for value in sorted({r[field] for r in records}):groups[k+'/'+value]=[r for r in records if r[field]==value]
    for key,rows in groups.items():
        ds=[d for r in rows for d in r['directions']]
        if ds:summary[key]={'roots':len(rows),'changed_directions':sum(d['different'] for d in ds),
            **{k:float(np.mean([d[k] for d in ds])) for k in ['old_choice_gain_under_policy_belief','policy_choice_gain_under_policy_belief','difference_under_policy_belief']}}
    report={'complete':not pending,'pending':pending,'verified_rollouts':total,'complete_mixture_roots':len(records),
        'source':s,'protocol_sha256':digest(PROTOCOL),'records':records,'summary':summary,'provenance':provenance,
        'qualification_eligible':False,'trained':False,
        'scope':'Conditional simulation diagnostic with disjoint A/B worlds. Not real-game strength, no fitted thresholds or candidate selection; affected-only39-root sample with one explicitly missing cell.'}
    write(ROOT/'ai/strong/sealed-belief-pilot-results-v1.json',report);print({k:report[k] for k in ['complete','verified_rollouts','complete_mixture_roots','summary']})


if __name__=='__main__':
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('command',choices=['launch','status','collect','compare']);parser.add_argument('--execute',action='store_true');a=parser.parse_args()
    if a.command=='launch':launch(a.execute)
    else:globals()[a.command]()
