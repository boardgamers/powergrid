"""Join the complete audited targets with fixed inputs and freeze the recipe."""
from collections import Counter
from datetime import datetime,timezone
from fractions import Fraction
import json
import numpy as np
import torch
from model_policy_iteration import policy_from_checkpoint
from prepare_auction_discount_teacher_v2 import ROOT,PROTOCOL,digest,read,save

OUT=ROOT/'ai/runs/nomination-discount-training-data-v1'
DESIGN=ROOT/'ai/strong/nomination-discount-training-design-v1.json'


def main():
    assert not OUT.exists() and not DESIGN.exists(),'Inspect prior training-data preparation'
    result_path=ROOT/'ai/strong/auction-discount-teacher-results-v2.json';result=read(result_path)
    assert result['complete'] and result['independently_audited'] and result['roots']==5770 and result['caps']==0
    assert result['rollouts']==1940544 and result['protocol_sha256']==digest(PROTOCOL)
    model_check=read(ROOT/'ai/strong/nomination-discount-model-check-v1.json');assert model_check['complete']
    assert model_check['model_sha256']==digest(ROOT/'ai/strong/model_nomination_discount_v1.py')
    inputs=ROOT/'ai/runs/nomination-discount-inputs-v1';check=read(inputs/'report.json')
    assert check['complete'] and check['protocol_sha256']==digest(PROTOCOL)
    assert all(digest(inputs/f)==sha for f,sha in check['files'].items())
    data=dict(np.load(inputs/'inputs.npz',allow_pickle=False));meta=read(inputs/'metadata.json')
    positions={r['rootId']:i for i,r in enumerate(meta)};assert len(positions)==5770
    shape=data['mask'].shape
    for key in ('target','precision','variance_of_mean','target_a','target_b'):data[key]=np.zeros(shape,np.float64)
    data['proposal_index']=np.zeros(5770,np.int64);seen=set();historical_mask_differences=0
    for shard in result['shards']:
        p=ROOT/f"ai/runs/auction-discount-teacher-collection-v2/shard-{shard['shard']:02d}/audit.json"
        assert digest(p)==shard['audit_sha256']
        for r in read(p)['summaries']:
            i=positions[r['rootId']];assert i not in seen;seen.add(i)
            assert meta[i]['split']==r['split'] and r['independently_audited'] and r['worlds']==64
            n=r['all_legal_options'];assert data['mask'][i].sum()==n
            data['proposal_index'][i]=r['baseline']
            for action,d in r['actions'].items():
                a=int(action);data['target'][i,a]=float(Fraction(d['paired_mean_margin']))
                data['variance_of_mean'][i,a]=d['paired_standard_error']**2
                data['target_a'][i,a],data['target_b'][i,a]=[float(Fraction(v)) for v in d['half_margins']]
            data['precision'][i,:n]=np.clip(.05**2/(.05**2+data['variance_of_mean'][i,:n]),.25,1.)
            meta[i]['baseline']=r['baseline'];meta[i]['decision']='nomination'
            old=set(np.flatnonzero(data['actions'][i,:n,100]>.5))|{r['baseline']}
            historical=meta[i]['old_label_options']
            if historical is not None:historical_mask_differences+=old!=set(historical)
    assert len(seen)==5770
    np.testing.assert_allclose(data['target'],(data['target_a']+data['target_b'])/2,atol=1e-15,rtol=1e-15)
    idx=np.arange(5770),data['proposal_index'];assert (data['target'][idx]==0).all()
    data['old_mask']=data['mask']&(data['actions'][:,:,100]>.5);data['old_mask'][idx]=True
    data['train']=np.array([m['split']=='train' for m in meta]);assert data['train'].sum()==4326
    parent_path=ROOT/'ai/runs/policy-iteration-training-verified-v2/frozen/ensemble-1/best.pt'
    assert digest(parent_path)=='6de3a433103a5cce4b88f54dd68ae8b4b4371d4e317ad9d8de1c5e3d4ea182fa'
    cp=torch.load(parent_path,map_location='cpu',weights_only=True);net=policy_from_checkpoint(cp).double().eval();torch.set_num_threads(1)
    with torch.inference_mode():
        for start in range(0,5770,128):
            end=min(start+128,5770)
            s=torch.from_numpy(data['state'][start:end,:1217].copy()).double()
            a=torch.from_numpy(data['actions'][start:end,:,:101].copy()).double()
            m=torch.from_numpy(data['mask'][start:end]);choices=net(s,a,m)[0].argmax(1).numpy()
            np.testing.assert_array_equal(choices,data['proposal_index'][start:end])
    OUT.mkdir();np.savez_compressed(OUT/'data.npz',**data);save(OUT/'metadata.json',meta)
    report={'complete':True,'roots':5770,'splits':{'train':4326,'validation':1444},
        'teacher_results_sha256':digest(result_path),'input_report_sha256':digest(inputs/'report.json'),
        'files':{f:digest(OUT/f) for f in ('data.npz','metadata.json')},'parent_sha256':digest(parent_path),
        'old_mask_definition':'Current legacy feature shortlist plus exact parent fallback; all-legal arm changes only nomination coverage.',
        'historical_teacher_option_sets_differing_from_current_mask':historical_mask_differences,
        'old_mask_nonparent_actions':int(data['old_mask'].sum()-5770),
        'all_legal_nonparent_actions':int(data['mask'].sum()-5770),
        'native_float64_teacher_baselines_equal':5770,'new_gradient_updates':0,'new_games':0}
    save(OUT/'report.json',report)
    design={'created_at':datetime.now(timezone.utc).isoformat(),'purpose':'Separate explicit discount inputs from broader nomination coverage.',
        'architecture':'nomination_discount_correction_v1','feature_revision':'4.4-auction-discount',
        'state_dim':1218,'action_dim':103,'parent_sha256':digest(parent_path),'data_report_sha256':digest(OUT/'report.json'),
        'model_check_sha256':digest(ROOT/'ai/strong/nomination-discount-model-check-v1.json'),
        'arms':[{'name':f'd{d}-all{a}','discount_inputs':bool(d),'all_legal':bool(a)} for d in (0,1) for a in (0,1)],
        'seeds':[15101,15102,15103,15104],'epochs':120,'batch_size':256,'evaluate_every':5,
        'learning_rate':.0003,'weight_decay':.001,'max_grad_norm':1.,'margin':.025,'ensemble_disagreement_penalty':1.,
        'loss':'Root-normalized paired advantage MSE; uncertainty weights clip(0.05^2/(0.05^2+variance_of_mean),0.25,1). Keep negative and uncertain targets. The old-coverage arm masks unavailable correction choices during fitting and routing.',
        'checkpoint_selection':'Minimum validation simulated regret over the complete legal menu; earliest epoch on ties. Each arm retains all four fixed seeds; no best-seed selection.',
        'initialization':'Identical frozen trained parent in every arm. Copy parent head-0 hidden layers, zero the new output layer and discount projections. Seed changes minibatch order, not initial weights.',
        'scope':'Nomination only. Non-nomination logits and all value outputs use the frozen parent exactly.',
        'reliability_review':'All 1940544 continuations passed. Best-action sets overlap between 32-world halves on 3844/5770 roots; 12451/16734 action margins exceeding 0.025 have the same sign in both halves. Use soft uncertainty-weighted targets and fixed seed ensemble, not hard winners or claimed confidence. All ten natural low-cash roots have zero sampled action advantages and are retained.',
        'evaluation':'All four trained ensembles are development candidates. New independent whole-game development deals across 2-6 players and Original/Recharged x open/sealed; existing confirmation and reserved final seeds remain separate. No strength claim from target fit.',
        'training_location':'HF Jobs only','new_gradient_updates_at_design':0,'qualified':False,'reserved_final_seeds_used':False}
    save(DESIGN,design);print({k:report[k] for k in ('roots','old_mask_nonparent_actions','all_legal_nonparent_actions','historical_teacher_option_sets_differing_from_current_mask')},flush=True)


if __name__=='__main__':main()
