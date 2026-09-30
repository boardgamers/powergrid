"""Six-slot public-state policy; inactive players have exactly zero value mass."""

import torch
from torch import nn


class MultiplayerPolicy(nn.Module):
    def __init__(self, width=384):
        super().__init__()
        self.player = nn.Sequential(nn.Linear(74, 128), nn.LayerNorm(128), nn.SiLU())
        # Global context, city ownership and territory occupancy retain seat order.
        self.context = nn.Sequential(
            nn.Linear(258 + 308 + 133 + 256 + 6, width),
            nn.LayerNorm(width),
            nn.SiLU(),
            nn.Linear(width, width),
            nn.SiLU(),
        )
        self.action = nn.Sequential(nn.Linear(98, 128), nn.SiLU())
        self.score = nn.Sequential(
            nn.Linear(width + 128, 256), nn.SiLU(), nn.Linear(256, 1)
        )
        self.value = nn.Sequential(
            nn.Linear(width + 128, 128), nn.SiLU(), nn.Linear(128, 1)
        )
        nn.init.zeros_(self.score[-1].weight)
        nn.init.zeros_(self.score[-1].bias)

    def forward(self, state, actions, mask):
        active = state[:, :6] > 0.5
        p = self.player(state[:, 264:708].reshape(-1, 6, 74))
        pooled = (p * active[:, :, None]).sum(1) / active.sum(1, keepdim=True).clamp(
            min=1
        )
        s = self.context(
            torch.cat(
                (state[:, 6:264], state[:, 708:], p[:, 0], pooled, state[:, :6]), -1
            )
        )
        a = self.action(actions)
        logits = actions[:, :, 74] * 2 + self.score(
            torch.cat((s[:, None].expand(-1, a.shape[1], -1), a), -1)
        ).squeeze(-1)
        values = self.value(torch.cat((s[:, None].expand(-1, 6, -1), p), -1)).squeeze(
            -1
        )
        return logits.masked_fill(~mask, -1e9), values.masked_fill(
            ~active, -1e9
        ).softmax(-1)
