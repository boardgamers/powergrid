"""Independently verify immutable bootstrap artifacts and paired plan coverage."""
import argparse
import json
import math
from pathlib import Path

from huggingface_hub import HfApi, hf_hub_download
from data import atomic_json, digest

REPO='coyotte508/powergrid-ai-multimap-v1'
REVISION='43695d4238afb3ba46aeb39e035745026303ab7f'
PREFIX='runs/multimap-bootstrap-20261102-v1-r1/'
JOB='6ae8c1a2c78863f9c630c44f'


def audit(output,replay=8):
    assert HfApi().inspect_job(job_id=JOB).status.stage=='COMPLETED'
    manifest_path=hf_hub_download(REPO,PREFIX+'artifacts.json',revision=REVISION)
    manifest=json.loads(Path(manifest_path).read_text())
    def download(name):
        path=Path(hf_hub_download(REPO,PREFIX+name,revision=REVISION))
        if digest(path)!=manifest[name]:raise RuntimeError(f'Hash mismatch: {name}')
        return path
    # Includes both checkpoint states; no bulk training data download needed.
    files={name:download(name) for name in manifest}
    status=json.loads(files['status.json'].read_text())
    assert status['stage']=='complete' and status['qualified'] is False
    plan=json.loads(files['development/plan.json'].read_text())
    assert plan['checkpointSha256']==manifest['model/best.pt']
    results=[json.loads(line) for line in files['development/games.jsonl'].read_text().splitlines()]
    expected={(s['seed'],seat,policy):s for s,seat,policy in plan['tasks']}
    actual={}
    for result in results:
        key=(result['spec']['seed'],result['seat'],result['policy'])
        assert key not in actual and key in expected
        s={k:v for k,v in result['spec'].items() if k not in ('focalSeat','focalTeacher')}
        assert s==expected[key]
        assert result['terminal'] and math.isfinite(result['credit']) and 0<=result['credit']<=1
        assert 0<result['steps']<=s['maxSteps']
        actual[key]=result
    assert set(actual)==set(expected) and len(results)==1920
    from evaluate import summarize,init_worker,one_game
    recomputed=summarize(results)
    recorded=json.loads(files['development/summary.json'].read_text())
    assert recomputed==recorded
    selection=json.loads(files['model/transfer.json'].read_text())
    history=json.loads(files['model/history.json'].read_text())
    best=min(history,key=lambda h:h['validation']['macroCellPolicyLoss'])
    assert best['epoch']==selection['selectedEpoch']
    grouped={}
    for cell,stats in recorded['cells'].items():
        map_name,count,variant,fast=cell.split('|')
        for group in ('map:'+map_name,'players:'+count,'auction:'+fast,'variant:'+variant):
            grouped.setdefault(group,[]).append(stats)
    groups={k:{p:sum(c[p]['winCredit'] for c in cells)/len(cells) for p in ('model','teacher')} for k,cells in grouped.items()}
    for row in groups.values():row['difference']=row['model']-row['teacher']
    replays=[]
    if replay:
        init_worker(files['model/best.pt'])
        # Fixed sampling over the sorted plan, not cherry-picked outcomes.
        tasks=sorted(plan['tasks'],key=lambda t:(t[0]['seed'],t[1],t[2]))
        for index in range(replay):
            task=tasks[index*len(tasks)//replay]
            repeated=one_game(task)
            original=actual[(task[0]['seed'],task[1],task[2])]
            for field in ('terminal','credit','steps','rounds'):
                assert repeated[field]==original[field],(task,field)
            replays.append(dict(seed=task[0]['seed'],seat=task[1],policy=task[2],matched=True))
    report=dict(repo=REPO,revision=REVISION,jobId=JOB,artifactManifestSha256=digest(manifest_path),
        checkpointSha256=manifest['model/best.pt'],artifactsVerified=len(manifest),games=1920,pairs=960,
        independentDeals=len({s['seed'] for s,_,_ in plan['tasks']}),failures=0,
        macroCellDifference=recorded['macroCellDifference'],groups=groups,selectedEpoch=best['epoch'],
        validation=best['validation']['all'],validationByPhase={k:v for k,v in best['validation'].items() if k.startswith('phase:')},
        transfer=selection['metrics']['all'],trainingSeconds=history[-1]['elapsedSeconds'],replays=replays,
        qualified=False,decision='Reject standalone clone for strength; retain only as representation warm-start. Diagnose phase errors and test policy improvement anchored to the stronger heuristic.',
        caveat='Two independent deals per configuration; all-seat repetitions are paired, not independent extra deals. No final-test or human-strength claim.')
    atomic_json(output,report)
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--replay',type=int,default=8)
    a=p.parse_args();audit(a.output,a.replay)
