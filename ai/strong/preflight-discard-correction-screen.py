"""Exercise every model at2p/6p and mixed-schema A260 in the frozen package."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from huggingface_hub import hf_hub_download

ROOT=Path(__file__).resolve().parents[2]
read=lambda p:json.loads(Path(p).read_text())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
source=read(ROOT/'ai/strong/discard-correction-screen-source-v1.json')
frozen=ROOT/'ai/runs/discard-correction-screen-source-v1'
assert all(sha(frozen/name)==value for name,value in source['overlays'].items())
models=read(frozen/'ai/strong/discard-correction-screen-models-v1.json')
protocol=read(frozen/'ai/strong/discard-correction-screen-protocol-v1.json')
out=ROOT/'ai/runs/discard-correction-screen-preflight-v1';out.mkdir(exist_ok=False)
spec=importlib.util.spec_from_file_location('arena_verifier',ROOT/'ai/strong/collect-population-screen.py')
verifier=importlib.util.module_from_spec(spec);spec.loader.exec_module(verifier)
paths={}
for key,pin in models.items():
    paths[key]=hf_hub_download(protocol['repo'],pin['prefix']+'/inference64.onnx',revision=pin['revision'])
    assert sha(paths[key])==pin['files']['inference64.onnx']
cases=[(key,n,'economic') for key in models for n in [2,6]]+[('10102',3,'a260')]
def smoke(case):
    key,n,opponent=case;name=f'{key}-{opponent}-{n}p';seed='discard-correction-screen-smoke-v1-{players}p'
    screen={'players':n,'opponent':opponent,'games':4*n}
    command=[sys.executable,str(frozen/'ai/strong/evaluate.py'),paths[key],'--players',str(n),
        '--games',str(4*n),'--workers',str(min(8,4*n)),'--seed',seed.format(players=n),
        '--opponent','economic','--output',str(out/(name+'.json'))]
    if opponent=='a260':
        other=next(x for x in protocol['screens'] if x['opponent']=='a260')
        path=hf_hub_download(protocol['repo'],other['model_path'],revision=other['revision'])
        assert sha(path)==other['sha256'];screen['sha256']=other['sha256'];command+=['--opponent-model',path]
    with (out/(name+'.log')).open('w') as log:r=subprocess.run(command,cwd=frozen,stdout=log,stderr=subprocess.STDOUT)
    assert r.returncode==0,(name,(out/(name+'.log')).read_text()[-2000:])
    report=read(out/(name+'.json'))
    summary=verifier.verify_report(report,screen,{'hashes':{'latest.onnx':models[key]['files']['inference64.onnx']}},
        {'seed_template':seed,'deal_offsets':[0]},models[key]['feature_revision'])
    print({'case':name,'games':report['games'],'truncated':report['truncated']},flush=True)
    return name,{'games':report['games'],'artifact_sha256':sha(out/(name+'.json')),'truncated':report['truncated'],
        'search_truncated':sum(x['truncated'] for x in summary['search_stats'].values())}
with ThreadPoolExecutor(max_workers=2) as pool:results=dict(pool.map(smoke,cases))
record={'source_revision':source['revision'],'source_sha256':source['sha256'],'cases':results,
    'games':sum(x['games'] for x in results.values()),'game_truncations':sum(x['truncated'] for x in results.values()),
    'search_truncations':sum(x['search_truncated'] for x in results.values()),'qualification_eligible':False}
assert record['games']==108 and record['game_truncations']==record['search_truncations']==0
(ROOT/'ai/strong/discard-correction-screen-preflight-v1.json').write_text(json.dumps(record,indent=2)+'\n')
print({k:v for k,v in record.items() if k!='cases'})
