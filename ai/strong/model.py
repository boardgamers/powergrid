import numpy as np
import torch
from torch import nn


class Policy(nn.Module):
    def __init__(self, sd=738, ad=96, width=384):
        super().__init__()
        self.state = nn.Sequential(
            nn.Linear(sd, width),
            nn.LayerNorm(width),
            nn.SiLU(),
            nn.Linear(width, width),
            nn.SiLU(),
        )
        self.action = nn.Sequential(nn.Linear(ad, 128), nn.SiLU())
        self.score = nn.Sequential(
            nn.Linear(width + 128, 256), nn.SiLU(), nn.Linear(256, 1)
        )
        self.value = nn.Sequential(nn.Linear(width, 128), nn.SiLU(), nn.Linear(128, 3))
        nn.init.zeros_(self.score[-1].weight)
        nn.init.zeros_(self.score[-1].bias)

    def forward(self, state, actions, mask):
        s = self.state(state)
        a = self.action(actions)
        residual = self.score(
            torch.cat((s[:, None, :].expand(-1, a.shape[1], -1), a), -1)
        ).squeeze(-1)
        # Start from a competent public-information policy; learn corrections.
        logits = actions[:, :, 74] * 2 + residual
        return logits.masked_fill(~mask, -1e9), self.value(s).softmax(-1)


def tensors(rows, device):
    n = len(rows)
    m = max(len(r["actions"]) for r in rows)
    ad = len(rows[0]["actions"][0])
    state = np.asarray([r["state"] for r in rows], np.float32)
    actions = np.zeros((n, m, ad), np.float32)
    mask = np.zeros((n, m), bool)
    for i, r in enumerate(rows):
        actions[i, : len(r["actions"])] = r["actions"]
        mask[i, : len(r["actions"])] = True
    return tuple(torch.from_numpy(a).to(device) for a in [state, actions, mask])
