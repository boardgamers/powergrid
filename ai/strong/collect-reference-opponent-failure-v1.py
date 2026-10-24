"""Archive a failed admission pilot and an isolated, not-yet-adopted sampler repair."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import shutil

from strategic_collection import ROOT,read,write,digest
from policy_iteration_evidence_archive import upload_evidence

STRONG=ROOT/'ai/strong'
spec=importlib.util.spec_from_file_location('reference_probe',STRONG/'probe-reference-opponents-v1.py')
probe=importlib.util.module_from_spec(spec);spec.loader.exec_module(probe)
EVIDENCE=ROOT/'ai/runs/reference-opponent-pilot-failure-evidence-v1'
DESCRIPTOR=STRONG/'reference-opponent-pilot-failure-evidence-v1.json'


def main():
    p=read(probe.OUT/'protocol.json');probe.validate(p)
    assert not EVIDENCE.exists() and not EVIDENCE.with_suffix('.tgz').exists() and not DESCRIPTOR.exists()
    assert not (probe.OUT/'pilot-complete.json').exists()
    assert not (STRONG/'reference-opponent-pilot-evidence-v1.json').exists()
    assert not (ROOT/'ai/runs/reference-opponent-launches-v1').exists()
    failure=read(probe.OUT/'pilot-failure.json')
    assert failure['stage']=='failed' and failure['root']==6 and failure['new_hf_jobs']==0
    assert not Path(f"/proc/{failure['parent_pid']}").exists()
    assert all(not Path(f'/proc/{pid}').exists() for pid in failure['child_pids'])
    completed=[]
    for mode,indices,label,count in [('neural_population',range(7),'control',64),
                                     ('reference_opponent_v1',[0,2,5],'pilot',2)]:
        for i in indices:
            row=read(probe.OUT/f'{label}-{i}.json')
            checks=probe.verify_rows(p,i,mode,0,count,row['rows'])
            assert checks==read(probe.OUT/f'{label}-{i}.check.json')
            completed.append({k:v for k,v in row.items() if k!='rows'} | {'checks':checks})
    assert sum(r['checks']['rollouts'] for r in completed)==908
    assert not (probe.OUT/'pilot-6.json').exists()
    # Verify failure rejection on a complete retained pilot without manufacturing failed outcomes.
    originals=read(probe.OUT/'pilot-0.json')['rows'];rejected=[]
    corruptions={
        'outer_cap':lambda rows:rows[0].update(truncated=True),
        'nested_cap':lambda rows:rows[0]['searchStats'].update(truncated=1),
        'prior_cap':lambda rows:rows[0]['diagnostic']['priorSearchStats'].update(truncated=1),
        'invalid_score':lambda rows:rows[0].update(value=1.1),
        'wrong_world':lambda rows:rows[0]['diagnostic'].update(sampledWorldSha256='0'*64),
        'wrong_action':lambda rows:rows[0].update(actionIndex=rows[1]['actionIndex']),
        'missing_result':lambda rows:rows.pop()}
    for name,corrupt in corruptions.items():
        rows=deepcopy(originals);corrupt(rows)
        try:probe.verify_rows(p,0,'reference_opponent_v1',0,2,rows)
        except AssertionError:rejected.append(name)
        else:raise AssertionError(f'Accepted corrupt evidence: {name}')
    repaired_log=(probe.OUT/'sampler-repair-tests-2.log').read_text()
    assert 'tests 3' in repaired_log and 'pass 3' in repaired_log and 'fail 0' in repaired_log
    diagnosis=read(probe.OUT/'failure-diagnosis.json')
    assert diagnosis['priorBelief']['committed'][0]['action']=={'name':'Bid','data':15}
    assert diagnosis['allBalancesPublic'] and diagnosis['missingEarlierActor']==1
    assert diagnosis['capturedSubsequentMoves']==[
        {'player':1,'move':{'name':'ChoosePowerPlant','data':8}},
        {'player':2,'move':{'name':'Bid','data':18}},
        {'player':3,'move':{'name':'Bid','data':18}},
        {'player':5,'move':{'name':'Bid','data':18}},
        {'player':1,'move':{'name':'ChoosePowerPlant','data':5}}]
    plan=read(STRONG/'population-hybrid-development-plan-v1.json')
    assert all(digest(ROOT/name)==sha for name,sha in plan['dependency_hashes'].items())
    sources=[probe.WORKER,probe.TEST,Path(probe.__file__),Path(__file__),
             STRONG/'reference-opponent-job-v1.py',STRONG/'launch-reference-opponents-v1.py',
             STRONG/'collect-reference-opponent-pilot-v1.py',
             STRONG/'reproduce-reference-replay-failure-v1.cjs',STRONG/'analysis-public-balances-v1.cjs',
             STRONG/'test-analysis-public-balances-v1.cjs',STRONG/'auction-world-generalization-evidence-v1.json']
    sources+=list(probe.OUT.glob('*'))+list(probe.OLD.glob('*.json'))
    EVIDENCE.mkdir()
    for file in sources:
        assert file.is_file() and not file.is_symlink()
        target=EVIDENCE/file.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(file,target);assert digest(file)==digest(target)
    review={'status':'pilot_failed_no_admission','protocol_sha256':digest(probe.OUT/'protocol.json'),
            'completed_controls':896,'completed_reference_pilot_rollouts':12,'required_reference_pilot_rollouts':16,
            'completed':completed,'failed_root':6,'failed_session':5175,'process_exit_code':1,
            'failure':failure,'diagnosis':diagnosis,'rejected_corruptions':rejected,
            'worker_tests':read(probe.OUT/'worker-test-receipt.json'),
            'isolated_sampler_repair':{'file':'ai/strong/analysis-public-balances-v1.cjs',
                'sha256':digest(STRONG/'analysis-public-balances-v1.cjs'),
                'test_sha256':digest(STRONG/'test-analysis-public-balances-v1.cjs'),
                'ordinary_fixture_worlds_exact':2553,'unknown_balance_cases_exact':24,
                'captured_failure_repaired':True,'hidden_fields_invariant':True,
                'integrated_into_rollout_worker':False,'adopted':False,
                'scope':'Skip unused balance replay only when every balance is public; keep existing replay for unknown money.'},
            'frozen_runtime_files_unchanged':len(p['runtime_hashes']),
            'frozen_dependencies_unchanged':len(plan['dependency_hashes']),
            'next':'Version a new nested-reference worker with this isolated sampler repair and explicit process exit on JSONL failure. Recheck control/arena parity and run a fresh complete pilot, including the failed 6p sealed root, before new HF admission. Preserve v1 evidence as failed; no automatic rerun or partial strength claim.',
            'draft_job_tools':'Prepared only. The successful-pilot admission descriptor is absent, so the launcher cannot submit jobs.',
            'new_hf_jobs':0,'gradients':False,'new_strength_games':0,'candidate_selected':False,
            'qualification_eligible':False,'reserved_final_seeds_used':False}
    write(EVIDENCE/'review.json',review)
    write(EVIDENCE/'manifest.json',{str(f.relative_to(EVIDENCE)):digest(f) for f in sorted(EVIDENCE.rglob('*')) if f.is_file()})
    result={**review,**upload_evidence(EVIDENCE)}
    write(DESCRIPTOR,result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('completed','failure','diagnosis','worker_tests')},indent=2))


if __name__=='__main__':main()
