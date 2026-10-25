"""Open and evaluate complete held-out behaviour only after validation selection freezes."""
import argparse
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import shutil

import numpy as np
from strategic_collection import ROOT, read, write, digest
from opponent_surrogate_collection_v1 import contract
from opponent_surrogate_training_v1 import SCHEMA, compact, input_digest, validate_arrays, group_weights, metrics
from opponent_surrogate_training_verification_v1 import validate_metrics
from opponent_surrogate_policy_v1 import SurrogatePolicy, make_policy


def load(name):
    spec = importlib.util.spec_from_file_location(name.replace('-', '_'), Path(__file__).with_name(name+'.py'))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module


selection = load('select-opponent-surrogate-v1')
manager = load('manage-opponent-surrogate-collection-v1')
DATA = ROOT/'ai/runs/opponent-surrogate-heldout-data-v1'
OUT = ROOT/'ai/runs/opponent-surrogate-heldout-evaluation-v1'


def expected_games():
    return {(n, r, deal, seat, 4*(deal*n+seat)+r)
            for n in range(2, 7) for r in range(4) for deal in range(28, 32) for seat in range(n)}


def prepare():
    selection.verify_frozen()  # Must precede any read of held-out raw decisions.
    trained, _, training, _ = selection.prerequisites()
    index = read(manager.INDEX)
    assert digest(manager.INDEX) == trained['collection_index_sha256']
    assert index['complete'] and index['split_games'] == {'train': 1920, 'validation': 320, 'test': 320}
    assert index['code_hashes'] == manager.code_hashes()
    cases = [(case, cell) for case, cell in index['cases'].items() if cell['row']['split'] == 'test']
    count = sum(cell['teacher_rows'] for _, cell in cases)
    assert sum(cell['row']['games'] for _, cell in cases) == 320 and count > 0
    frozen_sha = digest(selection.OUT/'frozen.json')
    DATA.mkdir(parents=True, exist_ok=False)
    write(DATA/'intent.json', {'frozen_selection_sha256': frozen_sha, 'created_at': datetime.now(timezone.utc).isoformat()})
    shutil.copy2(manager.INDEX, DATA/'collection-index.json')
    folder = DATA/'test'; folder.mkdir()
    arrays = {k: np.lib.format.open_memmap(folder/(k+'.npy'), mode='w+', dtype=dtype, shape=(count, *shape))
              for k, (dtype, shape) in SCHEMA.items()}
    seen_train = np.lib.format.open_memmap(DATA/'seen-train-inputs.npy', mode='w+', dtype=np.bool_, shape=(count,))
    train_digests = {input_digest({k: training['train'][k][i] for k in ('state', 'actions', 'mask')})
                     for i in range(len(training['train']['target']))}
    protocol = read(manager.launcher.PROTOCOL); pos = 0; identities = set(); games = set()
    for case, cell in sorted(cases):
        path = manager.COLLECTED/case/'verified.json'
        assert digest(path) == cell['verified_sha256']
        verified = manager.verified_receipt(case, full=True); assert verified['evidence'] == cell['evidence']
        for game in sorted((path.parent/'artifacts/games').glob('game-*'), key=lambda p: int(p.name.split('-')[1])):
            q = read(game/'contract.json')
            assert q == contract(protocol, q['players'], q['deal'], q['focal_seat'], q['rule'], 'collection')
            assert q['split'] == 'test'
            game_id = (q['players'], q['rule'], q['deal'], q['focal_seat'], q['episode'])
            assert game_id not in games; games.add(game_id)
            with (game/'opponent-decisions.jsonl').open() as stream:
                for line in stream:
                    row = compact(json.loads(line), q); identity = tuple(row['identity'])
                    assert identity not in identities; identities.add(identity)
                    for key in SCHEMA: arrays[key][pos] = row[key]
                    seen_train[pos] = input_digest(row) in train_digests; pos += 1
        print({'case': case, 'prepared_test_rows': pos}, flush=True)
    assert pos == count and games == expected_games()
    for array in [*arrays.values(), seen_train]: array.flush()
    validate_arrays(arrays); group_weights(arrays)
    assert {tuple(row[:5]) for row in arrays['identity']} == expected_games()
    assert frozen_sha == digest(selection.OUT/'frozen.json')
    write(DATA/'data-check.json', {'complete': True, 'games': 320, 'rows': count,
        'selection_frozen_sha256': frozen_sha, 'collection_index_sha256': digest(manager.INDEX),
        'training_data_check_sha256': trained['data_check_sha256'], 'preparer_sha256': digest(__file__),
        'test_rows_with_exact_training_inputs': int(seen_train.sum()),
        'files': {str(p.relative_to(DATA)): digest(p) for p in sorted(DATA.rglob('*')) if p.is_file()},
        'gradients': False, 'model_selection_allowed': False, 'qualification_eligible': False})
    print({'complete': True, 'test_games': 320, 'test_rows': count})


def load_test():
    selection.verify_frozen()
    report = read(DATA/'data-check.json')
    assert report['complete'] and report['games'] == 320 and report['model_selection_allowed'] is False
    assert report['selection_frozen_sha256'] == digest(selection.OUT/'frozen.json')
    assert report['preparer_sha256'] == digest(__file__)
    expected = {'collection-index.json', 'intent.json', 'seen-train-inputs.npy'} | {f'test/{k}.npy' for k in SCHEMA}
    assert set(report['files']) == expected
    assert {str(p.relative_to(DATA)) for p in DATA.rglob('*') if p.is_file()} == expected | {'data-check.json'}
    assert all(digest(DATA/name) == sha for name, sha in report['files'].items())
    assert digest(DATA/'collection-index.json') == report['collection_index_sha256'] == digest(manager.INDEX)
    data = {k: np.load(DATA/'test'/(k+'.npy'), mmap_mode='r', allow_pickle=False) for k in SCHEMA}
    validate_arrays(data); group_weights(data)
    assert len(data['target']) == report['rows']
    assert {tuple(row[:5]) for row in data['identity']} == expected_games()
    seen = np.load(DATA/'seen-train-inputs.npy', allow_pickle=False)
    assert seen.dtype == np.bool_ and seen.shape == (report['rows'],)
    assert int(seen.sum()) == report['test_rows_with_exact_training_inputs']
    return data, seen, report


def compare(data, scores, seen):
    assert set(scores) == {'selected', 'economic-prior'}
    full = {key: metrics(value, data) for key, value in scores.items()}
    for report in full.values(): validate_metrics(report, data)
    novel = ~seen
    novel_data = {k: v[novel] for k, v in data.items()}
    subset = {key: metrics(value[novel], novel_data) for key, value in scores.items()} if (data['mask'][novel].sum(1) > 1).any() else None
    return {'primary_all_test_rows': full, 'diagnostic_inputs_absent_from_training': subset,
            'test_rows_with_exact_training_inputs': int(seen.sum()),
            'macro_nll_delta_from_prior': full['selected']['macro_nll'] - full['economic-prior']['macro_nll'],
            'macro_agreement_delta_from_prior': full['selected']['macro_agreement'] - full['economic-prior']['macro_agreement'],
            'groups_with_worse_nll': [g for g, row in full['selected']['groups'].items()
                                      if row['nll'] > full['economic-prior']['groups'][g]['nll']]}


def evaluate():
    frozen, selected, policy = selection.verify_frozen()
    data, seen, data_report = load_test()
    OUT.mkdir(parents=True, exist_ok=False)
    frozen_sha = digest(selection.OUT/'frozen.json')
    write(OUT/'intent.json', {'frozen_selection_sha256': frozen_sha, 'started_at': datetime.now(timezone.utc).isoformat()})
    scores = {'selected': SurrogatePolicy(policy, selection.COLLECTED/'artifacts').scores(data),
              'economic-prior': SurrogatePolicy(make_policy([]), selection.COLLECTED/'artifacts').scores(data)}
    review = compare(data, scores, seen); np.savez(OUT/'scores.npz', **scores)
    assert frozen_sha == digest(selection.OUT/'frozen.json')
    write(OUT/'result.json', {**review, 'complete': True, 'test_games': 320, 'test_rows': len(data['target']),
        'independent_test_deals_per_count': 4,
        'selected_policy': selected['selected'], 'frozen_selection_sha256': frozen_sha,
        'policy_sha256': frozen['policy_sha256'], 'test_data_check_sha256': digest(DATA/'data-check.json'),
        'scores_sha256': digest(OUT/'scores.npz'), 'evaluator_sha256': digest(__file__),
        'training_result_sha256': digest(selection.TRAINING_RESULT),
        'gradients': False, 'models_reselected': False, 'qualification_eligible': False, 'reserved_final_seeds_used': False,
        'scope': 'Held-out imitation on every fixed test game, with a secondary natural-input-overlap diagnostic. No calibrated win probabilities, continuation fidelity or full-game strength claim.'})
    print({k: read(OUT/'result.json')[k] for k in ('complete', 'test_games', 'test_rows', 'macro_nll_delta_from_prior', 'macro_agreement_delta_from_prior')})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__); parser.add_argument('operation', choices=['prepare', 'evaluate'])
    globals()[parser.parse_args().operation]()
