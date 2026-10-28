"""Test stable sampling assumptions across 20 predetermined recorded turns.

No model inference, rollout, full-game trajectory, HF job or policy selection.
This is a mechanism check; it cannot establish that commitment improves play.
"""
from collections import Counter
import json
from pathlib import Path
import subprocess
import sys
import time

from public_policy_development_job_v1 import read,digest

ROOT=Path(__file__).resolve().parents[2]
RUNTIME=ROOT/'ai/runs/resource-replanning-job-source-prepared-v1/layout'
MANIFEST_SHA='cebda6cb0ed6a1eff28cad8cd02cb17e37bb62f59595b2237b989337b40a9415'
OUT=ROOT/'ai/runs/resource-sampling-anchor-v1-validated'
RESULT=ROOT/'ai/strong/resource-sampling-anchor-results-v1.json'
PRIOR=ROOT/'ai/runs/resource-replanning-development-collected-v1'
ARCHIVE=ROOT/'ai/runs/resource-replanning-development-complete-evidence-v1/manifest.json'
ARCHIVE_SHA='fb4cab7da560d86fe1bad88a363c9e83d3bb0aa86344de12368317dc95ae1839'
ROOT_FILES={
 'resource-turn-full-integration-v1':'0451d6e1189a9c0008386efc13cbcff0d54ab28290a521b19f42fb243b86f227',
 'resource-turn-full-integration-recovered-v1':'61e59190b8084292d757e06febe9a6fa847a183bf6ce1fc80c71bab5ec77b40a'}
PASS={'name':'Pass','data':True}


def write(path,value):
    with path.open('x') as stream:json.dump(value,stream,indent=2,allow_nan=False);stream.write('\n')


def latent(world):
    # Public cash/inventory deliberately change after buying. These three parts
    # define the random assumptions that must remain common within the turn.
    return {k:world[k] for k in ('deckSha256','roles','rolloutRngPrefix')}


def main():
    assert not OUT.exists() and not RESULT.exists(),'Inspect existing outcome; never repeat silently'
    assert digest(RUNTIME/'resource-job-manifest.json')==MANIFEST_SHA
    hashes=read(RUNTIME/'resource-job-manifest.json')
    assert all(digest(RUNTIME/name)==sha for name,sha in hashes.items())
    sys.path.insert(0,str(RUNTIME/'ai/strong'))
    from hybrid_search import public_seed
    assert digest(Path(sys.modules['hybrid_search'].__file__))==hashes['ai/strong/hybrid_search.py']
    assert digest(ARCHIVE)==ARCHIVE_SHA;archive=read(ARCHIVE)
    inputs={};roots=[]
    for name,sha in ROOT_FILES.items():
        path=ROOT/'ai/runs'/name/'search-roots.jsonl';assert digest(path)==sha
        inputs[str(path.relative_to(ROOT))]=sha
        roots.extend(json.loads(line) for line in path.read_text().splitlines())
    assert [(r['players'],r['episode']) for r in roots]==[(n,e) for n in range(2,7) for e in range(4)]
    OUT.mkdir();began=time.perf_counter();counts=Counter();cases=[]
    code={str(Path(__file__).relative_to(ROOT)):digest(__file__),
        'ai/strong/resource-sampling-anchor-probe-v1.cjs':digest(Path(__file__).with_name('resource-sampling-anchor-probe-v1.cjs'))}
    write(OUT/'design.json',{'selection':'First previously selected resource-search turn, economic opponent, seat zero, every 2–6 player/rule cell. Traverse its recorded atomic purchases through Pass; do not select by plan changes or wins.',
        'root_inputs':inputs,'runtime_manifest_sha256':MANIFEST_SHA,'original_archive_manifest_sha256':ARCHIVE_SHA,
        'controls':['recorded state-dependent sampling seed','first decision seed held fixed across the turn','private-field pollution'],
        'samples_per_position':8,'code_hashes':code,'new_inference':False,'new_hf_jobs':0,
        'rollouts':0,'new_full_game_trajectories':0,'qualification_eligible':False})
    stderr=(OUT/'probe.stderr.log').open('x')
    worker=subprocess.Popen(['node',str(ROOT/'ai/strong/resource-sampling-anchor-probe-v1.cjs'),str(RUNTIME)],
        stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=stderr,text=True,bufsize=1)
    def call(value):
        worker.stdin.write(json.dumps(value,allow_nan=False)+'\n');worker.stdin.flush()
        line=worker.stdout.readline();assert line,'Sampling probe exited; inspect stderr'
        return json.loads(line)
    try:
        with (OUT/'positions.jsonl').open('x') as output:
            for root in roots:
                n,episode=root['players'],root['episode']
                path=PRIOR/f'resource-replanning-development-v1-resource-filter-{n}p-economic-0-4/artifacts/evaluation/decisions-{episode}.jsonl'
                sha=digest(path);assert sha==archive[str(path.relative_to(ROOT))];inputs[str(path.relative_to(ROOT))]=sha
                rows=[json.loads(line) for line in path.read_text().splitlines()]
                first=root['recorded_atomic_decision'];start=first['decision']-1
                assert rows[start]==first and first['resourcePlan'] is not None
                call({'op':'reset','request':root['request']})
                anchor=first['resourcePlan']['search']['seed'];previous=None;reference=None
                local=Counter();turn=[];closed=False
                for row in rows[start:]:
                    assert row['round']==first['round']
                    plan=row['resourcePlan']
                    baseline=[d['move'] for d in plan['baselineDecisions']] if plan else [PASS]
                    if plan is None:assert row['move']==PASS
                    prepared=call({'op':'prepare','baselineActions':baseline});current=public_seed(prepared)
                    if plan:
                        assert current==plan['search']['seed'],'Recorded public sampling seed did not replay'
                        assert prepared['bundles']==plan['bundles'] and prepared['baseline']==plan['baseline']
                    sampled=call({'op':'inspect','currentSeed':current,'anchorSeed':anchor,'samples':8})
                    stable=[latent(w) for w in sampled['anchored']]
                    if reference is None:reference=stable
                    assert stable==reference,'Anchored latent worlds drifted within a recorded turn'
                    assert sampled['hiddenFieldControl']
                    local.update(positions=1,anchored_worlds_checked=8,hidden_field_controls=1,recorded_searches=int(plan is not None))
                    event={'players':n,'episode':episode,'decision':row['decision'],'round':row['round'],
                        'move':row['move'],'anchor_seed':anchor,'current_seed':current,'sampling':sampled,
                        'recorded_search':plan is not None}
                    if previous:
                        local['transitions']+=1;local['state_seed_changes']+=current!=previous['current_seed']
                        for key in ('deckSha256','roles','rolloutRngPrefix'):
                            local['resampled_'+key+'_changes']+=any(a[key]!=b[key] for a,b in zip(sampled['resampled'],previous['sampling']['resampled']))
                    transition=call({'op':'move','move':row['move'],'anchorSeed':anchor})
                    event['transition']=transition
                    if row['move']['name']=='BuyResource':
                        local['private_world_transition_controls']+=transition['privateWorldTransitionControls']
                        local['historical_baseline_metadata_mismatches']+=transition['historicalBaselineMetadata']!=transition['publicMetadata']
                    output.write(json.dumps(event,allow_nan=False)+'\n');output.flush();turn.append(row['move']);previous=event
                    if row['move']==PASS:closed=True;break
                assert closed and turn[-1]==PASS
                counts.update(local);cases.append({'players':n,'episode':episode,'counts':dict(local),
                    'recorded_actions':turn,'root_sha256':inputs[str((ROOT/'ai/runs'/('resource-turn-full-integration-v1' if len(cases)<17 else 'resource-turn-full-integration-recovered-v1')/'search-roots.jsonl').relative_to(ROOT))]})
                print(json.dumps({'completed_turn_checks':len(cases),'expected':20}),flush=True)
        worker.stdin.close();assert worker.wait(timeout=30)==0;stderr.close()
        assert all(digest(ROOT/name)==sha for name,sha in {**inputs,**code}.items())
        report={'passed':True,'turns':len(cases),'counts':dict(counts),'cases':cases,'input_hashes':inputs,
            'code_hashes':code,'runtime_manifest_sha256':MANIFEST_SHA,'seconds':time.perf_counter()-began,
            'output_hashes':{p.name:digest(p) for p in OUT.iterdir() if p.is_file()},
            'new_inference':False,'rollouts':0,'new_full_game_trajectories':0,'new_hf_jobs':0,
            'preserved_initial_probe_failure':{'path':'ai/runs/resource-sampling-anchor-v1',
                'completed_turn_checks':0,'reason':'Malformed automation object in the adversarial test fixture, not a policy/engine failure. Replaced with a structurally valid private automation fixture; fixed probe error exit to avoid a blocked reader. Initial logs, design and original source are preserved.'},
            'preserved_public_replay_failure':{'path':'ai/runs/resource-sampling-anchor-v1-checked',
                'completed_turn_checks':0,'completed_positions':1,
                'reason':'Direct E.move on a public empty deck sets cardsLeft=0 and nextCardWeak=false after a purchase. The probe now preserves these public invariants for Resources purchases and checks each transition against eight complete sampled worlds. Historical ModelResourceTurn is inspected without modification to determine whether the same defect exists there.'},
            'qualification_eligible':False,'reserved_final_seeds_used':False,
            'interpretation':'Holding the first public seed fixed preserves sampled deck, role assignment and continuation RNG prefix on these recorded turns. Public purchases still change cash/stock/markets. No policy choice, outcome or causal strength improvement was evaluated.'}
        write(OUT/'assessment.json',report);write(RESULT,{**report,'assessment_sha256':digest(OUT/'assessment.json')})
        print(json.dumps({k:v for k,v in report.items() if k not in ('cases','input_hashes','code_hashes','output_hashes')}),flush=True)
    except BaseException as error:
        if worker.poll() is None:worker.terminate();worker.wait(timeout=30)
        stderr.close();write(OUT/'failure.json',{'error':type(error).__name__+': '+str(error),'completed_turn_checks':len(cases)})
        raise


if __name__=='__main__':main()
