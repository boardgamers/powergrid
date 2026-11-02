"""Frozen candidate pool; equal-logit ensemble, no data-dependent fitting."""
import json
from pathlib import Path
import torch
from torch import nn
from huggingface_hub import hf_hub_download
from data import digest,generator_digest
from residual import load

POOL=json.loads((Path(__file__).parent/'candidate-pool-v1.json').read_text())
SERVING_FILES=('model.py','features.cjs','teacher.cjs','game.cjs','game_rl.cjs','residual.py','ppo-protocol-v1.json')


class EqualLogitEnsemble(nn.Module):
    def __init__(self,members):
        super().__init__()
        if not members:raise ValueError('Empty ensemble')
        if len({(m.width,m.bound) for m in members})!=1:raise ValueError('Incompatible members')
        self.members=nn.ModuleList(members);self.width=members[0].width;self.bound=members[0].bound

    def forward(self,batch):
        outputs=[model(batch) for model in self.members]
        logits=torch.stack([x[0] for x in outputs]).mean(0).masked_fill(~batch['actionMask'],-1e9)
        # Auxiliary values are NOT calibrated probabilities for the ensemble policy.
        return logits,torch.stack([x[1] for x in outputs]).mean(0)


def load_candidates(names=None):
    names=[m['name'] for m in POOL['members']]+['ensemble'] if names is None else list(names)
    allowed={m['name'] for m in POOL['members']}|{'ensemble'}
    if not names or len(names)!=len(set(names)) or not set(names)<=allowed:raise ValueError('Unknown or duplicate candidate')
    required=set(names)-{'ensemble'}
    if 'ensemble' in names:required.update(POOL['ensemble']['members'])
    models={}
    engine=generator_digest()
    for pin in POOL['members']:
        if pin['name'] not in required:continue
        path=hf_hub_download(pin['repo'],pin['path'],revision=pin['revision'])
        if digest(path)!=pin['sha256']:raise ValueError('Candidate checkpoint hash mismatch')
        model,saved=load(path)
        if saved['update']!=pin['update'] or saved['config']['generatorDigest']!=engine:raise ValueError('Candidate runtime/selection mismatch')
        for name in SERVING_FILES:
            if digest(Path(__file__).parent/name)!=saved['config']['sourceFiles'][name]:raise ValueError('Candidate serving source changed: '+name)
        models[pin['name']]=model.eval()
    if 'ensemble' in names:
        if POOL['ensemble']['weights']!=[1]*len(POOL['ensemble']['members']):raise ValueError('Only predeclared equal weights supported')
        models['ensemble']=EqualLogitEnsemble([models[n] for n in POOL['ensemble']['members']]).eval()
    return {name:models[name] for name in names}
