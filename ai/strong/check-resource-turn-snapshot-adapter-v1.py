"""One-shot recorded-game validation of the separate A260 resource arena route."""
import argparse
from concurrent.futures import ProcessPoolExecutor,as_completed
from copy import deepcopy
from datetime import datetime,timezone
import json
from pathlib import Path
import shutil
import time

import resource_turn_snapshot_arena_v1 as route

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'ai/runs/resource-turn-snapshot-adapter-v2'
FAILED=ROOT/'ai/runs/resource-turn-snapshot-adapter-v1'
ARTIFACT=ROOT/'ai/runs/resource-turn-full-artifact-v3'
OPPONENT=ROOT/'ai/runs/conservative-auction-development-prepared-v2/source/artifact/final-opponent-a260.onnx'
ORIGINAL=ROOT/'ai/runs/resource-replanning-development-collected-v1/resource-replanning-development-v1-filter-3p-a260-0-4/artifacts/evaluation'
ORIGINAL_MANIFEST=ROOT/'ai/runs/resource-replanning-development-complete-evidence-v1/manifest.json'
RESULT=ROOT/'ai/strong/resource-turn-snapshot-adapter-results-v1.json'
MODES=('filter','model-turn')


def config(mode,output):
    return {'artifact':str(ARTIFACT),'descriptor_sha256':route.DESCRIPTOR_SHA,
        'mode':mode,'players':3,'opponent':'a260','opponent_model':str(OPPONENT),
        'opponent_sha256':route.OPPONENT_SHA,'seed':'resource-replanning-development-v1-3p',
        'start':0,'deals':1,'workers':4,'output':str(output)}


def prepare():
    assert not OUT.exists() and not RESULT.exists(),'Inspect existing preparation or result'
    failed=route.read(FAILED/'failure-summary.json')
    assert failed['completed_replays']==0 and failed['failed_cases']==12
    for name,sha in route.read(FAILED/'plan.json')['code_hashes'].items():
        assert route.digest(FAILED/'original-source'/name)==sha
    assert route.digest(ORIGINAL_MANIFEST)=='fb4cab7da560d86fe1bad88a363c9e83d3bb0aa86344de12368317dc95ae1839'
    original=route.read(ORIGINAL_MANIFEST);inputs={}
    for path in [ORIGINAL/'evaluation.json',*[ORIGINAL/f'decisions-{i}.jsonl' for i in range(12)]]:
        name=str(path.relative_to(ROOT));sha=route.digest(path);assert original[name]==sha;inputs[name]=sha
    report=route.read(ORIGINAL/'evaluation.json')
    assert report['config']['opponent_sha256']==route.OPPONENT_SHA
    assert report['config']['model_sha256']==route.read(ARTIFACT/'resource-full-descriptor.json')['model']['sha256']
    assert report['config']['seed']==config('filter',OUT)['seed']
    ctx=route.context(config('filter',OUT));assert ctx.revision=='3.0'
    OUT.mkdir()
    plan={'created_at':datetime.now(timezone.utc).isoformat(),'scope':'recorded-game-engineering-replay',
        'modes':list(MODES),'episodes':list(range(12)),'distinct_original_games':12,'planned_replays':24,
        'purpose':'Verify the three-player A260 neural-opponent route through the existing v3 public atomic and complete-resource-turn transports. No policy or strategy selection.',
        'code_hashes':{str(p.relative_to(ROOT)):route.digest(p) for p in (
            Path(__file__).resolve(),ROOT/'ai/strong/resource_turn_snapshot_arena_v1.py')},
        'input_hashes':inputs,'original_archive_manifest_sha256':route.digest(ORIGINAL_MANIFEST),
        'artifact_descriptor_sha256':route.DESCRIPTOR_SHA,'artifact_manifest_sha256':route.MANIFEST_SHA,
        'opponent_sha256':route.OPPONENT_SHA,'opponent_feature_revision':'3.0',
        'opponent_hf_revision':'b38515c29e57826de05b55b645c29591e4a886bf',
        'opponent_hf_path':'runs/strong-league-v2-a/best.onnx',
        'preserved_failed_attempt':{'path':str(FAILED.relative_to(ROOT)),
            'summary_sha256':route.digest(FAILED/'failure-summary.json'),
            'plan_sha256':route.digest(FAILED/'plan.json'),
            'correction':'Revision 3.0 opponent observations omit playerOrder; hash only fields the encoder actually emits. Learner ordering remains mandatory and independently replayed.'},
        'new_hf_jobs':0,'new_full_game_trajectories':0,'new_strength_games':0,
        'qualification_eligible':False,'reserved_final_seeds_used':False}
    route.write(OUT/'plan.json',plan)
    print(json.dumps({'prepared':True,'recorded_games':12,'replays':24,'opponent_feature_revision':ctx.revision}),flush=True)


def pins():
    plan=route.read(OUT/'plan.json')
    for key in ('code_hashes','input_hashes'):
        assert all(route.digest(ROOT/name)==sha for name,sha in plan[key].items())
    assert route.digest(ORIGINAL_MANIFEST)==plan['original_archive_manifest_sha256']
    return plan


def one(mode,episode):
    report=route.read(ORIGINAL/'evaluation.json')
    reference={'terminal':next(r['terminal'] for r in report['results'] if r['episode']==episode),
        'decisions':[json.loads(line) for line in (ORIGINAL/f'decisions-{episode}.jsonl').read_text().splitlines()]}
    return route.play(config(mode,OUT/mode),episode,reference)


def tamper_checks(record):
    results=[]
    for key,value in (('opponent_sha256','0'*64),('players',2)):
        c=config('filter',OUT/'filter');c[key]=value
        try:route.context(c)
        except AssertionError:results.append({'case':key,'rejected':True})
        else:raise AssertionError('Wrong snapshot configuration was accepted')
    original_trace=OUT/'filter/snapshot-trace-0.jsonl'
    original_decisions=OUT/'filter/decisions-0.jsonl'
    rows=[json.loads(line) for line in original_trace.read_text().splitlines()]
    position=next(i for i,row in enumerate(rows) if row['actor']=='snapshot0')
    for key,value in (('index',-1),('input_sha256','0'*64),('model_sha256','0'*64),('actor','learner')):
        directory=OUT/('tamper-'+key);directory.mkdir();changed=deepcopy(rows);changed[position][key]=value
        trace=directory/'snapshot-trace-0.jsonl';trace.write_text(''.join(route.wire(row)+'\n' for row in changed))
        shutil.copy2(original_decisions,directory/original_decisions.name)
        modified=deepcopy(record);modified['snapshot']['trace_sha256']=route.digest(trace)
        try:route.audit_snapshot(config('filter',directory),modified,directory)
        except AssertionError:results.append({'case':key,'rejected':True})
        else:raise AssertionError('Corrupted snapshot trace accepted: '+key)
    assert len(results)==6
    route.write(OUT/'tamper-checks.json',results);return results


def execute():
    plan=pins();assert not (OUT/'execution-intent.json').exists(),'Inspect previous execution before recovery'
    route.write(OUT/'execution-intent.json',{'started_at':datetime.now(timezone.utc).isoformat(),
        'plan_sha256':route.digest(OUT/'plan.json')})
    began=time.perf_counter();summaries={};first=None
    for mode in MODES:
        output=OUT/mode;output.mkdir();records=[]
        with ProcessPoolExecutor(max_workers=4) as pool:
            pending={pool.submit(one,mode,episode):episode for episode in plan['episodes']}
            for future in as_completed(pending):
                records.append(future.result());print(json.dumps({'mode':mode,'recorded_games_replayed':len(records),'expected':12}),flush=True)
        records.sort(key=lambda r:r['episode']);c=config(mode,output)
        route.write(output/'evaluation.json',{'config':c,'results':records,'all_complete':True,
            'completed_games':12,'expected_games':12,'errors':[]})
        ctx=route.context(c);audit=ctx.auditor.audit(c,records);assert audit['passed'] and audit['games']==12
        route.write(output/'independent-audit.json',audit)
        snapshots=[route.audit_snapshot(c,record,output) for record in records]
        summaries[mode]={'replayed_games':12,'learner_audit':audit,
            'opponent_predictions_verified':sum(r['opponent_predictions_verified'] for r in snapshots),
            'learner_requests_engine_replayed':sum(r['learner_requests_replayed'] for r in snapshots),
            'all_terminals_exact':all(r['terminal_exact'] for r in snapshots)}
        if mode=='filter':first=records[0]
    negatives=tamper_checks(first);assert pins()==plan
    assessment={'passed':True,'seconds':time.perf_counter()-began,'plan_sha256':route.digest(OUT/'plan.json'),
        'code_hashes':plan['code_hashes'],'input_hashes':plan['input_hashes'],'modes':summaries,
        'distinct_original_games':12,'recorded_game_replays':24,'tampered_inputs_rejected':len(negatives),
        'new_hf_jobs':0,'new_full_game_trajectories':0,'new_strength_games':0,'new_gradients':0,
        'qualification_eligible':False,'reserved_final_seeds_used':False,
        'output_hashes':{str(p.relative_to(OUT)):route.digest(p) for p in sorted(OUT.rglob('*')) if p.is_file()}}
    route.write(OUT/'assessment.json',assessment)
    route.write(RESULT,{'status':'recorded_snapshot_opponent_route_verified_not_strength_tested',
        'assessment_sha256':route.digest(OUT/'assessment.json'),'artifact_descriptor_sha256':route.DESCRIPTOR_SHA,
        'opponent_sha256':route.OPPONENT_SHA,'recorded_game_replays':24,'modes':summaries,
        'tampered_inputs_rejected':len(negatives),'new_hf_jobs':0,'new_full_game_trajectories':0,
        'qualification_eligible':False,'reserved_final_seeds_used':False})
    print(json.dumps({k:v for k,v in assessment.items() if k not in ('code_hashes','input_hashes','output_hashes')}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('operation',choices=['prepare','execute'])
    globals()[parser.parse_args().operation]()
