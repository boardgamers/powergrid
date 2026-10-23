"""Check real nonzero-offset games and reject corrupt/missing paired evidence."""
import argparse
import copy
from pathlib import Path
import subprocess
import sys
from huggingface_hub import hf_hub_download
from strategic_correction_screen import ROOT, PROTOCOL, read, write, digest, contract, validate_pin, verify_report, verify_local


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('pin', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    pin, protocol = read(args.pin), read(PROTOCOL)
    validate_pin(pin, 'parent', protocol)
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    # Partitioning must cover every prescribed deal exactly once.
    total = 0
    for cell in protocol['screens']:
        episodes = []
        for start in range(0, 16, 4):
            screen, _ = contract(protocol, cell['players'], cell['opponent'], start, start+4)
            episodes.extend(range(start*4*cell['players'], (start+4)*4*cell['players']))
            total += screen['games']
        assert episodes == list(range(cell['games']))
    assert total == protocol['planned_games_per_model'] == 6720
    with (out/'smoke.log').open('w') as log:
        subprocess.run([sys.executable, str(ROOT/'ai/strong/strategic_correction_screen.py'),
            'parent', '2', 'economic', '0', '1', str(out/'smoke'), '--smoke', '--pin', str(args.pin.resolve())],
            cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
    verify_local(out/'smoke', 'parent', 2, 'economic', 0, 1, True, pin)
    model = hf_hub_download(pin['repo'], pin['prefix']+'/inference64.onnx', revision=pin['revision'])
    assert digest(model) == pin['files']['inference64.onnx']
    plumbing = {**protocol, 'seed_template': 'strategic-correction-shard-plumbing-v1-{players}p'}
    with (out/'offset.log').open('w') as log:
        subprocess.run([sys.executable, str(ROOT/'ai/strong/evaluate.py'), model, '--players', '2',
            '--games', '32', '--deal-offset', '4', '--workers', '4', '--seed', plumbing['seed_template'].format(players=2),
            '--opponent', 'economic', '--output', str(out/'offset.json')], cwd=ROOT,
            stdout=log, stderr=subprocess.STDOUT, check=True)
    report = read(out/'offset.json')
    verify_report(report, plumbing, pin, 2, 'economic', 4, 8)
    mutations = {
        'wrong_offset': lambda r: r.update(deal_offset=0),
        'wrong_model': lambda r: r.update(model_sha256='0'*64),
        'missing_game': lambda r: r['results'].pop(),
        'duplicate_pair': lambda r: r['results'].__setitem__(1, r['results'][0]),
        'wrong_deal_seed': lambda r: r['results'][0].update(gameSeed='wrong'),
        'wrong_episode': lambda r: r['results'][0].update(episode=0),
        'truncated_game': lambda r: r['results'][0].update(truncated=True),
        'changed_credit': lambda r: r['results'][0].update(win=-1),
        'truncated_search': lambda r: r['results'][0].update(searchStats={'search_geo': {'decisions':1,'evaluations':1,'truncated':1}}),
    }
    for name, mutate in mutations.items():
        changed = copy.deepcopy(report)
        mutate(changed)
        try:
            verify_report(changed, plumbing, pin, 2, 'economic', 4, 8)
        except (AssertionError, ValueError):
            pass
        else:
            raise AssertionError('Corruption accepted: '+name)
    result = {'passed': True, 'games': 40, 'serving_positions': 2553,
        'nonzero_deal_offset_verified': 4, 'corruptions_rejected': sorted(mutations),
        'full_grid_games_per_model': total, 'protocol_sha256': digest(PROTOCOL),
        'qualification_eligible': False, 'scope': 'Runtime/verifier plumbing; no development or final candidate games.'}
    write(out/'preflight.json', result)
    print(result)


if __name__ == '__main__':
    main()
