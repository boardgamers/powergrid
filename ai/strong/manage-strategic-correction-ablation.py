"""Guarded phase diagnostics, immutable collection and complete-cell comparisons."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tarfile
from huggingface_hub import HfApi, get_token, hf_hub_download
from strategic_correction_screen import ROOT, read, write, digest, summarize, same, pairs, module

PROTOCOL = ROOT/'ai/strong/strategic-correction-ablation-protocol-v1.json'
SOURCE = ROOT/'ai/strong/strategic-correction-ablation-source-v1.json'
GUARDS = ROOT/'ai/runs/strategic-correction-ablation-launches-v1'
VERIFIED = ROOT/'ai/runs/strategic-correction-ablation-verified-v1'


def name(key,n,arm,start,end): return f'{key}-{n}p-{arm}-{start}-{end}'
def prefix(case): return 'runs/strategic-correction-ablation-v1-'+case


def plan():
    p = read(PROTOCOL)
    return [(key,n,arm,start,start+4) for n in reversed(p['players']) for arm in p['arms']
        for start in range(0,16,4) for key in ['11101','11102']]


def launch(execute):
    p,s = read(PROTOCOL),read(SOURCE)
    check = read(ROOT/'ai/strong/strategic-correction-ablation-preflight-v1.json')
    arms = read(ROOT/'ai/strong/strategic-correction-ablation-arms-preflight-v1.json')
    assert check['passed'] and check['games']==128 and digest(ROOT/'ai/strong/strategic-correction-ablation-preflight-v1.json')==s['preflight_sha256']
    assert arms['passed'] and arms['games']==48 and arms['source']==s
    assert digest(PROTOCOL)==s['protocol_sha256']
    assert all(digest(ROOT/path)==sha for path,sha in s['overlays'].items())
    GUARDS.mkdir(exist_ok=True)
    with (GUARDS/'.launch.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        pending=[]
        for item in plan():
            guard=GUARDS/(name(*item)+'.json')
            if guard.exists():
                old=read(guard)
                assert old['stage']=='launched' and re.fullmatch('[a-f0-9]{24}',old['job_id']), 'Inspect unresolved original job; never silently retry'
                assert old['source']==s and old['protocol_sha256']==digest(PROTOCOL)
                assert old['case']==list(item)
            else: pending.append(item)
        print({'launch':execute,'new_jobs':len(pending),'existing_jobs':len(plan())-len(pending)},flush=True)
        if not execute:return
        env=os.environ.copy();env['HF_TOKEN']=env.get('HF_TOKEN') or get_token() or ''
        assert env['HF_TOKEN']
        for i,item in enumerate(pending):
            key,n,arm,start,end=item;case=name(*item);guard=GUARDS/(case+'.json')
            record={'stage':'launch_intent','case':list(item),'source':s,'protocol_sha256':digest(PROTOCOL),
                'timeout_hours':4,'created_at':datetime.now(timezone.utc).isoformat(),'qualification_eligible':False}
            with guard.open('x') as f:json.dump(record,f,indent=2)
            command=['hf','jobs','run','--detach','--flavor','cpu-performance','--timeout','4h','--secrets','HF_TOKEN',
                '--label','project=powergrid-ai','--label','stage=strategic-correction-ablation-v1-'+case]
            for k,v in {'SOURCE_ARCHIVE':s['archive'],'SOURCE_REVISION':s['revision'],'SOURCE_SHA256':s['sha256'],
                'MODEL_KEY':key,'PLAYERS':str(n),'ARM':arm,'START':str(start),'END':str(end),'HF_HUB_DISABLE_PROGRESS_BARS':'1'}.items():
                command+=['--env',k+'='+v]
            command+=['--','python:3.11-slim-bookworm','bash','-lc','''
set -euo pipefail
apt-get update -qq
apt-get install -y --no-install-recommends libstdc++6 libgomp1 ca-certificates >/dev/null
python -m pip install --quiet --timeout 120 --retries 5 huggingface_hub==2.0.0 onnxruntime==1.30.0 numpy==2.4.6
mkdir -p /workspace
python - <<'PY'
import urllib.request,tarfile,os,hashlib
from pathlib import Path
from huggingface_hub import hf_hub_download
urllib.request.urlretrieve('https://nodejs.org/dist/v24.14.0/node-v24.14.0-linux-x64.tar.xz','/tmp/node.tar.xz')
with tarfile.open('/tmp/node.tar.xz') as bundle: bundle.extractall('/opt')
path=hf_hub_download('coyotte508/powergrid-ai-training-v1',os.environ['SOURCE_ARCHIVE'],repo_type='dataset',revision=os.environ['SOURCE_REVISION'])
assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==os.environ['SOURCE_SHA256']
with tarfile.open(path) as bundle: bundle.extractall('/workspace',filter='data')
PY
export PATH=/opt/node-v24.14.0-linux-x64/bin:$PATH
cd /workspace
python -u ai/strong/strategic_correction_ablation.py "$MODEL_KEY" "$PLAYERS" "$ARM" "$START" "$END" ai/runs/ablation-job --upload
''']
            try:
                result=subprocess.run(command,cwd=ROOT,env=env,capture_output=True,text=True,check=True)
                guard.with_suffix('.log').write_text(result.stdout+result.stderr)
                ids=set(re.findall(r'\b[0-9a-f]{24}\b',result.stdout));assert len(ids)==1
                record.update(stage='launched',job_id=ids.pop())
            except BaseException as error:
                record.update(stage='launch_unknown',error=type(error).__name__+': '+str(error));raise
            finally:write(guard,record)
            print({'case':case,'job_id':record['job_id'],'dispatched_this_run':i+1},flush=True)


def status():
    api=HfApi();guards=sorted(GUARDS.glob('*.json'))
    def inspect(path):
        row=read(path);assert row['stage']=='launched'
        info=api.inspect_job(job_id=row['job_id'])
        return {**row,'guard':str(path.relative_to(ROOT)),'authoritative_status':info.status.stage,
            'message':info.status.message,'started_at':str(info.started_at),'finished_at':str(info.finished_at)}
    with ThreadPoolExecutor(max_workers=12) as pool: jobs=list(pool.map(inspect,guards))
    revision=api.model_info(read(PROTOCOL)['repo']).sha
    from collections import Counter
    report={'checked_at':datetime.now(timezone.utc).isoformat(),'jobs':jobs,'artifact_revision':revision,
        'status_counts':dict(Counter(x['authoritative_status'] for x in jobs)),'qualification_eligible':False}
    write(ROOT/'ai/strong/strategic-correction-ablation-status-v1.json',report)
    print({k:v for k,v in report.items() if k!='jobs'})


def collect():
    s,p=read(SOURCE),read(PROTOCOL)
    snapshot=read(ROOT/'ai/strong/strategic-correction-ablation-status-v1.json')
    revision=snapshot['artifact_revision'];assert re.fullmatch('[a-f0-9]{40}',revision)
    archive=Path(hf_hub_download('coyotte508/powergrid-ai-training-v1',s['archive'],repo_type='dataset',revision=s['revision']))
    assert digest(archive)==s['sha256']
    runtime=ROOT/'ai/runs/strategic-correction-ablation-collector-runtime-v1'
    if not runtime.exists():
        runtime.mkdir()
        with tarfile.open(archive) as bundle:bundle.extractall(runtime,filter='data')
    # Independently compare every runtime byte, including the engine and encoder,
    # before executing the archived collector. Do not use current-checkout drift.
    import hashlib
    with tarfile.open(archive) as bundle:
        for member in bundle.getmembers():
            if member.isfile():assert digest(runtime/member.name)==hashlib.sha256(bundle.extractfile(member).read()).hexdigest()
    VERIFIED.mkdir(exist_ok=True)
    jobs=[j for j in snapshot['jobs'] if j['authoritative_status']=='COMPLETED' and not (VERIFIED/name(*j['case'])/'verified.json').exists()]
    def one(job):
        key,n,arm,start,end=job['case'];case=name(*job['case']);out=VERIFIED/case
        if out.exists():
            intent=read(out/'collection-intent.json')
            assert intent['case']==job['case'] and intent['source']==s and intent['prefix']==prefix(case)
            pinned_revision=intent['revision'];assert re.fullmatch('[a-f0-9]{40}',pinned_revision)
        else:
            out.mkdir(exist_ok=False);pinned_revision=revision
            write(out/'collection-intent.json',{'case':job['case'],'source':s,'prefix':prefix(case),'revision':pinned_revision})
        def fetch(file):
            assert Path(file).name==file
            data=Path(hf_hub_download(p['repo'],prefix(case)+'/'+file,revision=pinned_revision)).read_bytes()
            if (out/file).exists():assert (out/file).read_bytes()==data,'Existing partial differs from its immutable artifact'
            else:(out/file).write_bytes(data)
        fetch('ablation-check.json');check=read(out/'ablation-check.json')
        for file,sha in check['artifacts'].items():fetch(file);assert digest(out/file)==sha
        program='import json,sys; from pathlib import Path; from strategic_correction_ablation import verify_local; print(json.dumps(verify_local(Path(sys.argv[1]),sys.argv[2],int(sys.argv[3]),sys.argv[4],int(sys.argv[5]),int(sys.argv[6]),json.loads(sys.argv[7]))))'
        env=os.environ.copy();env['PYTHONPATH']=str(runtime/'ai/strong')
        result=subprocess.run([sys.executable,'-c',program,str(out),key,str(n),arm,str(start),str(end),json.dumps(s)],
            cwd=runtime,env=env,capture_output=True,text=True)
        (out/'independent-check.log').write_text(result.stdout+result.stderr);result.check_returncode()
        summary=json.loads(result.stdout)
        same({k:v for k,v in summary.items()},read(out/'summary.json'))
        write(out/'verified.json',{'verified':True,'revision':pinned_revision,'prefix':prefix(case),'case':job['case'],
            'source':s,'protocol_sha256':digest(PROTOCOL),'summary':summary,'qualification_eligible':False,
            'artifacts':{x.name:digest(x) for x in out.iterdir() if x.is_file()}})
        return {'case':case,'games':summary['games'],'roots_verified':summary['public_choices_reproduced']}
    print({'collecting':len(jobs)},flush=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        for result in pool.map(one,jobs):print(result,flush=True)


def compare():
    protocol=read(PROTOCOL);s=read(SOURCE)
    baseline=module('ablation_baseline_manager','manage-strategic-correction-screen.py')
    arms={};pending=[]
    for key in ['11101','11102']:
        arms[key]={}
        for n in protocol['players']:
            reference={}
            for base in ['parent',key]:
                rows=[]
                for start in range(0,16,4):
                    baseline.verify_saved(base,n,'economic',start,start+4,False)
                    rows+=read(baseline.folder(base,n,'economic',start,start+4)/'evaluation.json')['results']
                reference[base]=rows
            for arm in protocol['arms']:
                rows=[];pieces=[]
                for start in range(0,16,4):
                    case=name(key,n,arm,start,start+4);out=VERIFIED/case
                    if not (out/'verified.json').exists():pending.append(case);continue
                    saved=read(out/'verified.json');assert saved['verified'] and saved['source']==s and saved['protocol_sha256']==digest(PROTOCOL)
                    for file,sha in saved['artifacts'].items():assert digest(out/file)==sha
                    rows+=read(out/'evaluation.json')['results']
                    pieces.append({'case':case,'revision':saved['revision'],'prefix':saved['prefix'],'verified_sha256':digest(out/'verified.json')})
                if len(pieces)!=4:continue
                from arena_statistics import validate_pairs
                validate_pairs(rows,n);assert len(rows)==64*n
                differences={}
                for base,old in reference.items():
                    diff=lambda a,b:pairs.paired_difference(a,b,protocol['bootstrap_replicates'],protocol['bootstrap_seed'])
                    differences[base]={'overall':diff(rows,old),'by_rules':{v+('/sealed' if sealed else '/open'):diff(
                        [r for r in rows if r['variant']==v and r['sealed']==sealed],
                        [r for r in old if r['variant']==v and r['sealed']==sealed])
                        for v in ['original','recharged'] for sealed in [False,True]}}
                arms[key][str(n)+'p/'+arm]={**summarize(rows,protocol),'differences':differences,'provenance':pieces}
    result={'complete':not pending,'pending':pending,'arms':arms,'source':s,'protocol_sha256':digest(PROTOCOL),
        'qualification_eligible':False,'candidate_selected':False}
    write(ROOT/'ai/strong/strategic-correction-ablation-results-v1.json',result)
    print({'complete':result['complete'],'pending':len(pending),'cells':{k:len(v) for k,v in arms.items()}})


if __name__=='__main__':
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('command',choices=['launch','status','collect','compare'])
    parser.add_argument('--execute',action='store_true');args=parser.parse_args()
    if args.command=='launch':launch(args.execute)
    else:globals()[args.command]()
