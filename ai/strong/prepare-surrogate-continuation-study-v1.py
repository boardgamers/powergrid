"""Freeze study inputs only after complete fresh roots and validation-selected training."""
import importlib.util
from pathlib import Path

from strategic_collection import ROOT, read, write, digest
from surrogate_continuation_study_v1 import code_hashes, MODES, SAMPLES, MAX_STEPS

STRONG = ROOT/'ai/strong'
OUT = ROOT/'ai/runs/surrogate-continuation-study-inputs-v1'


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, STRONG/filename)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module


def prepare():
    manager = load('study_root_manager', 'manage-surrogate-continuation-roots-v1.py')
    selection = load('study_surrogate_selection', 'select-opponent-surrogate-v1.py')
    assert manager.INDEX.exists(), 'Complete and freeze every original fresh-root shard first'
    assert (selection.OUT/'frozen.json').exists(), 'Complete actual HF training and validation-only selection first'
    root_index = manager.index()
    frozen, report, policy = selection.verify_frozen()
    roots = read(ROOT/root_index['root_manifest'])
    assert digest(ROOT/root_index['root_manifest']) == root_index['root_manifest_sha256']
    assert root_index['games'] == 160 and set(roots['phase_counts']) == {
        f'{n}/{rule}/{phase}' for n in range(2, 7) for rule in range(4) for phase in ('plant', 'bid', 'building')}
    assert all(root['identity']['mode'] == 'root' for root in roots['roots'])
    tasks = [{'root_id': root['root_id'], 'mode': mode, 'begin': 0, 'count': SAMPLES}
             for root in roots['roots'] for mode in MODES]
    evidence = {'complete': True, 'root_index_sha256': digest(manager.INDEX),
                'root_manifest_sha256': root_index['root_manifest_sha256'],
                'selection_freeze_sha256': digest(selection.OUT/'frozen.json'),
                'surrogate_policy_sha256': digest(selection.OUT/'policy.json'),
                'training_result_sha256': report['training_result_sha256'],
                'protocol_sha256': root_index['protocol_sha256'], 'code_hashes': code_hashes(),
                'preparer_sha256': digest(__file__), 'roots': len(roots['roots']), 'tasks': tasks,
                'samples': SAMPLES, 'actions_per_root': 2, 'max_steps': MAX_STEPS,
                'continuations': len(tasks)*SAMPLES*2, 'hf_jobs_admitted': False,
                'gradients': False, 'qualification_eligible': False, 'reserved_final_seeds_used': False,
                'scope': 'Inputs and fixed action pairs only; HF nested-reference runtime admission is still required.'}
    assert frozen['learned_surrogate_selected'] and evidence['continuations'] <= 23040
    OUT.mkdir(parents=True, exist_ok=False)
    write(OUT/'roots.json', roots); write(OUT/'policy.json', policy)
    assert digest(OUT/'roots.json') == root_index['root_manifest_sha256']
    assert digest(OUT/'policy.json') == evidence['surrogate_policy_sha256']
    write(OUT/'frozen.json', evidence)
    print({key: evidence[key] for key in ('complete', 'roots', 'continuations', 'hf_jobs_admitted')})
    return evidence


if __name__ == '__main__': prepare()
