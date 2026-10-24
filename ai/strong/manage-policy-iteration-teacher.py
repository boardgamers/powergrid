"""Guarded HF pilot, immutable artifact collection, and paired label diagnostics."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
from datetime import datetime,timezone
import fcntl,gzip,hashlib,json,os,re,subprocess,sys,tarfile
from pathlib import Path
from huggingface_hub import HfApi,get_token,hf_hub_download
from strategic_collection import ROOT,read,write,digest

PROTOCOL=ROOT/'ai/strong/policy-iteration-teacher-protocol-v2.json'
SOURCE=ROOT/'ai/strong/policy-iteration-teacher-source-v2.json'
STAGE='probe'
GUARDS=ROOT/'ai/runs/policy-iteration-teacher-probe-launches-v2'
VERIFIED=ROOT/'ai/runs/policy-iteration-teacher-probe-verified-v2'
name=lambda n,b,f,m:f'{n}p-{b}-{f}-{m}'
prefix=lambda case:'runs/policy-iteration-teacher-v2-'+STAGE+'-'+case


def plan():
    p=read(PROTOCOL);return [(n,b,f,m) for n in reversed(p['players']) for b in p['behaviors'] for f in p['opponents'] for m in p['modes']]


def launch(execute):
    s,p=read(SOURCE),read(PROTOCOL);check=read(ROOT/'ai/strong/policy-iteration-teacher-preflight-v2.json')
    assert check['passed'] and check['source']==s and check['controls']['rollouts']==584 and check['shard']['roots']==12
    assert digest(PROTOCOL)==s['protocol_sha256']
    for file,sha in s['overlays'].items():
        path=ROOT/'ai/runs/policy-iteration-selected-v2/roots.jsonl.gz' if file==p['roots']['file'] else ROOT/file
        assert digest(path)==sha
    admissions=admit_pilot(p,s) if STAGE=='pilot' else {}
    GUARDS.mkdir(exist_ok=True)
    with (GUARDS/'.launch.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);pending=[]
        for case in plan():
            path=GUARDS/(name(*case)+'.json')
            if path.exists():
                old=read(path);assert old['stage']=='launched' and re.fullmatch('[a-f0-9]{24}',old['job_id']), 'Inspect ambiguous handle; never duplicate it'
                assert old['case']==list(case) and old['source']==s
            else:pending.append(case)
        print({'execute':execute,'new_jobs':len(pending),'existing_jobs':60-len(pending)},flush=True)
        if not execute:return
        env=os.environ.copy();env['HF_TOKEN']=get_token() or env.get('HF_TOKEN') or '';assert env['HF_TOKEN']
        for case in pending:
            n,b,f,m=case;path=GUARDS/(name(*case)+'.json');record={'stage':'launch_intent','case':list(case),
                'source':s,'protocol_sha256':digest(PROTOCOL),'stage_kind':STAGE,'admission':admissions.get(name(*case)),'timeout_hours':4,'created_at':datetime.now(timezone.utc).isoformat(),'qualification_eligible':False}
            with path.open('x') as out:json.dump(record,out,indent=2)
            command=['hf','jobs','run','--detach','--flavor','cpu-performance','--timeout','4h','--secrets','HF_TOKEN',
                '--label','project=powergrid-ai','--label','stage=policy-v2-'+STAGE+'-'+name(*case)]
            for k,v in {'SOURCE_ARCHIVE':s['archive'],'SOURCE_REVISION':s['revision'],'SOURCE_SHA256':s['sha256'],
                'PLAYERS':str(n),'BEHAVIOR':b,'ROOT_SOURCE':f,'MODE':m,'TEACHER_STAGE':STAGE,'HF_HUB_DISABLE_PROGRESS_BARS':'1'}.items():command+=['--env',k+'='+v]
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
python -u ai/strong/policy_iteration_teacher.py "$PLAYERS" "$BEHAVIOR" "$ROOT_SOURCE" "$MODE" "$TEACHER_STAGE" ai/runs/policy-teacher --upload
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
    write(ROOT/f'ai/strong/policy-iteration-teacher-{STAGE}-status-v2.json',result);print({k:v for k,v in result.items() if k!='jobs'})


def collect():
    VERIFIED.mkdir(exist_ok=True)
    lock=(VERIFIED/'.collect.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    s,p=read(SOURCE),read(PROTOCOL);snapshot=read(ROOT/f'ai/strong/policy-iteration-teacher-{STAGE}-status-v2.json')
    archive=Path(hf_hub_download('coyotte508/powergrid-ai-training-v1',s['archive'],repo_type='dataset',revision=s['revision']))
    assert digest(archive)==s['sha256'];runtime=ROOT/'ai/runs/policy-iteration-teacher-collector-v2'
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
        fetch('label-check.json');check=read(out/'label-check.json');assert check['status']=='complete'
        assert check['source_revision']==s['revision'] and check['source_sha256']==s['sha256']
        for file,sha in check['artifacts'].items():fetch(file);assert digest(out/file)==sha
        command=[sys.executable,str(runtime/'ai/strong/policy_iteration_teacher.py'),*map(str,job['case']),STAGE,str(out),'--verify']
        result=subprocess.run(command,cwd=runtime,capture_output=True,text=True)
        (out/'independent-check.log').write_text(result.stdout+result.stderr);result.check_returncode()
        summary=json.loads(result.stdout);assert summary==check['summary']
        if STAGE=='pilot':check_probe_prefix(out,case,s)
        write(out/'verified.json',{'verified':True,'case':job['case'],'source':s,'revision':revision,'prefix':prefix(case),
            'summary':summary,'artifacts':{x.name:digest(x) for x in out.iterdir() if x.is_file()},'qualification_eligible':False})
        return {'case':case,'roots':summary['roots'],'rollouts':summary['rollouts']}
    jobs=[j for j in snapshot['jobs'] if j['authoritative_status']=='COMPLETED' and not (VERIFIED/name(*j['case'])/'verified.json').exists()]
    print({'collecting':len(jobs)},flush=True)
    with ThreadPoolExecutor(max_workers=8) as pool:
        for result in pool.map(one,jobs):print(result,flush=True)
    lock.close()


def check_probe_prefix(out,case,source):
    probe=ROOT/'ai/runs/policy-iteration-teacher-probe-verified-v2'/case
    v=read(probe/'verified.json');assert v['verified'] and v['source']==source
    assert digest(probe/'labels.jsonl.gz')==v['artifacts']['labels.jsonl.gz']
    def rows(path):
        with gzip.open(path/'labels.jsonl.gz','rt') as f:return {(r['rootId'],r['batch']):r for r in map(json.loads,f)}
    small,large=rows(probe),rows(out);assert small.keys()==large.keys()
    for key,a in small.items():
        b=large[key];assert a['samples']==2 and b['samples']==96
        assert a['options']==b['options'] and a['seed']==b['seed'] and a['neural_beliefs']==b['neural_beliefs']
        first=sorted((r for r in b['rollouts'] if r['sample']<2),key=lambda r:r['env'])
        assert first==sorted(a['rollouts'],key=lambda r:r['env']), 'Larger batches changed a frozen probe trajectory'


def summarize():
    s,p=read(SOURCE),read(PROTOCOL);cases={};pending=[]
    for case in plan():
        out=VERIFIED/name(*case)
        if not (out/'verified.json').exists():pending.append(name(*case));continue
        v=read(out/'verified.json');assert v['verified'] and v['source']==s
        for file,sha in v['artifacts'].items():assert digest(out/file)==sha
        if STAGE=='pilot':check_probe_prefix(out,name(*case),s)
        cases[name(*case)]={**v['summary'],'revision':v['revision'],'prefix':v['prefix'],
                           'verified_sha256':digest(out/'verified.json'),'artifacts':v['artifacts']}
    report={'complete':not pending,'stage':STAGE,'pending':pending,'source':s,'protocol_sha256':digest(PROTOCOL),
            'cases':cases,'complete_cases':len(cases),'planned_cases':60,
            'rollouts':sum(r['rollouts'] for r in cases.values()),'trained':False,'qualification_eligible':False}
    write(ROOT/f'ai/strong/policy-iteration-teacher-{STAGE}-results-v2.json',report)
    print({k:report[k] for k in ['complete','stage','complete_cases','rollouts']})


def admit_pilot(p,source):
    path=ROOT/'ai/strong/policy-iteration-teacher-probe-results-v2.json';r=read(path)
    assert r['complete'] and r['complete_cases']==60 and r['source']==source
    assert r['protocol_sha256']==digest(PROTOCOL)
    result={}
    for key,c in r['cases'].items():
        v=ROOT/'ai/runs/policy-iteration-teacher-probe-verified-v2'/key/'verified.json'
        assert digest(v)==c['verified_sha256']
        # Full same-root paired probes, 96/2 linear scaling and a 2x margin.
        seconds=sum(t['seconds'] for t in c['timings'])*48*2+300
        result[key]={'probe_results_sha256':digest(path),'conservative_seconds':seconds,'timeout_seconds':14400}
    assert all(v['conservative_seconds']<14400 for v in result.values()), 'Split the pilot workload in a new version; do not shorten horizons'
    return result


def cross_batch_recommendations(paired,options,parent):
    import numpy as np
    directions=[]
    for train,test in [('a','b'),('b','a')]:
        train_mean,test_mean=paired[train].mean(1),paired[test].mean(1)
        winner=int(train_mean.argmax())
        for margin in [0.,.025]:
            chosen=winner if train_mean[winner]>margin else parent
            directions.append({'selection_batch':train,'evaluation_batch':test,'margin':margin,
                'action':options[chosen],'changed':chosen!=parent,'evaluation_gain':float(test_mean[chosen]),
                'evaluation_paired_standard_error':float(paired[test][chosen].std(ddof=1)/np.sqrt(96))})
    return directions


def assess():
    """Descriptive cross-batch label quality, never a model-strength score."""
    import numpy as np
    assert STAGE=='pilot'
    p,s=read(PROTOCOL),read(SOURCE);report=read(ROOT/'ai/strong/policy-iteration-teacher-pilot-results-v2.json')
    assert report['complete'] and report['source']==s and report['complete_cases']==60
    bank={}
    for case in plan():
        out=VERIFIED/name(*case);v=read(out/'verified.json')
        assert digest(out/'verified.json')==report['cases'][name(*case)]['verified_sha256']
        assert digest(out/'labels.jsonl.gz')==v['artifacts']['labels.jsonl.gz']
        with gzip.open(out/'labels.jsonl.gz','rt') as f:
            for row in map(json.loads,f):
                key=row['rootId'],row['mode'],row['batch'];assert key not in bank;bank[key]=row
    records=[]
    for root in p['pilot_roots']:
        rid=root['rootId'];first=bank[rid,'neural','a'];options=first['options'];parent=options.index(first['model_proposal'])
        paired={}
        for batch in ['a','b']:
            assert all(bank[rid,mode,batch]['options']==options for mode in p['modes'])
            paired[batch]=np.mean([[bank[rid,mode,batch]['paired_advantages_over_proposal'][str(i)] for i in options] for mode in p['modes']],axis=0)
            assert paired[batch].shape==(len(options),96) and (paired[batch][parent]==0).all()
        directions=cross_batch_recommendations(paired,options,parent)
        records.append({**root,'directions':directions,
            'unmargined_batches_agree':len({d['action'] for d in directions if d['margin']==0.})==1})
    groups={'all':records}
    for field in ['players','decision','variant','sealed','behavior','mode','split']:
        for value in sorted({r[field] for r in records}):groups[field+'/'+str(value)]=[r for r in records if r[field]==value]
    summary={}
    for key,rows in groups.items():
        summary[key]={'roots':len(rows),'unmargined_batch_agreement':float(np.mean([r['unmargined_batches_agree'] for r in rows])),'margins':{}}
        for margin in [0.,.025]:
            ds=[d for r in rows for d in r['directions'] if d['margin']==margin]
            summary[key]['margins'][str(margin)]={'directions':len(ds),'changes':sum(d['changed'] for d in ds),
                'mean_cross_batch_simulated_gain':float(np.mean([d['evaluation_gain'] for d in ds])),
                'changed_negative_directions':sum(d['changed'] and d['evaluation_gain']<0 for d in ds)}
    result={'source':s,'pilot_results_sha256':digest(ROOT/'ai/strong/policy-iteration-teacher-pilot-results-v2.json'),
            'records':records,'summary':summary,'trained':False,'qualification_eligible':False,
            'scope':'Conditional simulated label quality only; fixed0/.025 margins, disjoint A/B evaluation, all adverse cells retained. No model has been trained, no threshold fitted, no real-game improvement or final qualification implied.'}
    write(ROOT/'ai/strong/policy-iteration-teacher-pilot-assessment-v2.json',result)
    print(summary['all'])


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('stage',choices=['probe','pilot'])
    p.add_argument('command',choices=['launch','status','collect','summarize','assess']);p.add_argument('--execute',action='store_true');a=p.parse_args()
    STAGE=a.stage
    GUARDS=ROOT/f'ai/runs/policy-iteration-teacher-{STAGE}-launches-v2'
    VERIFIED=ROOT/f'ai/runs/policy-iteration-teacher-{STAGE}-verified-v2'
    if a.command=='launch':launch(a.execute)
    else:globals()[a.command]()
