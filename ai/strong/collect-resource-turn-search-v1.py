"""Verify and archive the isolated whole-resource-turn search integration."""
import importlib.util
import json
from pathlib import Path
import shutil
import statistics

from strategic_collection import ROOT,read,write,digest
from policy_iteration_evidence_archive import upload_evidence


def main():
    base=ROOT/'ai/runs/resource-turn-search-v1';runtime=base/'runtime'
    prep=read(base/'preparation.json');contract=read(base/'contract/assessment.json')
    trained=read(base/'trained/assessment.json');selection=read(base/'selection.json')
    assert prep['unchanged_runtime_files']==len(prep['runtime_hashes'])==1463
    for name,sha in prep['runtime_hashes'].items():
        assert digest(runtime/name)==digest(ROOT/'ai/runs/population-hybrid-development-source-prepared-v1/layout'/name)==sha
    for name,sha in prep['new_files'].items():assert digest(runtime/name)==digest(ROOT/name)==sha
    for name,sha in read(ROOT/'ai/strong/population-hybrid-development-plan-v1.json')['dependency_hashes'].items():
        assert digest(ROOT/name)==sha
    assert contract['passed'] and contract['positions']==755 and contract['appended_baselines']==329
    assert contract['checker_sha256']==digest(ROOT/'ai/strong/test-resource-turn-search-v1.cjs')
    assert trained['passed'] and trained['baseline_positions']==755 and trained['baseline_decisions']==2251
    assert trained['search_cases']==23 and trained['rollouts']==1232 and trained['normal_caps']==0
    assert trained['preparation_sha256']==digest(base/'preparation.json')
    assert trained['selection_sha256']==digest(base/'selection.json')
    assert trained['checker_sha256']==digest(ROOT/'ai/strong/probe-resource-turn-search-v1.py')
    for name,sha in trained['artifacts'].items():assert digest(base/'trained'/name)==sha
    spec=importlib.util.spec_from_file_location('resource_probe',ROOT/'ai/strong/probe-resource-turn-search-v1.py')
    probe=importlib.util.module_from_spec(spec);spec.loader.exec_module(probe)
    rows=[json.loads(line) for line in (base/'trained/search.jsonl').open()]
    assert len(rows)==len(selection['selected'])==23
    results={};rollouts=0
    for row in rows:
        label,result=row['label'],row['result'];assert label not in results
        result['search']['worlds']={int(k):v for k,v in result['search']['worlds'].items()}
        probe.verify(selection['selected'][label]['request'],result)
        assert result['search']['usable'] and not result['search']['truncated']
        results[label]=result;rollouts+=result['search']['evaluations']
    assert rollouts==1232
    label='late-6p-recharged-sealed';reference=results[label];q=selection['selected'][label]['request']
    control_rollouts=0
    for name in ['partition','prefix','hidden','cap']:
        result=read(base/'trained'/(name+'.json'))
        result['search']['worlds']={int(k):v for k,v in result['search']['worlds'].items()}
        probe.verify(q,result)
        if name in ['partition','hidden']:assert probe.semantic(result)==probe.semantic(reference)
        elif name=='prefix':
            assert result['search']['seed']==reference['search']['seed'] and result['bundles']==reference['bundles']
            for key,values in reference['search']['sampleOutcomes'].items():
                assert values==result['search']['sampleOutcomes'][key][:4]
        else:assert result['search']['truncated']==116 and result['selected']==result['baseline']
        if name!='cap':
            assert not result['search']['truncated'];control_rollouts+=result['search']['evaluations']
    assert control_rollouts==464
    known=results['known-resource-omission']
    assert known['bundles'][known['baseline']]['id']=='0,0,0,0'
    assert known['bundles'][known['selected']]['id']=='3,0,0,0'
    assert known['search']['sampleOutcomes']['0,0,0,0']==[0,0,0,0]
    assert known['search']['sampleOutcomes']['3,0,0,0']==[1,1,1,1]
    summary={'status':'verified_isolated_resource_turn_search_not_integrated',
        'source_files_unchanged':1463,'running_screen_dependencies_unchanged':True,
        'contract_resource_positions':755,'contract_baseline_steps':contract['baseline_steps'],
        'partial_baselines_outside_generator_preserved':329,'contract_macro_controls':contract['macro_controls'],
        'contract_continuation_controls':contract['continuation_controls'],'invalid_requests_rejected':100,
        'actual_model_baselines':755,'actual_model_baseline_decisions':2251,
        'normal_search_cases':23,'normal_rollouts':1232,'additional_control_rollouts':464,
        'normal_rollout_caps':0,'deliberate_one_step_caps':116,
        'hidden_data_invariant':True,'worker_partition_exact':True,'sample_prefix_exact':True,
        'selected_changes_in_engineering_cases':sum(r['selected']!=r['baseline'] for r in results.values()),
        'known_omission':{'baseline':[0,0,0,0],'selected':[3,0,0,0],'cost':17,
            'baseline_sample_credits':[0,0,0,0],'selected_sample_credits':[1,1,1,1],
            'scope':'Outcome-selected diagnostic; four uncalibrated opponent/deck worlds, not a strength estimate.'},
        'local_HX370_ms':{'samples':23,'median':statistics.median(r['elapsedMs'] for r in results.values()),
            'maximum':max(r['elapsedMs'] for r in results.values())},
        'model_sha256':trained['model_sha256'],
        'limits':['Requires committing a complete returned resource turn; executing just firstMove and replanning changes the policy.',
            'No full-game arena adapter or platform persistence contract yet. Not production-ready.',
            'Public candidate family is one/two identical-cycle fuel requirements plus exact model baseline, not exhaustive stockpiles.',
            'Future building uses the model and existing strict loss filter; no forced construction route.',
            'Four-world engineering probes and equal opponent mixture are not calibrated values or strength evidence.',
            'Local HX370 timings are not target8840U latency.'],
        'next':'Complete unchanged active hybrid grid. Develop and verify an arena execution contract for complete plans, or explicitly evaluate a separately specified replanning policy; use fresh paired games and target serving checks before adoption. The component may also generate resource-turn teacher labels on fresh roots.',
        'new_hf_jobs':0,'new_strength_games':0,'gradients':False,'qualification_eligible':False,
        'reserved_final_seeds_used':False}
    evidence=ROOT/'ai/runs/resource-turn-search-evidence-v1';assert not evidence.exists();evidence.mkdir()
    sources=[p for p in base.rglob('*') if p.is_file() and 'runtime' not in p.relative_to(base).parts]
    sources += [ROOT/'ai/strong'/name for name in ['resource-turn-plans-v1.cjs','resource-turn-search-v1.cjs',
        'resource_turn_search_v1.py','test-resource-turn-search-v1.cjs','probe-resource-turn-search-v1.py',
        'collect-resource-turn-search-v1.py','resource-turn-proposal-evidence-v1.json',
        'population-hybrid-development-source-v1.json','population-hybrid-development-protocol-v1.json',
        'population-hybrid-development-plan-v1.json','policy_iteration_evidence_archive.py']]
    for source in sources:
        destination=evidence/source.relative_to(ROOT);destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,destination)
    write(evidence/'assessment.json',summary)
    write(evidence/'manifest.json',{str(p.relative_to(evidence)):digest(p) for p in evidence.rglob('*') if p.is_file()})
    receipt=upload_evidence(evidence)
    write(ROOT/'ai/strong/resource-turn-search-evidence-v1.json',{**summary,**receipt})
    print(json.dumps({**receipt,'normal_rollouts':1232,'additional_control_rollouts':464},indent=2))


if __name__=='__main__':main()
