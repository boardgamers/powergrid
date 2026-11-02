"""Heuristic-anchored residual policy. Zero head exactly recovers greedy teacher."""
import json
from pathlib import Path
import torch
from torch import nn
from data import digest
from model import GraphPolicy, SCHEMA as BASE_SCHEMA, collate, tensor_row

PROTOCOL=json.loads((Path(__file__).parent/'ppo-protocol-v1.json').read_text())
SCHEMA=PROTOCOL['schema']


class ResidualPolicy(nn.Module):
    def __init__(self,width=64,bound=8):
        super().__init__()
        self.width=width;self.bound=bound
        self.network=GraphPolicy(width)
        self.zero_actor()

    def zero_actor(self):
        nn.init.zeros_(self.network.action[-1].weight)
        nn.init.zeros_(self.network.action[-1].bias)

    def forward(self,batch):
        raw,value=self.network(batch)
        logits=batch['prior']+self.bound*torch.tanh(raw/self.bound)
        return logits.masked_fill(~batch['actionMask'],-1e9),value.sigmoid()


def warm_start(path):
    if digest(path)!=PROTOCOL['warmStart']['sha256']:
        raise ValueError('Wrong warm-start checkpoint')
    saved=torch.load(path,map_location='cpu',weights_only=True)
    assert saved['schema']==BASE_SCHEMA
    model=ResidualPolicy(saved['width'],PROTOCOL['residualBound'])
    model.network.load_state_dict(saved['state_dict'])
    model.zero_actor()
    return model


def row(observation,relations=None):
    result=tensor_row(observation,relations)
    prior=torch.tensor(observation['prior'],dtype=torch.float32)
    if prior.shape!=(len(result['actions']),) or not torch.isfinite(prior).all() or float(prior.max())!=0:
        raise ValueError('Invalid heuristic prior')
    result['prior']=prior
    return result


def batch(rows):
    result=collate(rows)
    result['prior']=torch.full(result['actionMask'].shape,-1e9)
    for i,r in enumerate(rows):result['prior'][i,:len(r['prior'])]=r['prior']
    return result


def save(path,model,**extra):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix('.tmp')
    torch.save(dict(schema=SCHEMA,width=model.width,bound=model.bound,state_dict=model.state_dict(),**extra),temp)
    temp.replace(path)


def load(path):
    saved=torch.load(path,map_location='cpu',weights_only=True)
    if saved['schema']!=SCHEMA:raise ValueError('Wrong residual schema')
    model=ResidualPolicy(saved['width'],saved['bound'])
    model.load_state_dict(saved['state_dict'])
    return model,saved
