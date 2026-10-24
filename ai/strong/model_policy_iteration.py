"""Two public-state representations and fixed disagreement-aware ensembles."""
import torch
from torch import nn
from model import Inference64Policy, policy_from_checkpoint as old_policy_from_checkpoint
from model_discard import DiscardPolicy
from model_strategic import StrategicHead, StrategicPolicy, route, FEATURE_REVISION, STATE_DIM, ACTION_DIM


class PublicStateHead(nn.Module):
    """Add direct access to all public features before the discard/eligibility flags."""
    def __init__(self):
        super().__init__()
        self.state = nn.Sequential(nn.Linear(384 + 1215, 256), nn.LayerNorm(256), nn.SiLU(),
                                   nn.Linear(256, 128), nn.SiLU())
        self.action = nn.Sequential(nn.Linear(128 + 100, 64), nn.SiLU())
        self.score = nn.Sequential(nn.Linear(192, 128), nn.SiLU(), nn.Linear(128, 1))
        nn.init.zeros_(self.score[-1].weight)
        nn.init.zeros_(self.score[-1].bias)

    def forward(self, context, action_embedding, state, actions):
        s = self.state(torch.cat((context, state[:, :1215]), -1))
        a = self.action(torch.cat((action_embedding, actions[:, :, :100]), -1))
        return self.score(torch.cat((s[:, None].expand(-1, a.shape[1], -1), a), -1)).squeeze(-1)


def ensemble_advantages(scores, proposal, penalty):
    """Penalty is seed disagreement, not a calibrated confidence interval."""
    assert penalty in [0., 1.]
    deltas = scores - scores.gather(2, proposal[None, :, None].expand(scores.shape[0], -1, 1))
    mean = deltas.mean(0)
    if penalty:
        spread = torch.sqrt(((deltas - mean[None])**2).mean(0))
        return mean - spread
    return mean


class PolicyIterationPolicy(nn.Module):
    def __init__(self, head_type='frozen', heads=1, margin=.025, parent_margin=.025, disagreement_penalty=0.):
        super().__init__()
        assert head_type in ['frozen', 'public'] and heads in [1, 4]
        assert disagreement_penalty in [0., 1.] and (heads == 4 or disagreement_penalty == 0.)
        self.parent = DiscardPolicy(parent_margin)
        self.parent.requires_grad_(False)
        factory = StrategicHead if head_type == 'frozen' else PublicStateHead
        self.heads = nn.ModuleList([factory() for _ in range(heads)])
        self.margin = margin
        self.disagreement_penalty = disagreement_penalty

    # The existing frozen ordered-player embeddings stay byte-for-byte intact.
    embeddings = StrategicPolicy.embeddings

    def forward(self, state, actions, mask):
        parent, values = self.parent(state[:, :1216], actions[:, :, :100], mask)
        context, action_embedding = self.embeddings(state, actions)
        scores = torch.stack([head(context, action_embedding, state, actions) for head in self.heads])
        combined = ensemble_advantages(scores, parent.argmax(1), self.disagreement_penalty)
        return route(parent, combined, mask, actions[:, :, 100] > .5, state[:, 1216] > .5, self.margin), values


def policy_from_checkpoint(checkpoint):
    architecture = checkpoint.get('architecture')
    if architecture not in ['policy_iteration_head', 'policy_iteration_ensemble']:
        return old_policy_from_checkpoint(checkpoint)
    assert checkpoint['feature_revision'] == FEATURE_REVISION
    assert checkpoint['state_dim'] == STATE_DIM and checkpoint['action_dim'] == ACTION_DIM
    args = checkpoint['model_args']
    assert args['heads'] == (1 if architecture == 'policy_iteration_head' else 4)
    net = PolicyIterationPolicy(**args)
    net.load_state_dict(checkpoint['state_dict'])
    precision = checkpoint.get('inference_precision', 'float32')
    if precision == 'float64':
        assert checkpoint['inference_only'] is True
        net = Inference64Policy(net, checkpoint.get('inference_transform', 'float64-native-silu-v1'))
    else:
        assert precision == 'float32'
    return net
