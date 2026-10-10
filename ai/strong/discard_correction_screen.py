"""Frozen complete-game development comparison, all counts and four rule cells."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
from huggingface_hub import HfApi, hf_hub_download
from five_plant_screen import ROOT, read, write, digest, collect


def run(args):
    protocol_path=ROOT/'ai/strong/discard-correction-screen-protocol-v1.json'
    protocol=read(protocol_path);models=read(ROOT/'ai/strong/discard-correction-screen-models-v1.json')
    pin=models[args.key]
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    status={'key':args.key,'status':'running','protocol_sha256':digest(protocol_path),
        'models_sha256':digest(ROOT/'ai/strong/discard-correction-screen-models-v1.json'),
        'source_revision':os.environ.get('SOURCE_REVISION'),'source_sha256':os.environ.get('SOURCE_SHA256'),
        'qualification_eligible':False}
    def execute(name,argv):
        with (out/(name+'.log')).open('w') as log:subprocess.run(argv,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
    try:
        for filename,sha in pin['files'].items():
            raw=Path(hf_hub_download(protocol['repo'],pin['prefix']+'/'+filename,revision=pin['revision'])).read_bytes()
            (out/filename).write_bytes(raw);assert digest(out/filename)==sha
        pt,onnx=out/'inference64.pt',out/'inference64.onnx'
        fixtures=ROOT/'ai/strong/fixtures/multiplayer-serving-v1.jsonl'
        for script,label,argv in [('check-export.py','parity',[str(pt),str(onnx),str(fixtures)]),
            ('benchmark-serving.py','serving',[str(onnx),str(fixtures)])]:
            execute(label,[sys.executable,str(ROOT/'ai/strong'/script),*argv,'--output',str(out/(label+'.json'))])
        parity,serving=read(out/'parity.json'),read(out/'serving.json')
        assert parity['positions']==serving['positions']==2553 and parity['all_actions_match'] and serving['all_moves_legal']
        assert parity['model_sha256']==serving['model_sha256']==pin['files']['inference64.onnx']
        manifest={'key':args.key,'revision':pin['revision'],'pin':pin,'feature_revision':pin['feature_revision'],
            'hashes':{'latest.onnx':pin['files']['inference64.onnx']},'qualification_eligible':False}
        write(out/'checkpoint.json',manifest)
        for screen in protocol['screens']:
            n,opponent=screen['players'],screen['opponent'];name=f'{opponent}-{n}p.json'
            command=[sys.executable,str(ROOT/'ai/strong/evaluate.py'),str(onnx),'--players',str(n),
                '--games',str(screen['games']),'--workers',str(protocol['workers']),
                '--seed',protocol['seed_template'].format(players=n),'--opponent','economic' if opponent=='a260' else opponent,
                '--output',str(out/name)]
            if opponent=='a260':
                other=hf_hub_download(protocol['repo'],screen['model_path'],revision=screen['revision'])
                assert digest(other)==screen['sha256'];command+=['--opponent-model',other]
            execute(name,command)
            print({'key':args.key,'cell':name,'stage':'completed'},flush=True)
        summary=collect(out,{'evaluation':protocol},manifest);write(out/'summary.json',summary)
        status.update(status='complete',games=sum(v['games'] for v in summary['cells'].values()),cells=len(summary['cells']),truncations=0)
        assert status['games']==1600 and status['cells']==7
    except BaseException as e:
        status.update(status='failed',error=type(e).__name__+': '+str(e));raise
    finally:
        status['artifacts']={p.name:digest(p) for p in out.iterdir() if p.is_file() and p.suffix not in ['.pt','.onnx']}
        write(out/'screen-check.json',status)
        if args.upload:HfApi().upload_folder(repo_id=protocol['repo'],folder_path=out,path_in_repo='runs/discard-correction-screen-v1-'+args.key,ignore_patterns=['*.pt','*.onnx'])
        print(status,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('key',choices=['parent','10101','10102']);p.add_argument('output',type=Path);p.add_argument('--upload',action='store_true');run(p.parse_args())
