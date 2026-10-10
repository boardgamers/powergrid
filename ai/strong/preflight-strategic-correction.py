"""Untrained correction: exact frozen-parent behavior through the export path."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import numpy as np
import torch
from huggingface_hub import hf_hub_download
from model_strategic import StrategicPolicy, FEATURE_REVISION, STATE_DIM, ACTION_DIM
from strategic_collection import get_model, read, write, ROOT
from infer import Model, Node

PARENT = {'revision': 'b115a2d78aae095e51fb72a5535b3507abdf90c0',
    'path': 'runs/discard-correction-v1/10102/best.pt',
    'sha256': '66a10b831a54843063bbca89743a542ed1f89515a16452a40483eef369c59bd8'}


def main():
    torch.set_num_threads(1)
    torch.manual_seed(11101)
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'ai/runs/strategic-correction-preflight-v1')
    out = parser.parse_args().output.resolve()
    out.mkdir(exist_ok=False)
    p = Path(hf_hub_download('coyotte508/powergrid-ai-germany-v1', PARENT['path'], revision=PARENT['revision']))
    assert hashlib.sha256(p.read_bytes()).hexdigest() == PARENT['sha256']
    cp = torch.load(p, map_location='cpu', weights_only=True)
    assert not cp.get('inference_only', False) and cp['architecture'] == 'multiplayer_discard_correction'
    net = StrategicPolicy()
    net.parent.load_state_dict(cp['state_dict'])
    assert all(torch.equal(v, net.parent.state_dict()[k]) for k, v in cp['state_dict'].items())
    draft = {'state_dict': net.state_dict(), 'architecture': 'multiplayer_strategic_correction',
        'model_args': {'margin': .025, 'parent_margin': .025}, 'feature_revision': FEATURE_REVISION,
        'state_dim': STATE_DIM, 'action_dim': ACTION_DIM, 'parent': PARENT, 'trained': False,
        'updates': 0, 'qualification_eligible': False}
    torch.save(draft, out/'zero-correction.pt')
    commands = [
        ('export-inference64.py', [out/'zero-correction.pt', out/'derivative']),
        ('check-export.py', [out/'derivative/inference64.pt', out/'derivative/inference64.onnx',
            ROOT/'ai/runs/multiplayer-serving-fixtures.jsonl', '--output', out/'export-parity.json'])]
    for script, args in commands:
        with (out/(script+'.log')).open('w') as f:
            subprocess.run([sys.executable, str(ROOT/'ai/strong'/script), *map(str, args)],
                           cwd=ROOT, stdout=f, stderr=subprocess.STDOUT, check=True)
    parent = get_model(read(ROOT/'ai/strong/strategic-teacher-training-protocol-v1.json'))
    candidate = Model(out/'derivative/inference64.onnx', threads=1)
    node = Node('strong/worker.cjs')
    count = eligible = 0
    try:
        with (ROOT/'ai/runs/multiplayer-serving-fixtures.jsonl').open() as f:
            for line in f:
                q = json.loads(line)['request']
                row = node.call({**q, 'featureRevision': FEATURE_REVISION})
                n = len(row['actions'])
                new_inputs = {'state': np.asarray([row['state']], np.float32),
                    'actions': np.asarray([row['actions']], np.float32), 'mask': np.ones((1,n), bool)}
                old_inputs = {**new_inputs, 'state': new_inputs['state'][:, :1216],
                    'actions': new_inputs['actions'][:, :, :100]}
                before = parent.session.run(None, old_inputs)
                after = candidate.session.run(None, new_inputs)
                for a, b in zip(before, after):
                    np.testing.assert_allclose(a, b, atol=1e-10, rtol=1e-10)
                assert int(before[0].argmax()) == int(after[0].argmax())
                eligible += int(row['state'][-1])
                count += 1
    finally:
        node.close()
    assert count == 2553 and read(out/'export-parity.json')['all_actions_match']
    result = {'positions': count, 'eligible': eligible, 'parent': PARENT,
        'parent_tensors_unchanged': True, 'parent_actions_and_values_preserved': True,
        'native_export_serving_parity': read(out/'export-parity.json'),
        'local_output': str(out.relative_to(ROOT)),
        'head_parameters': sum(p.numel() for p in net.head.parameters()), 'gradients': 0,
        'scope': 'Untrained zero correction only. No training, tuned threshold or strength claim.',
        'qualification_eligible': False}
    write(out/'preflight.json', result)
    write(ROOT/'ai/strong/strategic-correction-preflight-v1.json', result)
    print(result)


if __name__ == '__main__':
    main()
