import numpy as np
import torch
from torch import nn


class Policy(nn.Module):
    def __init__(self, sd=738, ad=96, width=384, strategic_only=False):
        super().__init__()
        self.strategic_only = strategic_only
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
        if self.strategic_only:
            strategic = (
                (actions[:, :, 0] + actions[:, :, 1] + actions[:, :, 5]) > 0
            ) & mask
            residual = residual * strategic.any(dim=1, keepdim=True)
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


class RuleSpecialists(nn.Module):
    """Fixed specialists selected only by the public schema-3 rule flags."""

    def __init__(self, default_strategic_only=False, sealed_strategic_only=False):
        super().__init__()
        self.default_policy = Policy(strategic_only=default_strategic_only)
        self.recharged_sealed_policy = Policy(strategic_only=sealed_strategic_only)

    def forward(self, state, actions, mask):
        regular = self.default_policy(state, actions, mask)
        sealed = self.recharged_sealed_policy(state, actions, mask)
        # Eight phase flags, round, step, Recharged flag, sealed-auction flag.
        use_sealed = ((state[:, 10] > 0.5) & (state[:, 11] > 0.5))[:, None]
        return tuple(torch.where(use_sealed, b, a) for a, b in zip(regular, sealed))


def policy_from_checkpoint(checkpoint):
    architecture = checkpoint.get("architecture", "policy")
    if architecture in ["multiplayer", "multiplayer_ordered"]:
        from model_v4 import MultiplayerPolicy

        args = dict(checkpoint.get("model_args", {}))
        if architecture == "multiplayer_ordered":
            args["ordered_players"] = True
        net = MultiplayerPolicy(**args)
    elif architecture == "multiplayer_ordered_plants":
        from model_v4_1 import FivePlantPolicy, FEATURE_REVISION, CONTROL_FEATURE_REVISION, STATE_DIM, ACTION_DIM

        if (checkpoint.get("feature_revision") not in [FEATURE_REVISION, CONTROL_FEATURE_REVISION]
                or checkpoint.get("state_dim") != STATE_DIM or checkpoint.get("action_dim") != ACTION_DIM):
            raise ValueError("Five-plant checkpoint feature contract mismatch")
        net = FivePlantPolicy(**checkpoint.get("model_args", {}))
    elif architecture == "rule_specialists":
        net = RuleSpecialists(**checkpoint["model_args"])
    elif architecture == "policy":
        net = Policy(strategic_only=checkpoint.get("strategic_only", False))
    else:
        raise ValueError(f"Unsupported architecture: {architecture}")
    net.load_state_dict(checkpoint["state_dict"])
    return net
