"""Archive atomic execution checks and full-game smokes without claiming strength."""
import json
from pathlib import Path
import shutil
import statistics

from strategic_collection import ROOT,read,write,digest
from policy_iteration_evidence_archive import upload_evidence


def semantic(d):
    if isinstance(d,dict):return {str(k):semantic(v) for k,v in d.items() if k!='elapsedMs'}
    if isinstance(d,list):return [semantic(v) for v in d]
    return d


def verify_plan(plan,seat):
    bundles=plan['bundles'];s=plan['search'];rows=plan['receipts']
    assert s['usable'] and not s['truncated']
    assert len(rows)==len(bundles)*s['samples']==s['evaluations']
    scores={b['id']:[] for b in bundles}
    for i,row in enumerate(rows):
        sample,index=divmod(i,len(bundles));b=bundles[index]
        assert row['env']==i and row['sample']==sample and row['actionIndex']==index
        assert row['resourceTurn']['actions']==b['actions'] and row['resourceTurn']['bundleId']==b['id']
        assert not row['truncated'] and sum(row['policyDecisions'].values())==row['steps']
        assert row['initialBelief']==s['worlds'][str(sample)]['initialBelief']
        values=[(p['powered'],p['money'],p['cities']) for p in row['terminal']]
        winners=[k for k,v in enumerate(values) if v==max(values)]
        assert row['value']==(1/len(winners) if seat in winners else 0)
        scores[b['id']].append(row['value'])
    assert scores==s['sampleOutcomes']
    means={k:sum(v)/len(v) for k,v in scores.items()};assert means==s['meanCredits']
    choice=max(range(len(bundles)),key=lambda i:(means[bundles[i]['id']],i==plan['baseline'],-i))
    assert choice==plan['selected'] and plan['actions']==bundles[choice]['actions']


def main():
    base=ROOT/'ai/runs/resource-replanning-v1';runtime=base/'runtime';prep=read(base/'preparation.json')
    for name,sha in {**prep['runtime_hashes'],**prep['new_files']}.items():assert digest(runtime/name)==sha
    for name,sha in prep['new_files'].items():assert digest(ROOT/name)==sha
    for name,sha in read(ROOT/'ai/strong/population-hybrid-development-plan-v1.json')['dependency_hashes'].items():assert digest(ROOT/name)==sha
    failed=read(base/'checks/assessment.json');fixed=read(base/'checks-v2/assessment.json')
    assert not failed['passed'] and fixed['passed']
    assert failed['checker_sha256']==digest(base/'failed-probe-v1.py')
    assert fixed['checker_sha256']==digest(ROOT/'ai/strong/probe-resource-replanning-v1.py')
    old=(base/'failed-probe-v1.py').read_text();new=(ROOT/'ai/strong/probe-resource-replanning-v1.py').read_text()
    assert new.replace('str(k):semantic(v)','k:semantic(v)').replace("BASE/'checks-v2'","BASE/'checks'")==old
    diagnosis=read(base/'serialization-diagnosis.json')
    assert diagnosis['same_move'] and diagnosis['equal_after_json_roundtrip'] and not diagnosis['policy_changes_required']
    for folder,report in [('checks',failed),('checks-v2',fixed)]:
        assert report['preparation_sha256']==digest(base/'preparation.json')
        assert report['selection_sha256']==digest(base/'selection.json')
        for name,sha in report['artifacts'].items():assert digest(base/folder/name)==sha
    assert fixed['outside_resource_positions']==1798 and fixed['turns']==23 and fixed['decisions']==112
    assert fixed['searched_decisions']==111 and fixed['rollouts']==4744 and fixed['caps']==0
    rows=[json.loads(l) for l in (base/'checks-v2/turns.jsonl').open()]
    previous=[json.loads(l) for l in (base/'checks/turns.jsonl').open()]
    assert len(rows)==len(previous)==23
    timings=[];changed=[];phase_rollouts=0
    for old_row,row in zip(previous,rows):
        assert row['label']==old_row['label'] and row['actual_actions']==old_row['actual_actions']
        assert row['initial']==old_row['initial'] and row['final']==old_row['final']
        for old_d,d in zip(old_row['decisions'],row['decisions']):
            r=d['result'];assert semantic(old_d['result'])==semantic(r)
            assert r['executionMode']=='stateless-atomic-resource-replanning-v1'
            timings.append(r['elapsedMs'])
            if r['resourcePlan']:
                verify_plan(r['resourcePlan'],d['request']['player'])
                assert r['move']==r['resourcePlan']['firstMove']==r['resourcePlan']['actions'][0]
                phase_rollouts+=r['search']['evaluations']
        if row['quantity_changed']:changed.append({k:row[k] for k in ['label','initial_planned_counts','actual_counts']})
    assert phase_rollouts==4744
    assert changed==[{'label':'early-2p-recharged-sealed','initial_planned_counts':[2,0,0,0],'actual_counts':[4,0,0,0]}]
    known=next(r for r in rows if r['label']=='known-resource-omission')
    assert known['actual_counts']==[3,0,0,0] and known['price']==17
    expected_standalone=next(r for r in rows if r['label']=='late-6p-recharged-sealed')['decisions'][0]['result']
    standalone=read(base/'checks-v2/standalone.json')['responses']
    assert len(standalone)==3 and 'error' in standalone[0] and 'move' not in standalone[0]
    for response,request_id,revision in zip(standalone[1:],['first-cli','retry-cli'],[17,18]):
        assert response['requestId']==request_id and response['revision']==revision
        assert semantic(response['decision'])==semantic(expected_standalone)
    capped=read(base/'checks-v2/cap.json')
    assert capped['search']['truncated']>0 and capped['index']==capped['modelProposal']
    assert capped['resourcePlan']['selected']==capped['resourcePlan']['baseline']
    replay=read(base/'replays/assessment.json')
    assert replay['passed'] and replay['games']==4 and replay['learner_moves']==540
    assert replay['opponent_moves']==1454 and replay['resource_moves']==167
    games=read(base/'games/assessment.json')
    assert games['passed'] and len(games['records'])==4 and not games['errors']
    assert games['checker_sha256']==digest(ROOT/'ai/strong/probe-resource-replanning-games-v1.py')
    expected={r['label']:r for r in read(base/'selection.json')['game_smokes']}
    game_rollouts=game_decisions=game_resource=0;game_timings={}
    for entry in games['records']:
        label=entry['label'];case=expected[label];folder=base/'games'/label
        config=read(folder/'config.json');record=entry['result'];episode=case['episode']
        assert digest(folder/'config.json')==entry['config_sha256'] and config['arm']=='resource-filter'
        assert digest(folder/f'decisions-{episode}.jsonl')==entry['receipt_sha256']==record['decision_receipt_sha256']
        assert read(folder/f'game-{episode}.json')==record
        assert not record['terminal']['truncated'] and not record['rollout_caps']
        decisions=[json.loads(l) for l in (folder/f'decisions-{episode}.jsonl').open()]
        assert len(decisions)==record['decisions'];count=rollouts=0
        for i,r in enumerate(decisions):
            assert r['decision']==i+1 and r['arm']=='resource-filter'
            if r['resourcePlan']:
                verify_plan(r['resourcePlan'],record['terminal']['seat'])
                assert r['move']==r['resourcePlan']['actions'][0]
                assert r['modelProposal']==r['resourcePlan']['baselineDecisions'][0]['index']
                count+=1;rollouts+=r['search']['evaluations']
            else:assert r['search'] is None
        assert count==entry['resource_decisions'] and rollouts==record['rollouts']
        searched=[r for r in decisions if r['resourcePlan']]
        game_timings[label]={'samples':len(searched),'median_ms':statistics.median(r['elapsedMs'] for r in searched),
            'maximum_ms':max(r['elapsedMs'] for r in searched)}
        slow=read(base/'replays'/(label+'-slow-root.json'))
        assert slow['reference']==max(searched,key=lambda r:r['elapsedMs'])
        assert slow['request']['state']['seed']=='secret' and slow['request']['state']['powerPlantsDeck']==[]
        game_decisions+=len(decisions);game_resource+=count;game_rollouts+=rollouts
    summary={'status':'verified_stateless_resource_replanning_research_only',
        'outside_resource_exact_controls':1798,'resource_turns':23,'atomic_decisions':112,
        'resource_searches':111,'phase_probe_rollouts':4744,'normal_caps':0,
        'observed_initial_plan_changes':changed,'known_omission_actual_buys':[3,0,0,0],
        'fresh_process_exact':True,'interleaved_request_exact':True,'standalone_exact':True,
        'deliberate_cap_returns_model_action':True,
        'full_engineering_games':4,'game_decisions':game_decisions,'game_resource_searches':game_resource,
        'game_rollouts':game_rollouts,'game_caps':0,
        'independent_replay_learner_moves':540,'independent_replay_opponent_moves':1454,
        'retained_slow_public_roots':4,'local_HX370_full_game_resource_timings':game_timings,
        'source_frozen_files_unchanged':1463,'all_inherited_files_unchanged':1467,
        'active_screen_dependencies_unchanged':True,
        'preserved_failure':'First standalone assertion compared live integer dictionary keys with JSON string keys. Exact after roundtrip; only verifier normalization and output directory changed. Original failure, checker and reproduction retained.',
        'local_HX370_atomic_ms':{'samples':len(timings),'median':statistics.median(timings),'maximum':max(timings)},
        'limits':['Stateless replanning is a distinct policy from committing the evaluated macro; four-world valuations assume the macro then model continuations.',
            'The one changed opening is an observed behavioral difference, not an established improvement or regression.',
            'Four games are integration smokes only: economic opponent, seat0, 2p/6p and two rule combinations.',
            'No fresh strength comparison, actual8840U benchmark, live platform integration or deployment qualification.',
            'Frozen canonical sealed-order limitation outside resources remains; later runtime must include the separately tested repair.'],
        'next':'Complete existing fixed hybrid screen, then compare the actual stateless resource policy on fresh paired games across all counts/rules/opponents. Preserve macro teacher as a separate policy. Pin any adopted async repair and benchmark the actual final runtime on 8840U.',
        'new_hf_jobs':0,'new_strength_games':0,'new_engineering_games':4,'gradients':False,
        'qualification_eligible':False,'reserved_final_seeds_used':False}
    evidence=ROOT/'ai/runs/resource-replanning-evidence-v1';assert not evidence.exists();evidence.mkdir()
    sources=[p for p in base.rglob('*') if p.is_file() and 'runtime' not in p.relative_to(base).parts]
    sources += [ROOT/'ai/strong'/name for name in ['resource_replanning_policy_v1.py','evaluate-resource-replanning-v1.py',
        'resource-execution-probe-v1.cjs','probe-resource-replanning-v1.py','probe-resource-replanning-games-v1.py',
        'collect-resource-replanning-v1.py','replay-resource-replanning-games-v1.cjs','resource-turn-search-evidence-v1.json',
        'population-hybrid-development-source-v1.json','population-hybrid-development-plan-v1.json',
        'policy_iteration_evidence_archive.py']]
    for source in sources:
        dest=evidence/source.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)
    write(evidence/'assessment.json',summary)
    write(evidence/'manifest.json',{str(p.relative_to(evidence)):digest(p) for p in evidence.rglob('*') if p.is_file()})
    receipt=upload_evidence(evidence);write(ROOT/'ai/strong/resource-replanning-evidence-v1.json',{**summary,**receipt})
    print(json.dumps({**receipt,'game_rollouts':game_rollouts,'game_decisions':game_decisions},indent=2))


if __name__=='__main__':main()
