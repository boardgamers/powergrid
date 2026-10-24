"""One whole-deal HF CPU runtime probe; never a strength or qualification screen."""
import argparse
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

from huggingface_hub import hf_hub_download
from strategic_collection import ROOT, read, write, digest
from policy_iteration_evidence_archive import upload_evidence


def main(players):
    protocol_path=ROOT/'ai/strong/population-hybrid-development-protocol-v1.json'
    protocol=read(protocol_path);pin=protocol['model_pin']
    assert players in [2,6]
    assert digest(protocol_path)==os.environ['PROTOCOL_SHA256']
    assert pin['key']=='frozen-1' and pin['training_verified']
    out=ROOT/f'ai/runs/population-hybrid-runtime-v2-{players}p';out.mkdir(parents=True,exist_ok=False)
    status={'players':players,'stage':'running','source_revision':os.environ['SOURCE_REVISION'],
        'source_sha256':os.environ['SOURCE_SHA256'],'protocol_sha256':digest(protocol_path),
        'model_pin':pin,'cpu_count':os.cpu_count(),'processor':platform.processor(),
        'arm':'combined','opponent':'search_geo','deals':1,'workers':8,'samples':8,'search_workers':1,
        'qualification_eligible':False,'reserved_final_seeds_used':False,
        'scope':'Full paired endpoint runtime pilot, excluded from fresh strength comparisons.'}
    start=time.perf_counter()
    try:
        model=Path(hf_hub_download(pin['repo'],pin['prefix']+'/inference64.onnx',revision=pin['revision']))
        assert digest(model)==pin['files']['inference64.onnx']
        cmd=[sys.executable,'-u','ai/strong/evaluate-population-policy.py','--model',str(model),
            '--runtime',str(ROOT),'--arm','combined','--players',str(players),'--opponent','search_geo',
            '--seed',protocol['smoke_seed_template'].format(players=players),'--deals','1','--samples','8',
            '--workers','8','--search-workers','1','--output',str(out/'evaluation')]
        with (out/'evaluation.log').open('w') as log:
            with subprocess.Popen(cmd,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True) as child:
                for line in child.stdout:
                    log.write(line);log.flush();print(line,end='',flush=True)
                if child.wait():raise subprocess.CalledProcessError(child.returncode,cmd)
        report=read(out/'evaluation/evaluation.json')
        assert report['all_complete'] and report['completed_games']==4*players
        assert report['game_caps']==report['rollout_caps']==0 and not report['errors']
        assert all(not stats['truncated'] for r in report['results'] for stats in r['terminal']['searchStats'].values())
        status.update(stage='complete',games=report['completed_games'],evaluation_seconds=report['seconds'],
            rollouts=sum(r['rollouts'] for r in report['results']),
            decisions=sum(r['decisions'] for r in report['results']),
            game_caps=0,rollout_caps=0)
    except BaseException as error:
        status.update(stage='failed',error=type(error).__name__+': '+str(error))
        raise
    finally:
        status['seconds']=time.perf_counter()-start
        write(out/'runtime-check.json',status)
        write(out/'manifest.json',{str(p.relative_to(out)):digest(p) for p in sorted(out.rglob('*')) if p.is_file()})
        evidence=upload_evidence(out)
        print({**status,'evidence':evidence},flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('players',type=int,choices=[2,6])
    main(parser.parse_args().players)
