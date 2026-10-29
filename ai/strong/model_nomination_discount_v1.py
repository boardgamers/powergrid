"""Nomination-only residual heads over the unchanged trained parent policy."""
import torch
from torch import nn
from model_policy_iteration import PolicyIterationPolicy, ensemble_advantages
from model_auction_discount_v1 import DiscountHead
from model_strategic import route

ARCHITECTURE='nomination_discount_correction_v1'


class NominationDiscountPolicy(nn.Module):
    def __init__(self, discount_inputs=True, all_legal=True, heads=4, margin=.025, disagreement_penalty=1.):
        super().__init__()
        assert type(discount_inputs) is type(all_legal) is bool and heads in (1,4)
        self.parent=PolicyIterationPolicy(head_type='frozen',heads=4,margin=.025,parent_margin=.025,disagreement_penalty=1.)
        self.parent.requires_grad_(False)
        self.heads=nn.ModuleList(DiscountHead() for _ in range(heads))
        self.discount_inputs=discount_inputs;self.all_legal=all_legal
        self.margin=margin;self.disagreement_penalty=disagreement_penalty

    def embeddings(self,state,actions):
        return self.parent.embeddings(state[:,:1217].contiguous(),actions[:,:,:101].contiguous())

    def score_heads(self,context,embedding,state,actions):
        if not self.discount_inputs:
            state=torch.cat((state[:,:1217],torch.zeros_like(state[:,1217:1218])),-1)
            actions=torch.cat((actions[:,:,:101],torch.zeros_like(actions[:,:,101:103])),-1)
        return torch.stack([head(context,embedding,state,actions) for head in self.heads])

    def forward(self,state,actions,mask):
        parent,values=self.parent(state[:,:1217].contiguous(),actions[:,:,:101].contiguous(),mask)
        context,embedding=self.embeddings(state,actions)
        scores=self.score_heads(context,embedding,state,actions)
        combined=ensemble_advantages(scores,parent.argmax(1),self.disagreement_penalty)
        nomination=(mask & (actions[:,:,0]>.5)).any(1)
        allowed=mask if self.all_legal else actions[:,:,100]>.5
        return route(parent,combined,mask,allowed,nomination,self.margin),values


def initialize(parent_checkpoint,**args):
    assert parent_checkpoint['architecture']=='policy_iteration_ensemble'
    assert parent_checkpoint['model_args']=={'head_type':'frozen','heads':4,'margin':.025,'parent_margin':.025,'disagreement_penalty':1.}
    net=NominationDiscountPolicy(**args)
    net.parent.load_state_dict(parent_checkpoint['state_dict'],strict=True)
    # Reuse the learned hidden representation but reset the added correction to zero.
    # Every arm/seed starts with identical tensors; seeds affect training order only.
    hidden={k.removeprefix('heads.0.'):v for k,v in parent_checkpoint['state_dict'].items() if k.startswith('heads.0.')}
    for head in net.heads:
        missing,extra=head.load_state_dict(hidden,strict=False)
        assert set(missing)=={'discount_state.weight','nomination_price.weight'} and not extra
        nn.init.zeros_(head.score[-1].weight);nn.init.zeros_(head.score[-1].bias)
    return net


def from_checkpoint(cp):
    assert cp['architecture']==ARCHITECTURE and cp['feature_revision']=='4.4-auction-discount'
    net=NominationDiscountPolicy(**cp['model_args']);net.load_state_dict(cp['state_dict'],strict=True)
    return net
