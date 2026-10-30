"""Separate target sampling noise, ranking quality and routing on existing data."""
from collections import defaultdict
import json
from pathlib import Path
import numpy as np
import torch

from model import Inference64Policy
from model_nomination_discount_v1 import from_checkpoint
from model_policy_iteration import ensemble_advantages
from run_nomination_minipc_v1 import read, save, digest, now

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'ai/strong/nomination-target-diagnostic-v1.json'


def choose(delta, allowed, parent, margin):
    ix = np.where(allowed, delta, -np.inf).argmax(1)
    return np.where(delta[np.arange(len(ix)), ix] > margin, ix, parent)


def metrics(choice, ids, data):
    achieved = data['target'][ids, choice[ids]]
    changes = choice[ids] != data['proposal_index'][ids]
    return {'roots': len(ids), 'changes': int(changes.sum()),
        'positive_changes': int(((achieved > 0) & changes).sum()),
        'negative_changes': int(((achieved < 0) & changes).sum()),
        'mean_sampled_advantage': float(achieved.mean())}


def main():
    assert not OUT.exists(), 'Preserve original analysis'
    folder = ROOT/'ai/runs/nomination-discount-training-data-v1'; report = read(folder/'report.json')
    assert all(digest(folder/k) == v for k,v in report['files'].items())
    data = dict(np.load(folder/'data.npz', allow_pickle=False)); meta = read(folder/'metadata.json')
    groups = defaultdict(list)
    for i,r in enumerate(meta):
        groups[r['split']+'/all'].append(i)
        groups[r['split']+'/'+r['variant']+('/sealed' if r['sealed'] else '/open')].append(i)
    groups = {k:np.array(v) for k,v in sorted(groups.items())}
    parent = data['proposal_index']; ids = np.arange(len(meta))
    # Select on one pre-existing 32-world half and score on the other, both directions.
    choices = [choose(data['target_'+h], data['mask'], parent, .025) for h in ('a','b')]
    reliability = {}
    for name,g in groups.items():
        in_sample = (data['target_a'][ids,choices[0]]+data['target_b'][ids,choices[1]])/2
        cross_sample = (data['target_b'][ids,choices[0]]+data['target_a'][ids,choices[1]])/2
        reliability[name] = {'roots':len(g), 'same_half_selected_gain':float(in_sample[g].mean()),
            'cross_half_selected_gain':float(cross_sample[g].mean()),
            'optimism_gap':float((in_sample[g]-cross_sample[g]).mean()),
            'same_selected_action_fraction':float((choices[0][g]==choices[1][g]).mean())}
    torch.set_num_threads(1); models = []; exports = read(ROOT/'ai/strong/nomination-discount-export-v1.json')
    previous = read(ROOT/'ai/strong/nomination-discount-validation-analysis-v1.json')
    for arm in exports['arms']:
        name = arm['arm']; path = ROOT/f'ai/runs/nomination-discount-export-v1/{name}/inference64.pt'
        assert digest(path) == arm['files']['inference64.pt']
        cp = torch.load(path, map_location='cpu', weights_only=True)
        net = Inference64Policy(from_checkpoint(cp), 'float64-exp-div-silu-v1').eval().policy
        score_rows = []; actual = []
        with torch.inference_mode():
            for begin in range(0, len(meta), 128):
                sl = slice(begin,begin+128)
                s,a,m = [torch.from_numpy(data[k][sl].copy()) for k in ('state','actions','mask')]
                s,a = s.double(),a.double()
                logits,_ = net.parent(s[:,:1217].contiguous(),a[:,:,:101].contiguous(),m)
                np.testing.assert_array_equal(logits.argmax(1).numpy(),parent[sl])
                context,embedding = net.embeddings(s,a)
                score_rows.append(net.score_heads(context,embedding,s,a).numpy())
                actual.extend(net(s,a,m)[0].argmax(1).tolist())
        scores = np.concatenate(score_rows,axis=1)
        deltas = scores-scores[:,ids,parent][:,:,None]
        mean = deltas.mean(0)
        cautious = ensemble_advantages(torch.from_numpy(scores),torch.from_numpy(parent),1.).numpy()
        allowed = data['mask'] if net.all_legal else data['old_mask']
        routed = choose(cautious,allowed,parent,.025)
        np.testing.assert_array_equal(routed,actual)
        diagnostic_choices = {'frozen_routing':routed,
            'mean_with_original_margin':choose(mean,allowed,parent,.025),
            'mean_positive_only':choose(mean,allowed,parent,0.)}
        measured = {key:{g:metrics(choice,group,data) for g,group in groups.items()} for key,choice in diagnostic_choices.items()}
        old = next(r for r in previous['arms'] if r['arm']==name)['groups']['all']
        checked = measured['frozen_routing']['validation/all']
        assert checked['changes']==old['changes']
        assert abs(checked['mean_sampled_advantage']-old['mean_sampled_advantage'])<1e-12
        row = {'arm':name,'checkpoint_sha256':digest(path),'diagnostic_routes':measured}
        models.append(row)
        print(json.dumps({'arm':name,'summary':{k:{s:v[s+'/all'] for s in ('train','validation')} for k,v in measured.items()}}),flush=True)
    save(OUT, {'created_at':now(),'complete':True,'data_report_sha256':digest(folder/'report.json'),
        'export_report_sha256':digest(ROOT/'ai/strong/nomination-discount-export-v1.json'),
        'analysis_sha256':digest(__file__),'target_half_checks':reliability,'models':models,
        'scope':'Retrospective analysis only. Half-selection uses disjoint simulation worlds but the same roots and opponent assumptions. Model validation targets were used for checkpoint selection. Alternative routes are diagnostics, not selected policies or fresh strength evidence.',
        'new_games':0,'new_gradients':0,'changed_models':0,'qualified':False,'reserved_final_seeds_used':False})


if __name__ == '__main__':
    main()
