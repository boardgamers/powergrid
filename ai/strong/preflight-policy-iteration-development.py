"""Exercise all model routes on disjoint plumbing games in the packaged runtime."""
import argparse
import copy
from pathlib import Path
import subprocess
import sys

import torch
from policy_iteration_development import ROOT, PROTOCOL, read, write, digest, validate_pin, contract, verify_local, verify_report


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--synthetic-root', type=Path, required=True)
    args = parser.parse_args()
    protocol = read(PROTOCOL)
    total = 0
    for cell in protocol['screens']:
        episodes = []
        for start in range(0, cell['deals'], 4):
            screen, _ = contract(protocol, cell['players'], cell['opponent'], start, start+4, 'development')
            episodes.extend(range(start*4*cell['players'], (start+4)*4*cell['players']))
            total += screen['games']
        assert episodes == list(range(cell['games']))
    assert total == protocol['planned_games_per_model'] == 6720
    assert total*len(protocol['models']) == protocol['planned_games_total'] == 33600
    out = ROOT/'ai/runs/policy-iteration-development-preflight-v2'
    out.mkdir(parents=True, exist_ok=False)
    cases, mutations_checked = {}, []
    for key in protocol['models']:
        local = None
        if key == 'parent':
            pin = protocol['parent_pin']
        else:
            directory = args.synthetic_root.resolve()/key
            cp = torch.load(directory/'inference64.pt', map_location='cpu', weights_only=True)
            assert cp['synthetic_untrained'] and cp['inference_only']
            pin = {'key': key, 'repo': protocol['repo'], 'files': {f: digest(directory/f) for f in ['inference64.pt', 'inference64.onnx']},
                   'feature_revision': cp['feature_revision'], 'model_args': cp['model_args'],
                   'synthetic_untrained': True, 'training_verified': False}
            local = directory/'inference64.onnx'
            # Neither a development run nor a live smoke may admit synthetic weights.
            try:
                validate_pin(pin, key, protocol)
            except (AssertionError, KeyError):
                pass
            else:
                raise AssertionError('Synthetic candidate admitted outside plumbing')
        pin_file = out/(key+'-pin.json')
        write(pin_file, pin)
        for n in [2, 6]:
            directory = out/(key+'-'+str(n)+'p')
            command = [sys.executable, '-u', 'ai/strong/policy_iteration_development.py', key, str(n),
                       'economic', '4', '5', str(directory), '--mode', 'plumbing', '--pin', str(pin_file)]
            if local:
                command += ['--local-model', str(local)]
            with (out/(directory.name+'.log')).open('w') as log:
                subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
            summary = verify_local(directory, key, n, 'economic', 4, 5, 'plumbing', pin)
            cases[directory.name] = {'model_pin': pin, 'summary': summary, 'evaluation_sha256': digest(directory/'evaluation.json')}
            print({'case': directory.name, 'games': summary['games'], 'passed': True}, flush=True)
            if key == 'public-1' and n == 6:
                original = read(directory/'evaluation.json')
                mutations = {
                    'wrong_model': lambda r: r.update(model_sha256='0'*64),
                    'wrong_offset': lambda r: r.update(deal_offset=0),
                    'wrong_seed_namespace': lambda r: r.update(seed='policy-iteration-development-v2-6p'),
                    'missing_game': lambda r: r['results'].pop(),
                    'duplicate_pair': lambda r: r['results'].__setitem__(1, r['results'][0]),
                    'wrong_deal': lambda r: r['results'][0].update(gameSeed='wrong'),
                    'wrong_episode': lambda r: r['results'][0].update(episode=0),
                    'wrong_credit': lambda r: r['results'][0].update(win=-1),
                    'truncated_game': lambda r: r['results'][0].update(truncated=True),
                    'truncated_search': lambda r: r['results'][0].update(searchStats={'economic': {'decisions': 1, 'evaluations': 1, 'truncated': 1}}),
                    'wrong_workers': lambda r: r.update(engine_workers=1),
                    'wrong_opponent': lambda r: r.update(opponent='legacy'),
                }
                for name, mutate in mutations.items():
                    changed = copy.deepcopy(original)
                    mutate(changed)
                    try:
                        verify_report(changed, protocol, pin, n, 'economic', 4, 5, 'plumbing')
                    except (AssertionError, ValueError):
                        mutations_checked.append(name)
                    else:
                        raise AssertionError('Corruption accepted: '+name)
    result = {'passed': True, 'cases': cases, 'games': sum(c['summary']['games'] for c in cases.values()),
              'protocol_sha256': digest(PROTOCOL), 'nonzero_deal_offset_verified': 4,
              'corruptions_rejected': sorted(mutations_checked), 'synthetic_admission_rejected': True,
              'games_per_development_model': total, 'gradients': False, 'reserved_final_seeds_used': False,
              'qualification_eligible': False, 'scope': '160 actual plumbing games across all five model routes,2p/6p and all four rules. Synthetic models are never admitted as trained candidates.'}
    assert result['games'] == 160 and len(mutations_checked) == 12
    write(out/'check.json', result)
    write(ROOT/'ai/strong/policy-iteration-development-preflight-v2.json', result)
    print({k: v for k, v in result.items() if k != 'cases'}, flush=True)


if __name__ == '__main__':
    main()
