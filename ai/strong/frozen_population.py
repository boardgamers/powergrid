"""Load immutable research opponents without adding them to the learner optimizer."""
import hashlib
import json
from pathlib import Path
import re

import torch
from huggingface_hub import hf_hub_download
from model import policy_from_checkpoint


def validate_specs(specs):
    if not isinstance(specs, list) or {s['role'] for s in specs} != {'frozen0', 'frozen1', 'frozen2'} or len(specs) != 3:
        raise ValueError('Exactly three distinct frozen opponent roles required')
    for spec in specs:
        if not re.fullmatch(r'[0-9a-f]{40}', spec['revision']) or not re.fullmatch(r'[0-9a-f]{64}', spec['sha256']):
            raise ValueError('Pin immutable checkpoint revision and SHA256')
        if not spec['path'].startswith('runs/') or not spec['path'].endswith('.pt'):
            raise ValueError('Expected checkpoint artifact path')
        if spec['feature_revision'] != '4.0-multiplayer' or spec['architecture'] != 'multiplayer_ordered':
            raise ValueError('Population requires ordered schema-4 opponents')


def load_population(config, repo, device):
    if not config:
        return {}, []
    specs = json.loads(Path(config).read_text())
    validate_specs(specs)
    actors = {}
    for spec in specs:
        path = Path(hf_hub_download(repo, spec['path'], revision=spec['revision']))
        if hashlib.sha256(path.read_bytes()).hexdigest() != spec['sha256']:
            raise ValueError('Frozen checkpoint hash mismatch')
        checkpoint = torch.load(path, map_location='cpu', weights_only=True)
        for key in ['feature_revision', 'architecture', 'update']:
            if checkpoint.get(key) != spec[key]:
                raise ValueError('Frozen checkpoint provenance mismatch: ' + key)
        actor = policy_from_checkpoint(checkpoint).to(device).eval()
        actor.requires_grad_(False)
        actors[spec['role']] = actor
    return actors, specs


def actor_for_role(role, learner, league, frozen):
    if role == 'learner':
        return learner
    if role in frozen:
        return frozen[role]
    if re.fullmatch(r'snapshot[0-2]', role):
        return league.actors[int(role[-1]) % len(league.actors)]
    raise ValueError('Unknown neural opponent role: ' + role)
