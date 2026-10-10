"""Independent-opponent extension, sharded by frozen model and player count."""
import argparse
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
from huggingface_hub import HfApi, hf_hub_download
from five_plant_screen import ROOT, read, write, digest, summarize

spec=importlib.util.spec_from_file_location('opponent_verifier',ROOT/'ai/strong/collect-population-screen.py')
verifier=importlib.util.module_from_spec(spec);spec.loader.exec_module(verifier)


def collect(out, protocol, pin, n, smoke=False):
    result={}
    for opponent,deals in protocol['opponents'].items():
        deals=1 if smoke else deals
        screen={'players':n,'opponent':opponent,'games':deals*4*n}
        evaluation={**protocol,'deal_offsets':list(range(deals)),
            'seed_template':protocol['smoke_seed_template' if smoke else 'seed_template']}
        path=out/(opponent+'.json');report=read(path)
        stats=verifier.verify_report(report,screen,{'hashes':{'latest.onnx':pin['files']['inference64.onnx']}},evaluation,pin['feature_revision'])
        rows=report['results']
        assert {r['episode'] for r in rows}==set(range(screen['games']))
        assert all(r['seat']==r['roles'].index('learner') and r['win']==r['value'][r['seat']] for r in rows)
        result[opponent]={**summarize(rows,evaluation),'artifact_sha256':digest(path),'seconds':report['seconds'],
            'search_stats':stats['search_stats'],'by_rules':{v+('/sealed' if s else '/open'):summarize(
                [r for r in rows if r['variant']==v and r['sealed']==s],evaluation)
                for v in ['original','recharged'] for s in [False,True]}}
    return result


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('key',choices=['parent','10101','10102'])
    p.add_argument('players',type=int,choices=range(2,7));p.add_argument('output',type=Path)
    p.add_argument('--smoke',action='store_true');p.add_argument('--upload',action='store_true');a=p.parse_args()
    protocol_path=ROOT/'ai/strong/discard-opponents-protocol-v1.json';protocol=read(protocol_path)
    models_path=ROOT/'ai/strong/discard-correction-screen-models-v1.json';pin=read(models_path)[a.key]
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    status={'status':'running','key':a.key,'players':a.players,'smoke':a.smoke,
        'protocol_sha256':digest(protocol_path),'models_sha256':digest(models_path),
        'source_revision':os.environ.get('SOURCE_REVISION'),'source_sha256':os.environ.get('SOURCE_SHA256'),
        'qualification_eligible':False}
    try:
        model=hf_hub_download(protocol['repo'],pin['prefix']+'/inference64.onnx',revision=pin['revision'])
        assert digest(model)==pin['files']['inference64.onnx'];write(out/'checkpoint.json',pin)
        for opponent,deals in protocol['opponents'].items():
            deals=1 if a.smoke else deals
            seed=protocol['smoke_seed_template' if a.smoke else 'seed_template'].format(players=a.players)
            command=[sys.executable,str(ROOT/'ai/strong/evaluate.py'),model,'--players',str(a.players),
                '--games',str(deals*4*a.players),'--workers',str(protocol['workers']),
                '--seed',seed,'--opponent',opponent,'--output',str(out/(opponent+'.json'))]
            with (out/(opponent+'.log')).open('w') as log:subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
            report=read(out/(opponent+'.json'))
            print({'key':a.key,'players':a.players,'opponent':opponent,'games':report['games'],'seconds':report['seconds']},flush=True)
        summary=collect(out,protocol,pin,a.players,a.smoke);write(out/'summary.json',summary)
        status.update(status='complete',games=sum(v['games'] for v in summary.values()),
            game_truncations=0,search_truncations=0)
    except BaseException as e:
        status.update(status='failed',error=type(e).__name__+': '+str(e));raise
    finally:
        status['artifacts']={p.name:digest(p) for p in out.iterdir() if p.is_file()}
        write(out/'screen-check.json',status)
        if a.upload:HfApi().upload_folder(repo_id=protocol['repo'],folder_path=out,
            path_in_repo='runs/discard-opponents-'+('smoke-' if a.smoke else '')+f'v1-{a.key}-{a.players}p')
        print(status,flush=True)


if __name__=='__main__':main()
