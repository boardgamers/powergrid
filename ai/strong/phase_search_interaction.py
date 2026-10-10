"""Exploratory four-arm effects, preserving shared deals across every arm."""
import numpy as np

from arena_statistics import validate_pairs


EFFECTS = {
    'auction_without_building': {'auction': 1, 'raw': -1},
    'auction_with_building': {'all': 1, 'building': -1},
    'building_without_auction': {'building': 1, 'raw': -1},
    'building_with_auction': {'all': 1, 'auction': -1},
    'interaction': {'all': 1, 'auction': -1, 'building': -1, 'raw': 1},
}


def factorial(arms, players, repeats=10000, seed=8501):
    """Input reports must already pass the model/source/routing collectors."""
    if set(arms) != {'raw', 'auction', 'building', 'all'}:
        raise ValueError('Expected all four phase arms')
    if not isinstance(repeats, int) or repeats < 1:
        raise ValueError('Expected positive bootstrap repetitions')
    indexed = {}
    for arm, rows in arms.items():
        validate_pairs(rows, players)
        if any(row['truncated'] for row in rows):
            raise ValueError('Truncated games cannot enter phase contrasts')
        indexed[arm] = {
            (r['gameSeed'], r['variant'], r['sealed'], r['seat']): float(r['win'])
            for r in rows
        }
    keys = sorted(indexed['raw'])
    if any(set(rows) != set(keys) for rows in indexed.values()):
        raise ValueError('Four-arm pair sets do not match')

    def summarize(selected):
        deals = sorted({key[0] for key in selected})
        by_deal = {deal: [key for key in selected if key[0] == deal] for deal in deals}
        if len({len(v) for v in by_deal.values()}) != 1:
            raise ValueError('Unequal within-deal coverage')
        # Draw a shared deal once and reuse it across all four arms. Independently
        # bootstrapping arm rates would discard covariance and give wrong CIs.
        picks = np.random.default_rng(seed).integers(len(deals), size=(repeats, len(deals)))
        effects = {}
        for name, coefficients in EFFECTS.items():
            differences = np.array([
                np.mean([sum(weight * indexed[arm][key] for arm, weight in coefficients.items())
                         for key in by_deal[deal]])
                for deal in deals
            ])
            effects[name] = {
                'coefficients': coefficients,
                'win_share_difference': float(differences.mean()),
                'paired_deal_bootstrap_95_interval': np.quantile(
                    differences[picks].mean(axis=1), [.025, .975]).tolist(),
            }
        return {'games_per_arm': len(selected), 'independent_deals': len(deals), 'effects': effects}

    return {
        'overall': summarize(keys),
        'rules': {variant + ('/sealed' if sealed else '/open'): summarize(
            [key for key in keys if key[1] == variant and key[2] == sealed])
            for variant in ['original', 'recharged'] for sealed in [False, True]},
        'qualification_eligible': False,
        'scope': 'Exploratory marginal 95% intervals on reused development deals; no multiplicity adjustment. '
                 'Interaction is all minus auction minus building plus raw; positive means complementarity '
                 'on the win-share scale. This does not validate distillation targets.',
    }
