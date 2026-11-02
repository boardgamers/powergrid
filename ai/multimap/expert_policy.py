"""Versioned expert-assisted residual policy; no legacy serving code is modified.

The portable graph representation is retained. One normalized action-prior scalar
is added to the scorer so a correction can observe the baseline it corrects.
A +/-16 residual can overcome every gap in the [-20,0] prior, unlike v1's +/-8.
"""
import json
from pathlib import Path

import torch
from torch import nn

from data import digest
from model import DIMS, GraphPolicy, SCHEMA as BASE_SCHEMA
from residual import row, batch

PROTOCOL = json.loads((Path(__file__).parent / 'expert-protocol-v2.json').read_text())
SCHEMA = PROTOCOL['schema']


class ExpertPolicy(nn.Module):
    def __init__(self, width=64, bound=16):
        super().__init__()
        if type(width) is not int or width < 1 or bound != 16:
            raise ValueError('Invalid expert graph width/residual bound')
        self.width, self.bound = width, bound
        self.network = GraphPolicy(width)
        self.network.action[0] = nn.Linear(DIMS['actions'] + 1 + width * 2, width * 2)
        self.zero_actor()

    def zero_actor(self):
        nn.init.zeros_(self.network.action[-1].weight)
        nn.init.zeros_(self.network.action[-1].bias)

    def forward(self, inputs):
        prior_feature = torch.where(inputs['actionMask'], inputs['prior'] / 20,
                                    torch.zeros_like(inputs['prior']))
        augmented = dict(inputs, actions=torch.cat([inputs['actions'], prior_feature.unsqueeze(-1)], -1))
        raw, value = self.network(augmented)
        logits = inputs['prior'] + self.bound * torch.tanh(raw / self.bound)
        return logits.masked_fill(~inputs['actionMask'], -1e9), value.sigmoid()


def warm_start(path):
    if digest(path) != PROTOCOL['warmStart']['sha256']:
        raise ValueError('Wrong frozen representation warm-start checkpoint')
    saved = torch.load(path, map_location='cpu', weights_only=True)
    if saved['schema'] != BASE_SCHEMA or saved['width'] != PROTOCOL['width']:
        raise ValueError('Wrong representation schema/width')
    model = ExpertPolicy(saved['width'], PROTOCOL['residualBound'])
    state = dict(saved['state_dict'])
    weight = state['action.0.weight']
    split = DIMS['actions']
    # Input order is [34 original action features, normalized prior, city, context].
    # Zero the new column, preserving every old representation weight/offset.
    state['action.0.weight'] = torch.cat([weight[:, :split], torch.zeros_like(weight[:, :1]),
                                         weight[:, split:]], dim=1)
    model.network.load_state_dict(state, strict=True)
    model.zero_actor()
    return model


def save(path, model, **extra):
    reserved = {'schema', 'width', 'bound', 'priorAsActionFeature', 'state_dict'}
    if reserved & set(extra):
        raise ValueError('Checkpoint metadata cannot replace model identity')
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    torch.save(dict(schema=SCHEMA, width=model.width, bound=model.bound, priorAsActionFeature=True,
                    state_dict=model.state_dict(), **extra), temp)
    temp.replace(path)


def load(path):
    saved = torch.load(path, map_location='cpu', weights_only=True)
    if (saved.get('schema') != SCHEMA or saved.get('bound') != 16 or
            saved.get('priorAsActionFeature') is not True):
        raise ValueError('Wrong expert policy identity')
    model = ExpertPolicy(saved['width'], saved['bound'])
    model.load_state_dict(saved['state_dict'], strict=True)
    if not all(torch.isfinite(p).all() for p in model.parameters()):
        raise ValueError('Nonfinite expert policy checkpoint')
    return model, saved
