"""Guarded fresh-state collection jobs and independent frozen-runtime verification."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import fcntl,hashlib,json,os,re,subprocess,sys,tarfile
from pathlib import Path
from huggingface_hub import HfApi,get_token,hf_hub_download
from strategic_collection import ROOT,read,write,digest

PROTOCOL=ROOT/'ai/strong/policy-iteration-collection-protocol-v2.json'
SOURCE=ROOT/'ai/strong/policy-iteration-collection-source-v2.json'
GUARDS=ROOT/'ai/runs/policy-iteration-collection-launches-v2'
VERIFIED=ROOT/'ai/runs/policy-iteration-collection-verified-v2'
name=lambda n,k,m:f'{n}p-{k}-{m}'
prefix=lambda case:'runs/policy-iteration-collection-v2-'+case


def plan():
    p=read(PROTOCOL);return [(n,k,m) for n in reversed(p['players']) for k in p['behaviors'] for m in p['opponents']]


def launch(execute):
    s,p=read(SOURCE),read(PROTOCOL);check=read(ROOT/'ai/strong/policy-iteration-collection-preflight-v2.json')
    assert check['passed'] and check['source']==s and check['games']['games']==192 and check['capture']['checks']==5106
    assert digest(PROTOCOL)==s['protocol_sha256'] and all(digest(ROOT/file)==sha for file,sha in s['overlays'].items())
    # Measured full-trajectory smoke cases, conservative scaling by all16 deals
    # and the worst matching policy/opponent across2p and6p; no shorter caps.
    admission=[]
    for n,k,m in plan():
        seconds=max(c['seconds'] for c in check['games']['cases'] if c['behavior']==k and c['opponent']==m)
        estimate=seconds*16*2*1.25;assert estimate<4*3600
        admission.append({'case':[n,k,m],'smoke_seconds':seconds,'conservative_scaled_seconds':estimate,'timeout_seconds':14400})
    GUARDS.mkdir(exist_ok=True)
    with (GUARDS/'.launch.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);pending=[]
        for case in plan():
            path=GUARDS/(name(*case)+'.json')
            if path.exists():
                row=read(path);assert row['stage']=='launched' and re.fullmatch('[a-f0-9]{24}',row['job_id']), 'Inspect unresolved handle, never silently retry'
                assert row['case']==list(case) and row['source']==s
            else:pending.append(case)
        print({'execute':execute,'new_jobs':len(pending),'existing_jobs':len(plan())-len(pending),'maximum_scaled_seconds':max(r['conservative_scaled_seconds'] for r in admission)},flush=True)
        if not execute:return
        env=os.environ.copy();env['HF_TOKEN']=get_token() or env.get('HF_TOKEN') or '';assert env['HF_TOKEN']
        for case in pending:
            n,k,m=case;path=GUARDS/(name(*case)+'.json')
            record={'stage':'launch_intent','case':list(case),'source':s,'protocol_sha256':digest(PROTOCOL),
                'timeout_hours':4,'admission':next(r for r in admission if r['case']==list(case)),
                'created_at':datetime.now(timezone.utc).isoformat(),'qualification_eligible':False}
            with path.open('x') as f:json.dump(record,f,indent=2)
            command=['hf','jobs','run','--detach','--flavor','cpu-performance','--timeout','4h','--secrets','HF_TOKEN',
                '--label','project=powergrid-ai','--label','stage=policy-iteration-collection-v2-'+name(*case)]
            for key,value in {'SOURCE_ARCHIVE':s['archive'],'SOURCE_REVISION':s['revision'],'SOURCE_SHA256':s['sha256'],
                'PLAYERS':str(n),'BEHAVIOR':k,'OPPONENT':m,'HF_HUB_DISABLE_PROGRESS_BARS':'1'}.items():command+=['--env',key+'='+value]
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
python -u ai/strong/policy_iteration_collection.py "$PLAYERS" "$BEHAVIOR" "$OPPONENT" ai/runs/policy-iteration-collection --upload
''']
            try:
                response=subprocess.run(command,cwd=ROOT,env=env,capture_output=True,text=True,check=True)
                path.with_suffix('.log').write_text(response.stdout+response.stderr)
                ids=set(re.findall(r'\b[a-f0-9]{24}\b',response.stdout));assert len(ids)==1
                record.update(stage='launched',job_id=ids.pop())
            except BaseException as e:record.update(stage='launch_unknown',error=type(e).__name__+': '+str(e));raise
            finally:write(path,record)
            print({'case':name(*case),'job_id':record['job_id']},flush=True)


def status():
    api=HfApi()
    def inspect(path):
        row=read(path);assert row['stage']=='launched';job=api.inspect_job(job_id=row['job_id'])
        return {**row,'guard':str(path.relative_to(ROOT)),'authoritative_status':job.status.stage,
            'message':job.status.message,'started_at':str(job.started_at),'finished_at':str(job.finished_at)}
    with ThreadPoolExecutor(max_workers=8) as pool:jobs=list(pool.map(inspect,sorted(GUARDS.glob('*.json'))))
    report={'checked_at':datetime.now(timezone.utc).isoformat(),'artifact_revision':api.model_info(read(PROTOCOL)['repo']).sha,
        'jobs':jobs,'status_counts':dict(Counter(r['authoritative_status'] for r in jobs)),'qualification_eligible':False}
    write(ROOT/'ai/strong/policy-iteration-collection-status-v2.json',report);print({k:v for k,v in report.items() if k!='jobs'})


def collect(workers=4):
    VERIFIED.mkdir(exist_ok=True)
    # Keep downloads and independent verification single-owner. A collector can
    # resume pinned partial outputs, but two writers must never share them.
    lock=(VERIFIED/'.collect.lock').open('a')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    s,p=read(SOURCE),read(PROTOCOL);snapshot=read(ROOT/'ai/strong/policy-iteration-collection-status-v2.json')
    archive=Path(hf_hub_download('coyotte508/powergrid-ai-training-v1',s['archive'],repo_type='dataset',revision=s['revision']))
    assert digest(archive)==s['sha256'];runtime=ROOT/'ai/runs/policy-iteration-collection-collector-v2'
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
            intent=read(out/'collection-intent.json');assert intent['source']==s and intent['case']==job['case']
        else:
            out.mkdir();intent={'case':job['case'],'source':s,'revision':snapshot['artifact_revision']};write(out/'collection-intent.json',intent)
        revision=intent['revision'];assert re.fullmatch('[a-f0-9]{40}',revision)
        def fetch(file):
            assert Path(file).name==file
            data=Path(hf_hub_download(p['repo'],prefix(case)+'/'+file,revision=revision)).read_bytes()
            if (out/file).exists():assert (out/file).read_bytes()==data
            else:(out/file).write_bytes(data)
        fetch('collection-check.json');check=read(out/'collection-check.json')
        assert check['status']=='complete' and check['source_revision']==s['revision'] and check['source_sha256']==s['sha256']
        for file,sha in check['artifacts'].items():fetch(file);assert digest(out/file)==sha
        result=subprocess.run([sys.executable,str(runtime/'ai/strong/policy_iteration_collection.py'),*map(str,job['case']),str(out),'--verify'],
            cwd=runtime,capture_output=True,text=True)
        (out/'independent-check.log').write_text(result.stdout+result.stderr);result.check_returncode()
        summary=json.loads(result.stdout)
        write(out/'verified.json',{'verified':True,'source':s,'case':job['case'],'revision':revision,'prefix':prefix(case),
            'summary':summary,'artifacts':{f.name:digest(f) for f in out.iterdir() if f.is_file()},'qualification_eligible':False})
        return {'case':case,**summary}
    jobs=[j for j in snapshot['jobs'] if j['authoritative_status']=='COMPLETED' and not (VERIFIED/name(*j['case'])/'verified.json').exists()]
    print({'collecting':len(jobs)},flush=True)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for result in pool.map(one,jobs):print(result,flush=True)
    lock.close()


def summarize():
    p,s=read(PROTOCOL),read(SOURCE);cases={};pending=[]
    for case in plan():
        out=VERIFIED/name(*case)
        if not (out/'verified.json').exists():pending.append(name(*case));continue
        v=read(out/'verified.json');assert v['verified'] and v['source']==s
        for file,sha in v['artifacts'].items():assert digest(out/file)==sha
        cases[name(*case)]={**v['summary'],'revision':v['revision'],'prefix':v['prefix'],
            'verified_sha256':digest(out/'verified.json'),'artifacts':v['artifacts']}
    games=sum(v['games'] for v in cases.values());roots=sum(v['roots'] for v in cases.values())
    report={'complete':not pending,'pending':pending,'cases':cases,'games':games,'engine_game_runs':2*games,
        'roots':roots,'planned_games':p['unique_games'],'source':s,'protocol_sha256':digest(PROTOCOL),
        'trained':False,'labels_generated':False,'qualification_eligible':False,
        'followup':'Select balanced public roots without outcomes; remove training/validation duplicate states and policy inputs, then freeze a separately checked teacher-label design on fresh training seeds.'}
    if not pending:assert games==7680 and len(cases)==30
    write(ROOT/'ai/strong/policy-iteration-collection-results-v2.json',report);print({k:report[k] for k in ['complete','games','roots','planned_games']})


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('command',choices=['launch','status','collect','summarize']);p.add_argument('--execute',action='store_true')
    p.add_argument('--workers',type=int,choices=range(1,17),default=4,help='Independent local verification processes; each model still uses one ORT thread')
    a=p.parse_args()
    if a.command=='launch':launch(a.execute)
    elif a.command=='collect':collect(a.workers)
    else:globals()[a.command]()
