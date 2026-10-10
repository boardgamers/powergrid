"""Learn paired continuation advantages; retain the frozen parent elsewhere."""
import torch
from torch import nn
from model_v4 import MultiplayerPolicy

FEATURE_REVISION = '4.2-discard-correction'
STATE_DIM, ACTION_DIM = 1216, 100


class DiscardHead(nn.Module):
    def __init__(self):
        super().__init__()
        self.state = nn.Sequential(nn.Linear(1215, 256), nn.LayerNorm(256), nn.SiLU(),
                                   nn.Linear(256, 128), nn.SiLU())
        self.action = nn.Sequential(nn.Linear(100, 64), nn.SiLU())
        self.score = nn.Sequential(nn.Linear(192, 128), nn.SiLU(), nn.Linear(128, 1))
        nn.init.zeros_(self.score[-1].weight)
        nn.init.zeros_(self.score[-1].bias)

    def forward(self, state, actions):
        context = self.state(state[..., :1215])
        action = self.action(actions)
        return self.score(torch.cat((context[:, None].expand(-1, action.shape[1], -1), action), -1)).squeeze(-1)


def corrected_logits(parent, scores, mask, eligible, margin):
    proposal = parent.argmax(1, keepdim=True)
    delta = scores - scores.gather(1, proposal)
    candidates = delta.masked_fill(~mask, -1e9)
    use_head = eligible[:, None] & (candidates.max(1, keepdim=True).values > margin)
    return torch.where(use_head, candidates, parent)


class DiscardPolicy(nn.Module):
    def __init__(self, margin=0.025):
        super().__init__()
        self.parent = MultiplayerPolicy(ordered_players=True)
        self.parent.requires_grad_(False)
        self.head = DiscardHead()
        self.margin = margin

    def forward(self, state, actions, mask):
        logits, values = self.parent(state[:, :1149], actions[:, :, :98], mask)
        scores = self.head(state, actions)
        return corrected_logits(logits, scores, mask, state[:, 1215] > .5, self.margin), values
