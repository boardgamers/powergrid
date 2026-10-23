"""Verify the entire frozen training manifest without performing gradients."""
import argparse
from collections import Counter
from pathlib import Path
import numpy as np
from strategic_correction_data import load, arrays
from strategic_collection import ROOT, read, write, digest


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    design_path = ROOT/'ai/strong/strategic-correction-design-v1.json'
    rows = load(read(args.manifest), read(design_path))
    negative = 0
    weights = []
    for split, count in [('train', 1440), ('validation', 480)]:
        selected = [row for row in rows if row['split'] == split]
        assert len(selected) == count
        data = arrays(selected)
        for name in ['state', 'actions', 'target', 'precision']:
            assert np.isfinite(data[name]).all(), name
        indices = np.arange(count), data['proposal_index']
        assert data['mask'][indices].all()
        assert (data['target'][indices] == 0).all()
        weight = data['precision'][data['mask']]
        assert (weight >= .25).all() and (weight <= 1).all()
        weights.extend(weight.tolist())
        negative += int((data['target'][data['mask']] < 0).sum())
    report = {'passed': True, 'roots': len(rows),
        'splits': dict(Counter(row['split'] for row in rows)),
        'by_count': dict(Counter(str(row['players']) for row in rows)),
        'by_decision': dict(Counter(row['decision'] for row in rows)),
        'parent_proposals_reproduced': len(rows), 'parent_targets_zero': True,
        'negative_advantages_retained': negative,
        'uncertainty_weight_range': [min(weights), max(weights)],
        'design_sha256': digest(design_path), 'manifest_sha256': digest(args.manifest),
        'gradients': 0, 'qualification_eligible': False}
    write(args.output, report)
    print(report)


if __name__ == '__main__':
    main()
