"""Guarded HF data collection and independent public-root verification."""
import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
import subprocess
from huggingface_hub import hf_hub_download
from strategic_collection import ROOT, PROTOCOL, SOURCE, read, write, digest, prefix, verify_local


def directory(n,mode,smoke):
    return ROOT/('ai/runs/strategic-training-collection-'+('smoke-' if smoke else '')+'verified-v1')/f'{n}p-{mode}'


def collect(a):
    assert re.fullmatch('[a-f0-9]{40}',a.revision)
    p=read(PROTOCOL);source=read(SOURCE);remote=prefix(a.players,a.mode,a.smoke)
    path=Path(hf_hub_download(p['repo'],remote+'/collection-check.json',revision=a.revision))
    status=read(path);assert status['status']=='complete'
    out=directory(a.players,a.mode,a.smoke);out.mkdir(parents=True,exist_ok=False)
    (out/'collection-check.json').write_bytes(path.read_bytes())
    assert set(status['artifacts'])=={'games.json','roots.jsonl.gz'}
    for name,sha in status['artifacts'].items():
        path=Path(hf_hub_download(p['repo'],remote+'/'+name,revision=a.revision));assert digest(path)==sha
        (out/name).write_bytes(path.read_bytes())
    summary=verify_local(out,a.players,a.mode,a.smoke)
    saved={'players':a.players,'mode':a.mode,'smoke':a.smoke,'revision':a.revision,'prefix':remote,
        'source_revision':source['revision'],'source_sha256':source['sha256'],'protocol_sha256':digest(PROTOCOL),
        'verified':True,'summary':summary,'qualification_eligible':False,
        'artifacts':{q.name:digest(q) for q in out.iterdir() if q.is_file()}}
    write(out/'verified.json',saved)
    print({k:v for k,v in summary.items() if k!='coverage'},flush=True)


def profile(n,mode):
    source=read(SOURCE);out=directory(n,mode,True);saved=read(out/'verified.json')
    for k,v in {'players':n,'mode':mode,'smoke':True,'verified':True,'protocol_sha256':digest(PROTOCOL),
                'source_revision':source['revision'],'source_sha256':source['sha256'],'qualification_eligible':False}.items():
        assert saved[k]==v,k
    for name,sha in saved['artifacts'].items():assert Path(name).name==name and digest(out/name)==sha
    assert saved['summary']['games']==4*n and saved['summary']['roots']>0
    assert saved['summary']['game_truncations']==saved['summary']['search_truncations']==0
    seconds=saved['summary']['seconds'];assert math.isfinite(seconds) and seconds>0
    projected=120+2*seconds*read(PROTOCOL)['deals_per_shard'];hours=max(4,math.ceil(projected/(.75*3600)))
    return {'players':n,'mode':mode,'probe_revision':saved['revision'],'verified_sha256':digest(out/'verified.json'),
            'probe_seconds':seconds,'projected_seconds':projected,'timeout_hours':hours,'admitted':hours<=12}


def summarize(smoke):
    source=read(SOURCE);p=read(PROTOCOL);shards={};pending=[]
    for n in p['players']:
        for mode in p['modes']:
            out=directory(n,mode,smoke);key=f'{n}p-{mode}'
            if not (out/'verified.json').exists():pending.append(key);continue
            saved=read(out/'verified.json')
            for k,v in {'players':n,'mode':mode,'smoke':smoke,'verified':True,'prefix':prefix(n,mode,smoke),
                'protocol_sha256':digest(PROTOCOL),'source_revision':source['revision'],
                'source_sha256':source['sha256'],'qualification_eligible':False}.items():assert saved[k]==v,k
            assert re.fullmatch('[a-f0-9]{40}',saved['revision'])
            for name,sha in saved['artifacts'].items():assert Path(name).name==name and digest(out/name)==sha
            summary=saved['summary'];assert summary['games']==4*n*(1 if smoke else p['deals_per_shard'])
            assert summary['game_truncations']==summary['search_truncations']==0
            assert summary['public_model_proposals_reproduced']==summary['roots']>0
            shards[key]={**summary,'revision':saved['revision'],'prefix':saved['prefix'],
                'verified_sha256':digest(out/'verified.json'),'artifacts':saved['artifacts']}
    games=sum(s['games'] for s in shards.values())
    if not pending:assert games==(sum(p['players'])*4*len(p['modes']) if smoke else p['unique_games'])
    result={'smoke':smoke,'all_shards_verified':not pending,'verified_shards':list(shards),'pending_shards':pending,
        'unique_games':games,'engine_game_runs':games*2,'roots':sum(s['roots'] for s in shards.values()),'shards':shards,
        'source_revision':source['revision'],'source_sha256':source['sha256'],'protocol_sha256':digest(PROTOCOL),
        'trained':False,'labels_generated':False,'qualification_eligible':False,
        'scope':'Runtime probes excluded from training data.' if smoke else 'Fresh public positions; no labels, gradients or strength claim.'}
    write(ROOT/('ai/strong/strategic-training-collection-'+('probes-' if smoke else '')+'results-v1.json'),result)
    print({k:result[k] for k in ['smoke','all_shards_verified','verified_shards','pending_shards','unique_games','roots']})


def launch(a):
    source=read(SOURCE);assert digest(PROTOCOL)==source['protocol_sha256']
    assert all(digest(ROOT/name)==sha for name,sha in source['overlays'].items())
    preflight=read(ROOT/'ai/strong/strategic-training-collection-preflight-v1.json')
    assert preflight['source_sha256']==source['sha256'] and preflight['frozen_package_passed']
    record={'players':a.players,'mode':a.mode,'smoke':a.smoke,'stage':'launch_intent',
        'created_at':datetime.now(timezone.utc).isoformat(),'source_revision':source['revision'],
        'source_sha256':source['sha256'],'protocol_sha256':digest(PROTOCOL),'qualification_eligible':False}
    hours=4
    if not a.smoke:
        admission=profile(a.players,a.mode);assert admission['admitted'],'Split work; do not reduce horizons'
        record['runtime_admission']=admission;hours=admission['timeout_hours']
    record['timeout_hours']=hours
    suffix=('smoke-' if a.smoke else '')+f'{a.players}p-{a.mode}'
    guards=ROOT/'ai/runs/strategic-training-collection-launches-v1';guards.mkdir(exist_ok=True)
    guard=guards/(suffix+'.json')
    with guard.open('x') as f:json.dump(record,f,indent=2)
    command=['hf','jobs','run','--detach','--flavor','cpu-performance','--timeout',f'{hours}h',
        '--secrets','HF_TOKEN','--label','project=powergrid-ai','--label','stage=strategic-collection-v1-'+suffix]
    for k,v in {'PLAYERS':str(a.players),'MODE':a.mode,'SMOKE':'1' if a.smoke else '0',
                'SOURCE_ARCHIVE':source['archive'],'SOURCE_REVISION':source['revision'],'SOURCE_SHA256':source['sha256'],
                'HF_HUB_DISABLE_PROGRESS_BARS':'1'}.items():command+=['--env',k+'='+v]
    command+=['--','pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime','bash','-lc','''
set -euo pipefail
python -m pip install --quiet --timeout 120 --retries 5 huggingface_hub==2.0.0 onnxruntime==1.30.0 numpy==2.4.6
mkdir -p /workspace
python - <<'PY'
import urllib.request,tarfile,os,hashlib
from pathlib import Path
from huggingface_hub import hf_hub_download
urllib.request.urlretrieve("https://nodejs.org/dist/v24.14.0/node-v24.14.0-linux-x64.tar.xz","/tmp/node.tar.xz")
with tarfile.open("/tmp/node.tar.xz") as f:f.extractall("/opt")
p=hf_hub_download("coyotte508/powergrid-ai-training-v1",os.environ['SOURCE_ARCHIVE'],repo_type='dataset',revision=os.environ['SOURCE_REVISION'])
assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==os.environ['SOURCE_SHA256']
with tarfile.open(p) as f:f.extractall('/workspace',filter='data')
PY
export PATH=/opt/node-v24.14.0-linux-x64/bin:$PATH
cd /workspace
args=()
if [ "$SMOKE" = 1 ]; then args+=(--smoke); fi
python -u ai/strong/strategic_collection.py "$PLAYERS" "$MODE" ai/runs/strategic-collection-run "${args[@]}" --upload
''']
    try:
        result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,check=True)
        (guards/(suffix+'.log')).write_text(result.stdout+result.stderr)
        ids=set(re.findall(r'\b[0-9a-f]{24}\b',result.stdout));assert len(ids)==1,'Ambiguous submission; inspect existing job label'
        record.update(stage='launched',job_id=ids.pop())
    except BaseException as e:
        record.update(stage='launch_unknown',error=type(e).__name__+': '+str(e));raise
    finally:write(guard,record)
    print(record,flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(__doc__);sub=parser.add_subparsers(dest='command',required=True)
    for verb in ['launch','collect','profile']:
        p=sub.add_parser(verb);p.add_argument('players',type=int,choices=range(2,7));p.add_argument('mode',choices=['economic','search_geo','snapshot0'])
        if verb!='profile':p.add_argument('--smoke',action='store_true')
        if verb=='collect':p.add_argument('revision')
    sub.add_parser('summarize').add_argument('--smoke',action='store_true')
    a=parser.parse_args()
    if a.command=='launch':launch(a)
    elif a.command=='collect':collect(a)
    elif a.command=='summarize':summarize(a.smoke)
    else:
        result=profile(a.players,a.mode);write(ROOT/f'ai/strong/strategic-collection-{a.players}p-{a.mode}-runtime-v1.json',result);print(result)
