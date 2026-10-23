"""Read-only calibration of the fixed strategic models on their frozen labels."""
from collections import defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
FROZEN = ROOT/'ai/runs/strategic-correction-source-v1'
sys.path.insert(0, str(FROZEN/'ai/strong'))
from strategic_correction_data import load, arrays
from model import policy_from_checkpoint


def main():
    torch.set_num_threads(4)
    read = lambda p: json.loads(p.read_text())
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    source = read(ROOT/'ai/strong/strategic-correction-source-v1.json')
    data_path = ROOT/'ai/strong/strategic-teacher-training-results-v1.json'
    assert digest(data_path) == source['data_manifest_sha256']
    design = read(FROZEN/'ai/strong/strategic-correction-design-v1.json')
    rows = load(read(data_path), design)
    data = arrays(rows)
    states = torch.from_numpy(data['state']).double()
    actions = torch.from_numpy(data['actions']).double()
    report = {'training_source':source, 'data_manifest_sha256':digest(data_path), 'models':{},
        'gradients':False, 'qualification_eligible':False,
        'scope':'Post-hoc diagnostic of fixed teacher labels and fixed models. No threshold selection, retraining or whole-game strength claim.'}
    output = ROOT/'ai/runs/strategic-correction-calibration-v1'
    output.mkdir(exist_ok=False)
    for key in ['11101','11102']:
        pin = read(ROOT/'ai/strong/strategic-correction-screen-pins-v1'/(key+'.json'))
        path = ROOT/'ai/runs/strategic-correction-verified-v1'/key/'derivative/inference64.pt'
        assert digest(path) == pin['files']['inference64.pt']
        net = policy_from_checkpoint(torch.load(path,map_location='cpu',weights_only=True)).eval().policy
        with torch.inference_mode():
            context, embedding = net.embeddings(states, actions)
            scores = net.head(context, embedding, states, actions).numpy()
        delta = scores - scores[np.arange(len(rows)),data['proposal_index'],None]
        eligible = np.where(data['mask'],delta,-1e9)
        chosen = np.where(eligible.max(1)>design['margin'],eligible.argmax(1),data['proposal_index'])
        records = []; groups = defaultdict(list)
        for i,row in enumerate(rows):
            index = int(chosen[i]); changed = index != row['proposal_index']
            record = {k:row[k] for k in ['rootId','split','players','decision','variant','sealed','source_mode','deal']}
            record.update(changed=changed, predicted_gain=float(delta[i,index]),
                teacher_gain=float(data['target'][i,index]),
                chosen_action_index=index, parent_action_index=row['proposal_index'])
            records.append(record)
            names = [row['split'], row['split']+'/'+row['decision'], row['split']+'/'+str(row['players'])+'p',
                row['split']+'/'+str(row['players'])+'p/'+row['decision']]
            if changed:
                gain = record['predicted_gain']
                bin_name = '.025-.05' if gain<.05 else '.05-.10' if gain<.1 else '.10-.20' if gain<.2 else '.20+'
                names.append(row['split']+'/changed-predicted-gain/'+bin_name)
            for name in names: groups[name].append(record)
        summaries = {}
        for name, items in groups.items():
            changed = [r for r in items if r['changed']]
            summaries[name] = {'roots':len(items), 'changed':len(changed),
                'changed_fraction':len(changed)/len(items),
                'mean_predicted_gain':float(np.mean([r['predicted_gain'] for r in items])),
                'mean_teacher_gain':float(np.mean([r['teacher_gain'] for r in items])),
                'changed_mean_teacher_gain':float(np.mean([r['teacher_gain'] for r in changed])) if changed else None,
                'changed_negative_teacher_fraction':sum(r['teacher_gain']<0 for r in changed)/len(changed) if changed else None}
        with gzip.open(output/(key+'.jsonl.gz'),'wt') as stream:
            for row in records: stream.write(json.dumps(row)+'\n')
        report['models'][key] = {'pin':pin, 'groups':summaries, 'records_sha256':digest(output/(key+'.jsonl.gz'))}
        print(key, json.dumps({k:v for k,v in summaries.items() if k in ['train','validation','validation/nomination','validation/bid','validation/building']}), flush=True)
    (output/'calibration.json').write_text(json.dumps(report,indent=2)+'\n')
    (ROOT/'ai/strong/strategic-correction-calibration-v1.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__ == '__main__':
    main()
