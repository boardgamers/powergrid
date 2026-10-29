"""Describe exported nomination choices on saved validation targets; no strength claim."""
from collections import defaultdict
import numpy as np
from export_nomination_training_v1 import session
from prepare_auction_discount_teacher_v2 import ROOT, read, save, digest


def main():
    output = ROOT/'ai/strong/nomination-discount-validation-analysis-v1.json'; assert not output.exists()
    data_root = ROOT/'ai/runs/nomination-discount-training-data-v1'
    data = dict(np.load(data_root/'data.npz', allow_pickle=False)); meta = read(data_root/'metadata.json')
    exports = read(ROOT/'ai/strong/nomination-discount-export-v1.json'); reports = []
    for arm in exports['arms']:
        path = ROOT/f"ai/runs/nomination-discount-export-v1/{arm['arm']}/inference64.onnx"
        assert digest(path) == arm['files']['inference64.onnx']; model = session(path); choices = []
        for start in range(0, len(meta), 64):
            batch = {k: np.ascontiguousarray(data[k][start:start+64]) for k in ('state', 'actions', 'mask')}
            choices.extend(model.run(None, batch)[0].argmax(1).tolist())
        choices = np.asarray(choices); ids = np.arange(len(meta)); achieved = data['target'][ids, choices]
        changed = choices != data['proposal_index']; groups = defaultdict(list)
        for i, row in enumerate(meta):
            if row['split'] != 'validation': continue
            for key in ('all', 'players/'+str(row['players']), 'kind/'+row['kind'],
                        'rules/'+row['variant']+('/sealed' if row['sealed'] else '/open')): groups[key].append(i)
        results = {}
        for label, group in groups.items():
            g = np.asarray(group)
            results[label] = {'roots': len(g), 'changes': int(changed[g].sum()),
                'positive_changes': int(((achieved[g] > 0) & changed[g]).sum()),
                'negative_changes': int(((achieved[g] < 0) & changed[g]).sum()),
                'mean_sampled_advantage': float(achieved[g].mean()),
                'half_a_advantage': float(data['target_a'][g, choices[g]].mean()),
                'half_b_advantage': float(data['target_b'][g, choices[g]].mean())}
        reports.append({'arm': arm['arm'], 'model_sha256': digest(path), 'groups': results})
        print({'arm': arm['arm'], **results['all']}, flush=True)
    save(output, {'complete': True, 'arms': reports, 'data_report_sha256': digest(data_root/'report.json'),
                  'export_report_sha256': digest(ROOT/'ai/strong/nomination-discount-export-v1.json'),
                  'new_games': 0, 'new_gradients': 0, 'qualified': False,
                  'interpretation': 'Validation positions were used for checkpoint selection. These are sampled conditional continuation margins, not independent whole-game win rates or calibrated confidence.'})


if __name__ == '__main__': main()
