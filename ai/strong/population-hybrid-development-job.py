"""One fixed paired shard of the population-hybrid development screen."""
import argparse
import os
import subprocess
import sys
import time

from huggingface_hub import hf_hub_download
from strategic_collection import ROOT,read,write,digest
from policy_iteration_evidence_archive import upload_evidence
from population_hybrid_development import PROTOCOL,contract,case_key,expected_config
from population_policy_verification import verify_evaluation


def run(arm,players,opponent,start,end):
    protocol=read(PROTOCOL);cell=contract(protocol,arm,players,opponent,start,end)
    assert digest(PROTOCOL)==os.environ['PROTOCOL_SHA256']
    key=case_key(arm,players,opponent,start,end)
    out=ROOT/'ai/runs'/key;out.mkdir(parents=True,exist_ok=False)
    pin=protocol['model_pin']
    status={'stage':'running','case':key,'source_revision':os.environ['SOURCE_REVISION'],
        'source_sha256':os.environ['SOURCE_SHA256'],'protocol_sha256':digest(PROTOCOL),
        'model_pin':pin,'qualification_eligible':False,'reserved_final_seeds_used':False}
    begin=time.perf_counter()
    try:
        model=hf_hub_download(pin['repo'],pin['prefix']+'/inference64.onnx',revision=pin['revision'])
        assert digest(model)==pin['files']['inference64.onnx']
        cmd=[sys.executable,'-u','ai/strong/evaluate-population-policy.py','--model',model,
            '--runtime',str(ROOT),'--arm',arm,'--players',str(players),'--opponent',opponent,
            '--seed',protocol['seed_template'].format(players=players),'--start',str(start),
            '--deals',str(end-start),'--samples','8','--workers','8','--search-workers','1',
            '--output',str(out/'evaluation')]
        if opponent=='a260':
            other=hf_hub_download(pin['repo'],cell['model_path'],revision=cell['revision'])
            assert digest(other)==cell['sha256'];cmd+=['--opponent-model',other]
        with (out/'evaluation.log').open('w') as log:
            with subprocess.Popen(cmd,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True) as child:
                for line in child.stdout:log.write(line);log.flush();print(line,end='',flush=True)
                if child.wait():raise subprocess.CalledProcessError(child.returncode,cmd)
        summary=verify_evaluation(out/'evaluation',expected_config(protocol,arm,players,opponent,start,end))
        write(out/'summary.json',summary)
        status.update(stage='complete',games=summary['games'])
    except BaseException as error:
        status.update(stage='failed',error=type(error).__name__+': '+str(error));raise
    finally:
        status['seconds']=time.perf_counter()-begin;write(out/'development-check.json',status)
        write(out/'manifest.json',{str(p.relative_to(out)):digest(p) for p in sorted(out.rglob('*')) if p.is_file()})
        evidence=upload_evidence(out);print({**status,'evidence':evidence},flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument('arm');parser.add_argument('players',type=int);parser.add_argument('opponent')
    parser.add_argument('start',type=int);parser.add_argument('end',type=int)
    args=parser.parse_args();run(args.arm,args.players,args.opponent,args.start,args.end)
