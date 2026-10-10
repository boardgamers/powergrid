"""Append-only inputs with exact parent weights and zero-initialized new paths."""
import torch
from torch import nn
from model_v4 import MultiplayerPolicy

FEATURE_REVISION = "4.1-five-plants"
ARCHITECTURE = "multiplayer_ordered_plants"
STATE_DIM, ACTION_DIM = 1215, 100


class FivePlantPolicy(MultiplayerPolicy):
    def __init__(self, width=384):
        super().__init__(width=width, ordered_players=True)
        self.extra_player = nn.Linear(11, 128, bias=False)
        self.extra_action = nn.Linear(2, 128, bias=False)
        nn.init.zeros_(self.extra_player.weight)
        nn.init.zeros_(self.extra_action.weight)

    def forward(self, state, actions, mask):
        # Match the parent's strides as well as its matrix shapes. Otherwise
        # BLAS may pick a different reduction for these appended-input views.
        legacy_state = state[:, :1149].contiguous()
        legacy_actions = actions[:, :, :98].contiguous()
        active = legacy_state[:, :6] > 0.5
        p = self.player[0](legacy_state[:, 264:708].reshape(-1, 6, 74))
        p = p + self.extra_player(state[:, 1149:1215].reshape(-1, 6, 11))
        p = self.player[2](self.player[1](p))
        pooled = (p * active[:, :, None]).sum(1) / active.sum(1, keepdim=True).clamp(min=1)
        s = self.context(torch.cat((legacy_state[:, 6:264], legacy_state[:, 708:],
                                   (p * active[:, :, None]).flatten(1), pooled, legacy_state[:, :6]), -1))
        a = self.action[1](self.action[0](legacy_actions) + self.extra_action(actions[:, :, 98:100]))
        logits = legacy_actions[:, :, 74] * 2 + self.score(
            torch.cat((s[:, None].expand(-1, a.shape[1], -1), a), -1)).squeeze(-1)
        values = self.value(torch.cat((s[:, None].expand(-1, 6, -1), p), -1)).squeeze(-1)
        return logits.masked_fill(~mask, -1e9), values.masked_fill(~active, -1e9).softmax(-1)


def transfer_from_v4(checkpoint):
    """Explicit research transfer; no optimization and no changed legacy tensors."""
    if (checkpoint.get("architecture") != "multiplayer_ordered"
            or checkpoint.get("feature_revision") != "4.0-multiplayer"
            or checkpoint.get("state_dim") != 1149 or checkpoint.get("action_dim") != 98):
        raise ValueError("Transfer requires an ordered schema-4.0 checkpoint")
    args = dict(checkpoint.get("model_args", {}))
    args.pop("ordered_players", None)
    net = FivePlantPolicy(**args)
    missing, unexpected = net.load_state_dict(checkpoint["state_dict"], strict=False)
    if set(missing) != {"extra_player.weight", "extra_action.weight"} or unexpected:
        raise ValueError("Unexpected transfer keys")
    return net
