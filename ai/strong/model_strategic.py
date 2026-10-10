"""Paired-advantage correction over the exact teacher menu; parent stays frozen."""
import torch
from torch import nn
from model_discard import DiscardPolicy

FEATURE_REVISION = '4.3-strategic-correction'
STATE_DIM, ACTION_DIM = 1217, 101


def route(parent, scores, mask, shortlisted, eligible, margin):
    proposal = parent.argmax(1, keepdim=True)
    # The parent proposal is always an available fallback, including outside the shortlist.
    is_proposal = torch.arange(mask.shape[1], device=mask.device)[None, :] == proposal
    allowed = mask & (shortlisted | is_proposal)
    delta = scores - scores.gather(1, proposal)
    candidates = delta.masked_fill(~allowed, -1e9)
    use_head = eligible[:, None] & (candidates.max(1, keepdim=True).values > margin)
    return torch.where(use_head, candidates, parent)


class StrategicHead(nn.Module):
    def __init__(self):
        super().__init__()
        self.state = nn.Sequential(nn.Linear(384+66, 128), nn.LayerNorm(128), nn.SiLU())
        self.action = nn.Sequential(nn.Linear(128+100, 64), nn.SiLU())
        self.score = nn.Sequential(nn.Linear(192, 128), nn.SiLU(), nn.Linear(128, 1))
        nn.init.zeros_(self.score[-1].weight)
        nn.init.zeros_(self.score[-1].bias)

    def forward(self, context, action_embedding, state, actions):
        s = self.state(torch.cat((context, state[:, 1149:1215]), -1))
        a = self.action(torch.cat((action_embedding, actions[:, :, :100]), -1))
        return self.score(torch.cat((s[:, None].expand(-1, a.shape[1], -1), a), -1)).squeeze(-1)


class StrategicPolicy(nn.Module):
    def __init__(self, margin=0.025, parent_margin=0.025):
        super().__init__()
        self.parent = DiscardPolicy(parent_margin)
        self.parent.requires_grad_(False)
        self.head = StrategicHead()
        self.margin = margin

    def embeddings(self, state, actions):
        # Reuse the frozen ordered-player representation; city ownership and holdings
        # stay attached to the same relative seats. No parent layer is trained.
        base = self.parent.parent
        active = state[:, :6] > .5
        players = base.player(state[:, 264:708].reshape(-1, 6, 74))
        pooled = (players * active[:, :, None]).sum(1) / active.sum(1, keepdim=True).clamp(min=1)
        context = base.context(torch.cat((state[:, 6:264], state[:, 708:1149],
            (players * active[:, :, None]).flatten(1), pooled, state[:, :6]), -1))
        return context, base.action(actions[:, :, :98])

    def forward(self, state, actions, mask):
        logits, values = self.parent(state[:, :1216], actions[:, :, :100], mask)
        context, action_embedding = self.embeddings(state, actions)
        scores = self.head(context, action_embedding, state, actions)
        return route(logits, scores, mask, actions[:, :, 100] > .5, state[:, 1216] > .5, self.margin), values
