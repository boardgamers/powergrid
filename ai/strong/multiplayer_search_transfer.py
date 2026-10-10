"""Fixed search48 versus the independent search reference at 3–6 players."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

from huggingface_hub import HfApi, hf_hub_download
from search_transfer import ROOT, read, write, digest, verify as verify_transfer

PROTOCOL = ROOT/'ai/strong/multiplayer-search-transfer-protocol-v1.json'


def case_for(protocol, players):
    return next(c for c in protocol['cases'] if c['players'] == players)


def verify(report, protocol, key, players, smoke=False, guided=True):
    case = case_for(protocol, players)
    assert case['opponent'] == 'search_geo'
    # The shared verifier accepts an optional frozen neural opponent. This
    # experiment only uses search_geo, so no neural-opponent pin is needed.
    return verify_transfer(report, {**protocol, 'frozen_opponent': {}}, key, case, guided, smoke)


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('key', choices=['parent', '10101', '10102'])
    p.add_argument('players', type=int, choices=range(3, 7))
    p.add_argument('output', type=Path)
    p.add_argument('--smoke', action='store_true'); p.add_argument('--upload', action='store_true')
    a = p.parse_args(); protocol = read(PROTOCOL); case = case_for(protocol, a.players)
    assert protocol['candidate_search'] == {'samples': 48, 'geography': True, 'scope': 'all',
        'include_model_proposal': True, 'search_max_steps': 2400, 'actual_game_max_steps': 1600}
    if a.smoke: assert a.key == protocol['smoke']['model']
    pin = protocol['models'][a.key]; out = a.output.resolve(); out.mkdir(parents=True, exist_ok=False)
    deals = 1 if a.smoke else case['deals']
    seed = protocol['smoke']['seed_template'].format(case=case['id']) if a.smoke else case['seed']
    status = {'key': a.key, 'players': a.players, 'smoke': a.smoke, 'status': 'running',
        'protocol_sha256': digest(PROTOCOL), 'source_revision': os.environ.get('SOURCE_REVISION'),
        'source_sha256': os.environ.get('SOURCE_SHA256'), 'trained': False, 'qualification_eligible': False}
    try:
        model = hf_hub_download(protocol['repo'], pin['prefix']+'/inference64.onnx', revision=pin['revision'])
        assert digest(model) == pin['files']['inference64.onnx']; write(out/'checkpoint.json', pin)
        command = [sys.executable, str(ROOT/'ai/strong/evaluate.py'), model, '--players', str(a.players),
            '--games', str(deals*4*a.players), '--workers', '24', '--seed', seed,
            '--search-samples', '48', '--geographic-search', '--search-scope', 'all',
            '--opponent', 'search_geo', '--output', str(out/'search.json')]
        with (out/'search.log').open('w') as log:
            subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
        summary = verify(read(out/'search.json'), protocol, a.key, a.players, a.smoke)
        write(out/'summary.json', summary)
        status.update(status='complete', games=deals*4*a.players, game_truncations=0, search_truncations=0)
    except BaseException as error:
        status.update(status='failed', error=type(error).__name__+': '+str(error)); raise
    finally:
        status['artifacts'] = {p.name: digest(p) for p in out.iterdir() if p.is_file()}
        write(out/'search-transfer-check.json', status)
        if a.upload:
            HfApi().upload_folder(repo_id=protocol['repo'], folder_path=out,
                path_in_repo='runs/multiplayer-search-transfer-'+('smoke-' if a.smoke else '')+f'v1-{a.key}-{a.players}p')
        print(status, flush=True)


if __name__ == '__main__': main()
