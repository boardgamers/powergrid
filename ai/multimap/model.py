"""Small relational city graph + masked player set + legal-action scorer.

No city/region/map ID embeddings. Node permutation equivariant; build actions
use gathered city embeddings. Zero-padding must not affect logits or value.
"""
import torch
from torch import nn

SCHEMA = "multimap-graph-v1"
DIMS = {"global": 273, "players": 80, "nodes": 36, "actions": 34}


def mlp(a, b, c):
    return nn.Sequential(nn.Linear(a, b), nn.ReLU(), nn.Linear(b, c))


def mean_pool(x, mask):
    return (x * mask.unsqueeze(-1)).sum(1) / mask.sum(1, keepdim=True).clamp_min(1)


class GraphPolicy(nn.Module):
    def __init__(self, width=64):
        super().__init__()
        self.width = width
        self.city = mlp(DIMS["nodes"], width, width)
        self.messages = nn.ModuleList([nn.Linear(width * 5, width) for _ in range(2)])
        self.player = mlp(DIMS["players"], width, width)
        self.context = mlp(DIMS["global"] + width * 3, width * 2, width)
        self.action = mlp(DIMS["actions"] + width * 2, width * 2, 1)
        self.value = mlp(width, width, 1)

    def forward(self, batch):
        mask = batch["nodeMask"]
        city = self.city(batch["nodes"]) * mask.unsqueeze(-1)
        for layer in self.messages:
            messages = [city] + [torch.bmm(batch["relations"][:, k], city) for k in range(4)]
            city = (city + torch.relu(layer(torch.cat(messages, -1)))) * mask.unsqueeze(-1)
        players = self.player(batch["players"])
        context = self.context(torch.cat([
            batch["global"], mean_pool(city, mask), players[:, 0],
            mean_pool(players, batch["playerMask"]),
        ], -1))
        index = batch["actionCity"]
        selected = city.gather(1, index.clamp_min(0).unsqueeze(-1).expand(-1, -1, self.width))
        selected = selected * (index >= 0).unsqueeze(-1)
        context_actions = context.unsqueeze(1).expand(-1, index.shape[1], -1)
        logits = self.action(torch.cat([batch["actions"], selected, context_actions], -1)).squeeze(-1)
        logits = logits.masked_fill(~batch["actionMask"], -1e9)
        return logits, self.value(context).squeeze(-1)


def tensor_row(row, relations=None):
    result = {k: torch.tensor(row[k], dtype=torch.float32) for k in DIMS}
    result["relations"] = relations if relations is not None else torch.tensor(row["relations"], dtype=torch.float32)
    result["actionCity"] = torch.tensor(row["actionCity"], dtype=torch.long)
    result["targets"] = torch.tensor(row.get("targets", [1] * len(row["actions"])), dtype=torch.float32)
    result["value"] = torch.tensor(row.get("value", 0), dtype=torch.float32)
    for k, dim in DIMS.items():
        if result[k].shape[-1] != dim or not torch.isfinite(result[k]).all():
            raise ValueError(f"Invalid tensor {k}")
    assert len(result["actions"]) == len(result["actionCity"]) == len(result["targets"])
    assert result["targets"].sum() > 0
    assert (result["actionCity"] >= -1).all() and (result["actionCity"] < len(result["nodes"])).all()
    return result


def collate(rows):
    b = len(rows)
    n = max(len(r["nodes"]) for r in rows)
    p = max(len(r["players"]) for r in rows)
    a = max(len(r["actions"]) for r in rows)
    batch = {"global": torch.stack([r["global"] for r in rows]),
             "players": torch.zeros(b, p, DIMS["players"]),
             "nodes": torch.zeros(b, n, DIMS["nodes"]),
             "actions": torch.zeros(b, a, DIMS["actions"]),
             "relations": torch.zeros(b, 4, n, n),
             "nodeMask": torch.zeros(b, n, dtype=torch.bool),
             "playerMask": torch.zeros(b, p, dtype=torch.bool),
             "actionMask": torch.zeros(b, a, dtype=torch.bool),
             "actionCity": torch.full((b, a), -1, dtype=torch.long),
             "targets": torch.zeros(b, a),
             "value": torch.stack([r["value"] for r in rows])}
    for i, r in enumerate(rows):
        n, p, a = len(r["nodes"]), len(r["players"]), len(r["actions"])
        batch["nodes"][i, :n] = r["nodes"]
        batch["players"][i, :p] = r["players"]
        batch["actions"][i, :a] = r["actions"]
        batch["relations"][i, :, :n, :n] = r["relations"]
        batch["nodeMask"][i, :n] = True
        batch["playerMask"][i, :p] = True
        batch["actionMask"][i, :a] = True
        batch["actionCity"][i, :a] = r["actionCity"]
        batch["targets"][i, :a] = r["targets"] / r["targets"].sum()
    return batch
