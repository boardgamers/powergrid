"""Strict native/ONNX parity on every current-engine public serving fixture.

Uses existing immutable weights and the actual frozen policy preparation path.
No export, training, search rollout, full game, selection or reserved seed.
"""
from collections import Counter
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import time

import numpy as np

ROOT=Path(__file__).resolve().parents[2]
ARTIFACT=ROOT/'ai/runs/current-auction-grid-prepared-v1/source/artifact'
PACKAGE=ROOT/'ai/runs/current-full-serving-8840u-prepared-v1/package'
CHECKPOINT=ROOT/'ai/runs/policy-iteration-training-verified-v2/frozen/ensemble-1/derivative/inference64.pt'
NATIVE=ROOT/'ai/runs/current-engine-export-native-source-v1'
PROOF=ROOT/'ai/runs/policy-iteration-final-technical-evidence-archive-v2/receipts/frozen-1-parity.json'
OUT=ROOT/'ai/runs/current-engine-export-parity-v1'
RESULT=ROOT/'ai/strong/current-engine-export-parity-v1.json'
RUNTIME_SHA='fc135130689140b6fd72a76e6e14c59a7fea59717b858d330bac0c7f6aad93df'
MODEL_SHA='55331f43379e8fe89025d93b1a7a48c88e0ea39b4ebd3a7ef8240d4b62753530'
CHECKPOINT_SHA='3c17d4228e7446f8859aa01e79020ed91f454312925d29c153a76f49f94118da'
COUNTS={'2':349,'3':427,'4':527,'5':609,'6':641}


def read(p):return json.loads(Path(p).read_text())
def digest(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def wire(x):return json.dumps(x,separators=(',',':'),allow_nan=False)
def object_hash(x):return hashlib.sha256(wire(x).encode()).hexdigest()
def save(p,x):
    with Path(p).open('x') as f:json.dump(x,f,indent=2,allow_nan=False);f.write('\n')


def compare_outputs(expected,actual,players,actions):
    assert type(players) is int and 2<=players<=6 and actions>0
    expected=[np.asarray(v) for v in expected];actual=[np.asarray(v) for v in actual]
    assert len(expected)==len(actual)==2
    for outputs in (expected,actual):
        assert outputs[0].shape==(1,actions) and outputs[1].shape==(1,6)
        assert all(np.isfinite(v).all() for v in outputs)
        assert np.all(outputs[1][:,players:]==0)
        assert np.all(outputs[1]>=0) and np.all(outputs[1]<=1)
        np.testing.assert_allclose(outputs[1].sum(1),1,atol=1e-10,rtol=1e-10)
    for a,b in zip(actual,expected):np.testing.assert_allclose(a,b,atol=1e-8,rtol=1e-10)
    selected=int(actual[0].argmax(1)[0]);native=int(expected[0].argmax(1)[0])
    assert selected==native, 'Near-tied logits must still choose the same legal index'
    return selected,[float(np.abs(a-b).max()) for a,b in zip(actual,expected)]


def admit():
    from huggingface_hub import hf_hub_download
    assert not OUT.exists() and not RESULT.exists(),'Inspect original parity outcome; never overwrite'
    assert digest(ARTIFACT/'manifest.json')==RUNTIME_SHA
    manifest=read(ARTIFACT/'manifest.json')
    assert all(digest(ARTIFACT/n)==h for n,h in manifest.items())
    assert digest(CHECKPOINT)==CHECKPOINT_SHA and digest(ARTIFACT/'policy.onnx')==MODEL_SHA
    proof=read(PROOF);pin=proof['model_pin']
    assert proof['complete'] and proof['positions']==2553 and proof['all_native_onnx_actions_equal']
    assert proof['checkpoint_sha256']==pin['files']['inference64.pt']==CHECKPOINT_SHA
    assert proof['model_sha256']==pin['files']['inference64.onnx']==MODEL_SHA
    descriptor=read(ROOT/'ai/strong/policy-iteration-final-technical-evidence-v2.json')
    archive=Path(hf_hub_download(descriptor['repo'],descriptor['archive_path'],revision=descriptor['revision']))
    assert digest(archive)==descriptor['archive_sha256']
    with tarfile.open(archive) as bundle:
        raw=bundle.extractfile('manifest.json').read();assert hashlib.sha256(raw).hexdigest()==descriptor['manifest_sha256']
        files=json.loads(raw);name='receipts/frozen-1-parity.json'
        assert digest(PROOF)==files[name]==hashlib.sha256(bundle.extractfile(name).read()).hexdigest()
    training_path=ROOT/'ai/runs/policy-iteration-training-verified-v2/frozen/verified.json'
    assert digest(training_path)==proof['input_artifacts'][str(training_path.relative_to(ROOT))]
    training=read(training_path);native=read(NATIVE/'manifest.json');source=training['source']
    assert native['verified_training_sha256']==digest(training_path) and native['checkpoint_sha256']==CHECKPOINT_SHA
    assert native['source']=={k:source[k] for k in ('archive','revision','sha256')}
    assert set(native['files'])=={'model.py','model_policy_iteration.py','model_strategic.py','model_discard.py','model_v4.py','model_v4_1.py'}
    archive=Path(hf_hub_download('coyotte508/powergrid-ai-training-v1',source['archive'],revision=source['revision'],repo_type='dataset'))
    assert digest(archive)==source['sha256']
    with tarfile.open(archive) as bundle:
        for name,sha in native['files'].items():
            assert digest(NATIVE/name)==sha==hashlib.sha256(bundle.extractfile('ai/strong/'+name).read()).hexdigest()
    package_manifest=read(PACKAGE/'benchmark-manifest.json')
    assert package_manifest['runtime_manifest_sha256']==RUNTIME_SHA and package_manifest['positions']==2553
    assert digest(PACKAGE/'cases.jsonl')==package_manifest['files']['cases.jsonl']
    tests=ROOT/'ai/runs/current-engine-export-parity-tests-v1-first.log'
    assert 'Ran 4 tests' in tests.read_text() and tests.read_text().rstrip().endswith('OK')
    sources=[Path(__file__),CHECKPOINT,PROOF,ARTIFACT/'manifest.json',PACKAGE/'cases.jsonl',
        PACKAGE/'benchmark-manifest.json',ROOT/'ai/strong/policy-iteration-final-technical-evidence-v2.json',
        ROOT/'ai/strong/test_current_engine_export_parity_v1.py',tests,training_path,NATIVE/'manifest.json',
        *(NATIVE/n for n in native['files'])]
    return manifest,proof,{str(p.relative_to(ROOT)):digest(p) for p in sources}


def run():
    manifest,proof,pins=admit()
    sys.path.insert(0,str(NATIVE))
    import torch,onnxruntime
    import model_policy_iteration,model,model_strategic,model_discard,model_v4_1,model_v4
    from model_policy_iteration import policy_from_checkpoint
    native_manifest=read(NATIVE/'manifest.json')
    for module in (model_policy_iteration,model,model_strategic,model_discard,model_v4_1,model_v4):
        origin=Path(module.__file__).resolve();assert origin.parent==NATIVE
        assert digest(origin)==native_manifest['files'][origin.name]
    sys.path.insert(0,str(ARTIFACT/'ai/strong'))
    import hybrid_search,infer,pool
    for module in (hybrid_search,infer,pool):
        origin=Path(module.__file__).resolve();assert origin.is_relative_to(ARTIFACT)
        assert digest(origin)==manifest[str(origin.relative_to(ARTIFACT))]
    torch.set_num_threads(1)
    cp=torch.load(CHECKPOINT,map_location='cpu',weights_only=True)
    assert cp['inference_precision']=='float64' and cp['inference_only']
    assert cp['feature_revision']=='4.3-strategic-correction' and cp['architecture']=='policy_iteration_ensemble'
    native=policy_from_checkpoint(cp).eval();exported=hybrid_search.Model(ARTIFACT/'policy.onnx',threads=1)
    assert exported.sha256==MODEL_SHA
    OUT.mkdir();save(OUT/'intent.json',{'started_at':datetime.now(timezone.utc).isoformat(),'input_hashes':pins,
        'positions':2553,'model_pin':proof['model_pin'],'runtime_manifest_sha256':RUNTIME_SHA,
        'purpose':'Fresh current-engine native/ONNX export comparison only; no retraining or policy selection.'})
    started=time.perf_counter();counts=Counter();maximum=[0.,0.];positions=0
    with (OUT/'engine.stderr.log').open('x') as stderr,(OUT/'receipts.jsonl').open('x') as receipts:
        worker=subprocess.Popen(['node',str(ARTIFACT/'ai/strong/population-hybrid-policy.cjs')],
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=stderr,text=True,bufsize=1,cwd='/tmp')
        try:
            with (PACKAGE/'cases.jsonl').open() as source:
                for index,line in enumerate(source):
                    case=json.loads(line);assert case['index']==index;q=case['request'];n=case['players']
                    worker.stdin.write(wire({'op':'prepare','state':q['state'],'player':q['player'],'featureRevision':cp['feature_revision']})+'\n');worker.stdin.flush()
                    answer=worker.stdout.readline();assert answer,'Frozen preparation worker exited'
                    root=json.loads(answer);row=root['observation']
                    assert root['moves']==case['legal'] and row['playerOrder']==case['player_order']
                    batch={'state':np.asarray([row['state']],np.float32),'actions':np.asarray([row['actions']],np.float32)}
                    batch['mask']=np.ones(batch['actions'].shape[:2],bool)
                    assert batch['state'].shape==(1,1217) and batch['actions'].shape==(1,len(case['legal']),101)
                    assert all(np.isfinite(v).all() for v in batch.values())
                    assert int((batch['state'][0,:6]>.5).sum())==n
                    with torch.inference_mode():expected=[v.numpy() for v in native(*(torch.from_numpy(batch[k]) for k in ('state','actions','mask')))]
                    actual=exported.session.run(None,batch);choice,errors=compare_outputs(expected,actual,n,len(case['legal']))
                    maximum=[max(a,b) for a,b in zip(maximum,errors)];counts[str(n)]+=1;positions+=1
                    record={'index':index,'requestId':q['requestId'],'revision':q['revision'],'players':n,
                        'request_sha256':object_hash(q),'legal_sha256':object_hash(case['legal']),
                        'model_sha256':MODEL_SHA,'checkpoint_sha256':CHECKPOINT_SHA,
                        'input_tensors':{k:{'shape':list(v.shape),'dtype':str(v.dtype),'sha256':hashlib.sha256(v.tobytes()).hexdigest()} for k,v in batch.items()},
                        'native_outputs':[v.tolist() for v in expected],'onnx_outputs':[v.tolist() for v in actual],
                        'selected_index':choice,'selected_move':case['legal'][choice],'max_errors':errors}
                    receipts.write(wire(record)+'\n');receipts.flush()
                    if positions%250==0:print(json.dumps({'positions':positions,'max_errors':maximum}),flush=True)
        finally:
            worker.stdin.close();code=worker.wait(timeout=30);worker.stdout.close();assert code==0
    assert positions==2553 and dict(counts)==COUNTS
    assert all(digest(ROOT/n)==h for n,h in pins.items())
    assert all(digest(ARTIFACT/n)==h for n,h in manifest.items())
    report={'complete':True,'positions':positions,'by_player_count':dict(counts),'all_native_onnx_actions_equal':True,
        'all_moves_legal':True,'finite_values':True,'inactive_values_zero':True,'values_normalized':True,
        'max_logit_error':maximum[0],'max_value_error':maximum[1],'seconds':time.perf_counter()-started,
        'torch':torch.__version__,'onnxruntime':onnxruntime.__version__,'numpy':np.__version__,
        'model_sha256':MODEL_SHA,'checkpoint_sha256':CHECKPOINT_SHA,'model_pin':proof['model_pin'],
        'native_source':native_manifest['source'],'native_source_manifest_sha256':digest(NATIVE/'manifest.json'),
        'runtime_manifest_sha256':RUNTIME_SHA,'input_hashes':pins,
        'receipts_sha256':digest(OUT/'receipts.jsonl'),'engine_stderr_sha256':digest(OUT/'engine.stderr.log'),
        'new_native_forward_passes':2553,'new_onnx_forward_passes':2553,'new_hf_jobs':0,'new_search_rollouts':0,
        'new_full_evaluation_games':0,'gradient_updates':0,'candidate_selected':False,'qualified':False,'reserved_final_seeds_used':False,
        'scope':'Base-network export parity for both frozen confirmation policies on all current-engine public fixtures. Filter/search overrides are verified separately; not a strength or calibrated-value claim.'}
    save(RESULT,report);print(json.dumps({k:report[k] for k in ('complete','positions','max_logit_error','max_value_error','seconds')}),flush=True)


if __name__=='__main__':run()
