"""Resume all frozen development cases after both runtime probes verify."""
import argparse
import fcntl
import importlib.util
import os
import re
from types import SimpleNamespace
from huggingface_hub import get_token
from strategic_correction_screen import ROOT, PROTOCOL, SOURCE, read, write, digest, pin_hash, case_key


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('keys', nargs='+', choices=['parent', '11101', '11102'])
    parser.add_argument('--launch', action='store_true')
    args = parser.parse_args()
    assert len(set(args.keys)) == len(args.keys)
    spec = importlib.util.spec_from_file_location('screen_manager', ROOT/'ai/strong/manage-strategic-correction-screen.py')
    manager = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(manager)
    protocol, source = read(PROTOCOL), read(SOURCE)
    guards = ROOT/'ai/runs/strategic-correction-screen-launches-v1'
    guards.mkdir(exist_ok=True)
    with (guards/'.batch.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        pins = {key: manager.get_pin(key) for key in args.keys}
        for key in args.keys:
            admission = manager.admission(key)
            assert admission['admitted'], 'Repartition execution; never shorten game horizons'
            print({'runtime_admission': admission}, flush=True)
            if args.launch:
                write(ROOT/'ai/strong'/f'strategic-correction-screen-{key}-admission-v1.json', admission)
        # Start the expensive independent-search cells first, then the other
        # primary opponents, then extensions. Both seeds use the same full grid.
        cells = sorted(protocol['screens'], key=lambda c: (
            0 if c['opponent'] == 'search_geo' else 1 if c['stage'] == 'primary' else 2,
            -c['players'], c['opponent']))
        plan, existing = [], 0
        for cell in cells:
            for start in range(0, cell['deals'], 4):
                for key in args.keys:
                    item = SimpleNamespace(key=key, players=cell['players'], opponent=cell['opponent'],
                        start=start, end=start+4, smoke=False)
                    guard = guards/(case_key(key, item.players, item.opponent, start, start+4)+'.json')
                    if guard.exists():
                        old = read(guard)
                        assert old['stage'] == 'launched' and re.fullmatch('[a-f0-9]{24}', old['job_id']), \
                            'Unresolved launch intent: inspect the original job before resuming'
                        assert old['source_revision'] == source['revision'] and old['source_sha256'] == source['sha256']
                        assert old['protocol_sha256'] == digest(PROTOCOL) and old['model_pin_sha256'] == pin_hash(pins[key])
                        assert all(old[name] == getattr(item, name) for name in ['key','players','opponent','start','end','smoke'])
                        existing += 1
                    else:
                        plan.append(item)
        print({'launch': args.launch, 'new_jobs': len(plan), 'already_dispatched': existing,
            'new_games': sum(4*x.players*(x.end-x.start) for x in plan)}, flush=True)
        if not args.launch:
            return
        # Keep authentication solely in the subprocess environment. The guarded
        # launcher passes the secret name to HF, never its value in arguments.
        os.environ['HF_TOKEN'] = os.environ.get('HF_TOKEN') or get_token() or ''
        assert os.environ['HF_TOKEN'], 'HF authentication is unavailable'
        for i, item in enumerate(plan):
            manager.launch(item)
            print({'dispatched_this_run': i+1, 'planned_this_run': len(plan)}, flush=True)


if __name__ == '__main__':
    main()
