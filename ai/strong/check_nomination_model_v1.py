"""Actual-input scope/initialization checks; no optimizer or simulation."""
import json
import numpy as np
import torch
from model_nomination_discount_v1 import initialize
from prepare_auction_discount_teacher_v2 import ROOT,digest,read,save


def main():
    output=ROOT/'ai/strong/nomination-discount-model-check-v1.json';assert not output.exists()
    torch.set_num_threads(1);torch.manual_seed(15101)
    checkpoint=ROOT/'ai/runs/policy-iteration-training-verified-v2/frozen/ensemble-1/best.pt'
    assert digest(checkpoint)=='6de3a433103a5cce4b88f54dd68ae8b4b4371d4e317ad9d8de1c5e3d4ea182fa'
    parent=torch.load(checkpoint,map_location='cpu',weights_only=True)
    new=dict(np.load(ROOT/'ai/runs/nomination-discount-inputs-v1/inputs.npz',allow_pickle=False))
    old=dict(np.load(ROOT/'ai/runs/policy-iteration-features-v2/features.npz',allow_pickle=False))
    # Actual stored bidding/building rows, separate from the new nomination data.
    ids=np.flatnonzero(~((old['actions'][:,:,0]>.5)&old['mask']).any(1))[:256]
    non={'state':np.pad(old['state'][ids],((0,0),(0,1))),
         'actions':np.pad(old['actions'][ids],((0,0),(0,0),(0,2))),'mask':old['mask'][ids]}
    cases={}
    for discount in (False,True):
        for all_legal in (False,True):
            net=initialize(parent,discount_inputs=discount,all_legal=all_legal).eval()
            assert not any(p.requires_grad for p in net.parent.parameters())
            assert all(torch.equal(v,parent['state_dict'][k]) for k,v in net.parent.state_dict().items())
            with torch.inference_mode():
                for start in range(0,len(new['state']),128):
                    s,a,m=[torch.from_numpy(new[k][start:start+128]) for k in ('state','actions','mask')]
                    before=net.parent(s[:,:1217].contiguous(),a[:,:,:101].contiguous(),m);after=net(s,a,m)
                    assert all(torch.equal(x,y) for x,y in zip(before,after))
                # A nonzero correction cannot alter another phase or its value output.
                for head in net.heads:
                    head.score[-1].weight.normal_(0,.2);head.score[-1].bias.fill_(.3)
                    head.discount_state.weight.normal_(0,.2);head.nomination_price.weight.normal_(0,.2)
                s,a,m=[torch.from_numpy(non[k]) for k in ('state','actions','mask')]
                before=net.parent(s[:,:1217].contiguous(),a[:,:,:101].contiguous(),m);after=net(s,a,m)
                assert all(torch.equal(x,y) for x,y in zip(before,after))
                s,a,m=[torch.from_numpy(new[k][:64]) for k in ('state','actions','mask')]
                logits,values=net(s,a,m);base,base_values=net.parent(s[:,:1217].contiguous(),a[:,:,:101].contiguous(),m)
                assert torch.equal(values,base_values) and m.gather(1,logits.argmax(1)[:,None]).all()
                if not discount:
                    changed_s=s.clone();changed_a=a.clone();changed_s[:,1217]=1-changed_s[:,1217]
                    changed_a[:,:,101:]=torch.randn_like(changed_a[:,:,101:])
                    other=net(changed_s,changed_a,m);assert torch.equal(logits,other[0])
            cases[f'd{int(discount)}-all{int(all_legal)}']={'initial_exact_nomination_rows':5770,
                'non_nomination_rows_unchanged_after_head_mutation':len(ids),'all_moves_legal':True,'values_unchanged':True}
    save(output,{'complete':True,'cases':cases,'parent_sha256':digest(checkpoint),
        'model_sha256':digest(ROOT/'ai/strong/model_nomination_discount_v1.py'),
        'inputs_sha256':digest(ROOT/'ai/runs/nomination-discount-inputs-v1/inputs.npz'),
        'new_gradient_updates':0,'new_games':0,'qualified':False})
    print({'complete':True,'cases':len(cases),'nomination_checks':4*5770,'other_phase_checks':4*len(ids)},flush=True)


if __name__=='__main__':main()
