"""Frozen-parent inference on expanded legal bid menus; no gradients or game outcomes."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import onnxruntime as ort
import torch
from model import policy_from_checkpoint, tensors

p = argparse.ArgumentParser(__doc__)
p.add_argument('encoded', type=Path)
p.add_argument('checkpoint', type=Path)
p.add_argument('model', type=Path)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
assert sha(a.checkpoint) == '1f9d1c89908ab036f6e6a54facba94b352bbae005e1ac042d88c60067e895224'
assert sha(a.model) == '2f1dd42625ea86404155e63124e55d95d07016027a0ceda4e08164357b554927'
torch.set_num_threads(1)
cp = torch.load(a.checkpoint, map_location='cpu', weights_only=True)
net = policy_from_checkpoint(cp).eval()
opts = ort.SessionOptions(); opts.intra_op_num_threads = 1
session = ort.InferenceSession(str(a.model), opts, providers=['CPUExecutionProvider'])
rows, cells = [], {}
parity = {kind: {'positions': 0, 'strict_failures': [], 'decision_mismatches': [],
                 'max_logit_error': 0., 'max_value_error': 0.} for kind in ['original', 'expanded']}
for line in a.encoded.read_text().splitlines():
    data = json.loads(line)
    choices = {}
    for kind in ['original', 'expanded']:
        obs = data[kind]
        x = tensors([obs], 'cpu')
        with torch.inference_mode():
            expected = [v.numpy() for v in net(*x)]
        actual = session.run(None, dict(zip(['state', 'actions', 'mask'], [v.numpy() for v in x])))
        item = parity[kind]; item['positions'] += 1
        for i, name in enumerate(['max_logit_error', 'max_value_error']):
            item[name] = max(item[name], float(np.max(np.abs(actual[i] - expected[i]))))
            if not np.allclose(actual[i], expected[i], rtol=1e-4, atol=1e-5):
                item['strict_failures'].append({'position': data['position'], 'output': i})
        if int(actual[0].argmax()) != int(expected[0].argmax()):
            item['decision_mismatches'].append(data['position'])
        choices[kind] = obs['moves'][int(actual[0].argmax())]
    changed = choices['original'] != choices['expanded']
    omitted = choices['expanded'] not in data['original']['moves']
    cell = cells.setdefault(data['key'], {'positions': 0, 'changed_choices': 0, 'chose_omitted_bid': 0,
                                        'changed_to_retained_move': 0, 'original_actions': 0, 'expanded_actions': 0})
    cell['positions'] += 1; cell['changed_choices'] += changed; cell['chose_omitted_bid'] += omitted
    cell['changed_to_retained_move'] += changed and not omitted
    cell['original_actions'] += len(data['original']['moves']); cell['expanded_actions'] += len(data['expanded']['moves'])
    if omitted: assert choices['expanded']['name'] == 'Bid'
    rows.append({'position': data['position'], 'key': data['key'], **choices,
                 'chose_omitted_bid': omitted, 'changed_choice': changed,
                 'original_actions': len(data['original']['moves']), 'expanded_actions': len(data['expanded']['moves'])})
assert len(rows) == 142
result = {'checkpoint_sha256': sha(a.checkpoint), 'model_sha256': sha(a.model),
          'encoded_sha256': sha(a.encoded), 'positions': len(rows), 'cells': cells, 'rows': rows,
          'parity': parity, 'qualification_eligible': False, 'trained': False,
          'interpretation': 'Counterfactual single-position choice coverage of the fixed fixture corpus. No game outcomes were measured and no training or live encoder was changed. Model preference is not proof of move quality; an expanded menu would need a separately versioned controlled strength experiment.'}
a.output.write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'positions': len(rows), 'cells': cells, 'parity': parity}))
