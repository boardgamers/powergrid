"""Small public-information imitation policy for simulated search opponents."""
import torch
from torch import nn

FEATURE_REVISION = '4.3-strategic-correction'
STATE_DIM, ACTION_DIM, MAX_CANDIDATES = 1217, 101, 6


class OpponentSurrogate(nn.Module):
    def __init__(self, width=256, action_width=96, score_width=128):
        super().__init__()
        # The flat state preserves each player's holdings, money and geography
        # in the same relative-seat order as the action/ownership features.
        self.context = nn.Sequential(nn.Linear(STATE_DIM, width), nn.LayerNorm(width), nn.SiLU(),
                                     nn.Linear(width, width), nn.SiLU())
        self.action = nn.Sequential(nn.Linear(ACTION_DIM, action_width), nn.SiLU())
        self.score = nn.Sequential(nn.Linear(width + action_width, score_width), nn.SiLU(), nn.Linear(score_width, 1))
        nn.init.zeros_(self.score[-1].weight)
        nn.init.zeros_(self.score[-1].bias)

    def forward(self, state, actions, mask):
        context, action = self.context(state), self.action(actions)
        residual = self.score(torch.cat((context[:, None].expand(-1, action.shape[1], -1), action), -1)).squeeze(-1)
        # The economic prior is a deterministic public action feature. Neither
        # sampled teacher scores nor teacher random seeds enter this network.
        return (2 * actions[:, :, 74] + residual).masked_fill(~mask, -1e9)


class Float64Silu(nn.Module):
    def forward(self, x):
        # Avoid ORT QuickGelu fusion, which has no float64 CPU kernel.
        return x / (1 + torch.exp(-x))


class Inference64(nn.Module):
    def __init__(self, policy):
        super().__init__(); self.policy = policy.double()
        for block in (self.policy.context, self.policy.action, self.policy.score):
            for name, module in list(block.named_children()):
                if isinstance(module, nn.SiLU): setattr(block, name, Float64Silu())

    def forward(self, state, actions, mask):
        return self.policy(state.double(), actions.double(), mask)


def from_checkpoint(checkpoint):
    assert checkpoint['architecture'] == 'opponent_surrogate_v1'
    assert checkpoint['feature_revision'] == FEATURE_REVISION
    assert checkpoint['state_dim'] == STATE_DIM and checkpoint['action_dim'] == ACTION_DIM
    assert checkpoint['max_candidates'] == MAX_CANDIDATES
    net = OpponentSurrogate(**checkpoint['model_args'])
    net.load_state_dict(checkpoint['state_dict'], strict=True)
    precision = checkpoint.get('inference_precision', 'float32')
    if precision == 'float64':
        assert checkpoint['inference_only'] is True
        assert checkpoint['inference_transform'] == 'float64-exp-div-silu-v1'
        return Inference64(net)
    assert precision == 'float32'
    return net
