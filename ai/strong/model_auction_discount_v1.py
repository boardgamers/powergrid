"""Untrained schema-4.4 extension of the frozen-head policy-iteration model.

Keep the parent matrix shapes and routing unchanged. Separate zero-initialized
projections give the new public inputs a learnable path without widening an
existing matrix multiplication. This does not expand teacher-option coverage.
"""
import copy
import torch
from torch import nn

from model import Inference64Policy
from model_policy_iteration import PolicyIterationPolicy, ensemble_advantages
from model_strategic import StrategicHead, route

FEATURE_REVISION = '4.4-auction-discount'
STATE_DIM, ACTION_DIM = 1218, 103
ARCHITECTURE = 'policy_iteration_auction_discount_v1'


class DiscountHead(StrategicHead):
    def __init__(self):
        super().__init__()
        self.discount_state = nn.Linear(1, 128, bias=False)
        self.nomination_price = nn.Linear(2, 64, bias=False)
        nn.init.zeros_(self.discount_state.weight)
        nn.init.zeros_(self.nomination_price.weight)

    def forward(self, context, action_embedding, state, actions):
        s = self.state[0](torch.cat((context, state[:, 1149:1215]), -1))
        s = self.state[2](self.state[1](s + self.discount_state(state[:, 1217:1218])))
        a = self.action[0](torch.cat((action_embedding, actions[:, :, :100]), -1))
        a = self.action[1](a + self.nomination_price(actions[:, :, 101:103]))
        return self.score(torch.cat((s[:, None].expand(-1, a.shape[1], -1), a), -1)).squeeze(-1)


class AuctionDiscountPolicy(PolicyIterationPolicy):
    def __init__(self, head_type='frozen', heads=4, margin=.025, parent_margin=.025, disagreement_penalty=1.):
        if head_type != 'frozen' or heads != 4:
            raise ValueError('This prototype supports the four-member frozen-head ensemble only')
        super().__init__(head_type, heads, margin, parent_margin, disagreement_penalty)
        self.heads = nn.ModuleList(DiscountHead() for _ in range(heads))

    def forward(self, state, actions, mask):
        # Wider rows change strides. Restore the original layout as well as the
        # original values before invoking frozen matrix multiplications.
        old_state = state[:, :1217].contiguous()
        old_actions = actions[:, :, :101].contiguous()
        parent, values = self.parent(old_state[:, :1216], old_actions[:, :, :100], mask)
        context, action_embedding = self.embeddings(old_state, old_actions)
        scores = torch.stack([head(context, action_embedding, state, actions) for head in self.heads])
        combined = ensemble_advantages(scores, parent.argmax(1), self.disagreement_penalty)
        return route(parent, combined, mask, old_actions[:, :, 100] > .5, old_state[:, 1216] > .5, self.margin), values


def extend_checkpoint(checkpoint, *, parent_sha256):
    if checkpoint.get('architecture') != 'policy_iteration_ensemble' or checkpoint.get('inference_only', False):
        raise ValueError('Extend the original training checkpoint, not an inference derivative')
    if (checkpoint.get('feature_revision'), checkpoint.get('state_dim'), checkpoint.get('action_dim')) != ('4.3-strategic-correction', 1217, 101):
        raise ValueError('Expected unchanged schema 4.3 checkpoint')
    if checkpoint['model_args']['head_type'] != 'frozen' or checkpoint['model_args']['heads'] != 4:
        raise ValueError('Unsupported parent head architecture')
    if not all(t.dtype == torch.float32 for t in checkpoint['state_dict'].values()):
        raise ValueError('Parent stored weights must be float32')
    net = AuctionDiscountPolicy(**checkpoint['model_args'])
    expected = {f'heads.{i}.{name}.weight' for i in range(4) for name in ('discount_state', 'nomination_price')}
    missing, unexpected = net.load_state_dict(checkpoint['state_dict'], strict=False)
    if set(missing) != expected or unexpected:
        raise ValueError('Parent tensors do not exactly match the preserved architecture')
    state = net.state_dict()
    assert all(torch.equal(state[k], v) for k, v in checkpoint['state_dict'].items())
    assert all(torch.count_nonzero(state[k]) == 0 for k in expected)
    result = dict(architecture=ARCHITECTURE, state_dict=state, feature_revision=FEATURE_REVISION,
        model_args=copy.deepcopy(checkpoint['model_args']),
        warm_start_parent_metadata={k: copy.deepcopy(v) for k, v in checkpoint.items() if k != 'state_dict'},
        state_dim=STATE_DIM, action_dim=ACTION_DIM, warm_start_parent_sha256=parent_sha256,
        initialized_new_tensors=sorted(expected), new_gradient_updates=0,
        qualification_eligible=False)
    return result


def policy_from_checkpoint(checkpoint):
    if checkpoint.get('architecture') != ARCHITECTURE:
        raise ValueError('Wrong discount policy architecture')
    if (checkpoint.get('feature_revision'), checkpoint.get('state_dim'), checkpoint.get('action_dim')) != (FEATURE_REVISION, STATE_DIM, ACTION_DIM):
        raise ValueError('Wrong discount feature contract')
    net = AuctionDiscountPolicy(**checkpoint['model_args'])
    net.load_state_dict(checkpoint['state_dict'])
    precision = checkpoint.get('inference_precision', 'float32')
    if precision == 'float64':
        if checkpoint.get('inference_only') is not True:
            raise ValueError('Float64 runtime must be an inference-only derivative')
        net = Inference64Policy(net, checkpoint.get('inference_transform', 'float64-native-silu-v1'))
    elif precision != 'float32':
        raise ValueError('Unsupported inference precision')
    return net
