"""Prepare only train/validation tensors from the complete verified HF corpus."""
import argparse
from collections import Counter
import importlib.util
import json
from pathlib import Path
import shutil

import numpy as np
from strategic_collection import ROOT, read, write, digest
from opponent_surrogate_training_v1 import SCHEMA, compact, input_digest, validate_arrays, group_weights
from opponent_surrogate_collection_v1 import contract

spec = importlib.util.spec_from_file_location('surrogate_data_manager', Path(__file__).with_name('manage-opponent-surrogate-collection-v1.py'))
manager = importlib.util.module_from_spec(spec); spec.loader.exec_module(manager)


def prepare(output):
    assert manager.INDEX.exists(), 'The complete fresh collection must verify before training-data preparation'
    index = read(manager.INDEX)
    assert index['complete'] and index['games'] == 2560 and index['twins'] == 640
    assert index['split_games'] == {'train': 1920, 'validation': 320, 'test': 320}
    assert index['code_hashes'] == manager.code_hashes()
    assert index['protocol_sha256'] == digest(manager.launcher.PROTOCOL)
    protocol = read(manager.launcher.PROTOCOL)
    counts = Counter()
    cases = [(name, cell) for name, cell in index['cases'].items() if cell['row']['split'] in ('train', 'validation')]
    for _, cell in cases: counts[cell['row']['split']] += cell['teacher_rows']
    output = output.resolve(); output.mkdir(parents=True, exist_ok=False)
    shutil.copy2(manager.INDEX, output/'collection-index.json')
    arrays = {}
    for split, count in counts.items():
        folder = output/split; folder.mkdir()
        arrays[split] = {k: np.lib.format.open_memmap(folder/(k+'.npy'), mode='w+', dtype=dtype, shape=(count, *shape))
                         for k, (dtype, shape) in SCHEMA.items()}
    positions = Counter(); games = Counter(); training_digests = set(); overlaps = 0; unique = set()
    # Always process train first. Validation/test never influence preprocessing.
    for case, cell in sorted(cases, key=lambda item: (item[1]['row']['split'] != 'train', item[0])):
        verified_path = manager.COLLECTED/case/'verified.json'
        assert digest(verified_path) == cell['verified_sha256']
        verified = manager.verified_receipt(case, full=True)
        assert verified['evidence'] == cell['evidence']
        split = cell['row']['split']; folder = verified_path.parent/'artifacts/games'
        for game in sorted(folder.glob('game-*'), key=lambda p: int(p.name.split('-')[1])):
            q = read(game/'contract.json'); assert q['split'] == split
            assert q == contract(protocol, q['players'], q['deal'], q['focal_seat'], q['rule'], 'collection')
            games[split] += 1
            with (game/'opponent-decisions.jsonl').open() as stream:
                for line in stream:
                    row = json.loads(line); packed = compact(row, q); identity = tuple(packed['identity'])
                    assert identity not in unique; unique.add(identity)
                    key = input_digest(packed)
                    if split == 'train': training_digests.add(key)
                    else: overlaps += key in training_digests
                    pos = positions[split]
                    for k in SCHEMA: arrays[split][k][pos] = packed[k]
                    positions[split] += 1
        print({'case': case, 'prepared_rows': dict(positions)}, flush=True)
    assert positions == counts and games == {'train': 1920, 'validation': 320}
    for split, data in arrays.items():
        for a in data.values(): a.flush()
        validate_arrays(data); group_weights(data)
    report = {'complete': True, 'collection_games': 2560, 'prepared_games': 2240,
              'split_games': dict(games), 'split_rows': dict(positions), 'test_records_included': False,
              'training_eligible': True, 'collection_index_sha256': digest(manager.INDEX),
              'collection_protocol_sha256': digest(manager.launcher.PROTOCOL),
              'preparer_sha256': digest(__file__),
              'tensorizer_sha256': digest(Path(__file__).with_name('opponent_surrogate_training_v1.py')),
              'validation_rows_with_exact_train_inputs': overlaps,
              'duplicate_input_scope': 'Natural identical public positions can recur across fresh deals. Report overlap without selecting/removing rows by outcomes; seed/deal identifiers are metadata only.',
              'files': {str(p.relative_to(output)): digest(p) for p in sorted(output.rglob('*')) if p.is_file()},
              'gradients': False, 'qualification_eligible': False, 'reserved_final_seeds_used': False}
    write(output/'data-check.json', report)
    print({k: report[k] for k in ('complete', 'split_rows', 'test_records_included', 'validation_rows_with_exact_train_inputs')})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__); parser.add_argument('output', type=Path)
    prepare(parser.parse_args().output)
