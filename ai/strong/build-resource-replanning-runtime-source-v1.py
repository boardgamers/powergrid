"""Package the preregistered endpoint pilot without modifying the frozen engine."""
import argparse
from datetime import datetime, timezone
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

from huggingface_hub import HfApi, hf_hub_download
from strategic_collection import ROOT, read, write, digest
from resource_development_v1 import PROTOCOL, CURRENT_PLAN, verify_pins

STRONG = ROOT / 'ai/strong'
PREP = ROOT / 'ai/runs/resource-replanning-runtime-source-prepared-v1'
LAYOUT = PREP / 'layout'
PLAN = STRONG / 'resource-replanning-runtime-plan-v1.json'
SOURCE = STRONG / 'resource-replanning-runtime-source-v1.json'
ARCHIVE = ROOT / 'ai/runs/strong-source-resource-replanning-runtime-v1.tgz'
REPO = 'coyotte508/powergrid-ai-training-v1'
MODEL = ROOT / 'ai/runs/policy-iteration-trained-8840u-prepared-v2/local-package-frozen-1/policy.onnx'


def prerequisite():
    protocol = read(PROTOCOL)
    verify_pins(protocol)
    comparison = STRONG / 'population-hybrid-development-comparison-v1.json'
    evidence = read(STRONG / 'population-hybrid-development-complete-evidence-v1.json')
    assert evidence['comparison_sha256'] == digest(comparison)
    assert evidence['remote_archive_verified'] and evidence['complete_development_comparison']
    assert evidence['games'] == 8400 and evidence['batches'] == 135
    assert read(comparison)['complete'] and read(comparison)['source'] == protocol['base_source']
    preflight = read(STRONG / 'resource-development-preflight-evidence-v1.json')
    assert preflight['remote_archive_verified'] and preflight['tests'] == 11
    assert preflight['protocol_sha256'] == digest(PROTOCOL)
    assert digest(MODEL) == protocol['model_pin']['files']['inference64.onnx']
    return protocol, evidence, preflight


def prepare():
    protocol, comparison, preflight = prerequisite()
    assert not any(path.exists() for path in (PREP, PLAN, ARCHIVE, SOURCE)), 'Inspect any existing preparation before proceeding'
    plan = {
        'created_at': datetime.now(timezone.utc).isoformat(),
        'purpose': 'Full paired endpoint runtime and execution validation. Exclude all pilot outcomes from strength.',
        'protocol_sha256': digest(PROTOCOL),
        'completed_comparison_sha256': comparison['comparison_sha256'],
        'completed_comparison_evidence_revision': comparison['revision'],
        'preflight_evidence_revision': preflight['revision'],
        'cells': [{'players': n, 'arm': arm, 'games': 4 * n,
                   'replay_episodes': list(range(4 * (n - 1), 4 * n))}
                  for n in (2, 6) for arm in ('filter', 'resource-filter')],
        'games': 64, 'samples': 8, 'workers': 8, 'search_workers': 1,
        'game_max_steps': 1600, 'rollout_max_steps': 2400,
        'opponent': 'search_geo', 'deals_per_cell': 1, 'start': 0,
        'seed_template': protocol['smoke_seed_template'],
        'cell_order': '2p filter, 2p resource-filter, 6p filter, 6p resource-filter; one cell at a time.',
        'replay_selection': 'All four rule combinations at the last seat of each endpoint/arm, fixed before running: 16 games.',
        'measurement': 'Process-tree RSS every 100 ms plus waited process CPU and complete-cell wall time. Local HX370 engineering measurements, not target AMD8840U latency or HF hardware performance.',
        'admission': 'No HF strength admission is made by this plan. Any error/cap or failed complete replay stops for review; no automatic retries. Decide hardware/timeout from the complete measured pilot, keeping both horizons and whole deals.',
        'runtime_code': {name: digest(STRONG / name) for name in
                         ('resource-replanning-runtime-pilot-v1.py', 'build-resource-replanning-runtime-source-v1.py')},
        'automatic_retries': False, 'new_strength_games': 0, 'new_hf_jobs': 0,
        'gradients': False, 'qualification_eligible': False, 'reserved_final_seeds_used': False,
    }
    write(PLAN, plan)
    PREP.mkdir()
    LAYOUT.mkdir()
    base = protocol['base_source']
    archive = ROOT / 'ai/runs' / base['archive']
    assert digest(archive) == base['sha256']
    with tarfile.open(archive) as bundle:
        members = bundle.getmembers()
        assert len(members) == 1463 and all(member.isfile() for member in members)
        assert all(not Path(member.name).is_absolute() and '..' not in Path(member.name).parts for member in members)
        bundle.extractall(LAYOUT, filter='data')
    before = {str(file.relative_to(LAYOUT)): digest(file) for file in LAYOUT.rglob('*') if file.is_file()}
    assert len(before) == 1463
    names = set(protocol['source_overlays']) | set(protocol['evidence_hashes'])
    # Keep all 1,463 frozen files intact. Current reporting-tool hashes are
    # checked on the host, but reporting tools are not runtime overlays.
    names |= {'ai/strong/' + name for name in (
        'resource_development_v1.py', 'resource-replanning-development-protocol-v1.json',
        'resource-replanning-runtime-plan-v1.json', 'resource-replanning-runtime-pilot-v1.py',
        'build-resource-replanning-runtime-source-v1.py', 'resource-development-preflight-evidence-v1.json',
        'population-hybrid-development-plan-v1.json', 'population-hybrid-development-comparison-v1.json',
        'population-hybrid-development-complete-evidence-v1.json')}
    added = {}
    for name in sorted(names):
        source, target = ROOT / name, LAYOUT / name
        if name in before:
            assert digest(source) == before[name], 'Frozen dependency changed: ' + name
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            added[name] = digest(source)
            assert digest(target) == added[name]
    assert all(digest(LAYOUT / name) == sha for name, sha in before.items())
    manifest = {**before, **added}
    write(LAYOUT / 'resource-runtime-manifest.json', manifest)
    with tarfile.open(ARCHIVE, 'w:gz') as bundle:
        for name in sorted([*manifest, 'resource-runtime-manifest.json']):
            bundle.add(LAYOUT / name, arcname=name, recursive=False)
    source = {
        'repo': REPO, 'revision': 'layout-preflight', 'archive': ARCHIVE.name,
        'sha256': digest(ARCHIVE), 'bytes': ARCHIVE.stat().st_size,
        'manifest_sha256': digest(LAYOUT / 'resource-runtime-manifest.json'),
        'protocol_sha256': digest(PROTOCOL), 'runtime_plan_sha256': digest(PLAN),
        'unchanged_base_files': len(before), 'new_files': added, 'base': base,
        'remote_archive_verified': False, 'gradients': False,
        'qualification_eligible': False, 'reserved_final_seeds_used': False,
    }
    temporary = PREP / 'layout-source.json'
    write(temporary, source)
    command = [sys.executable, str(LAYOUT / 'ai/strong/resource-replanning-runtime-pilot-v1.py'),
               '--source', str(temporary), '--model', str(MODEL), '--check-layout']
    assert not (LAYOUT / 'ai/runs').exists()
    with (PREP / 'layout-check.log').open('x') as log:
        subprocess.run(command, cwd=LAYOUT, stdout=log, stderr=subprocess.STDOUT, check=True)
    check = read(PREP / 'layout-check.log')
    assert check['layout_verified'] and check['games'] == check['jobs'] == 0
    assert len(check['commands']) == 4 and not (LAYOUT / 'ai/runs').exists()
    for cell, command in zip(plan['cells'], check['commands']):
        for flag, value in (('--players', str(cell['players'])), ('--arm', cell['arm']), ('--samples', '8'),
                            ('--workers', '8'), ('--search-workers', '1'), ('--start', '0'), ('--deals', '1')):
            assert command[command.index(flag) + 1] == value
    assert all(digest(LAYOUT / name) == sha for name, sha in manifest.items())
    source['layout_check_sha256'] = digest(PREP / 'layout-check.log')
    write(PREP / 'prepared.json', source)
    print({'prepared': True, 'unchanged_base_files': len(before), 'new_files': len(added),
           'sha256': source['sha256'], 'new_games': 0, 'new_jobs': 0}, flush=True)


def upload():
    prerequisite()
    prepared = read(PREP / 'prepared.json')
    assert not SOURCE.exists() and prepared['revision'] == 'layout-preflight'
    assert digest(ARCHIVE) == prepared['sha256']
    assert digest(PROTOCOL) == prepared['protocol_sha256'] and digest(PLAN) == prepared['runtime_plan_sha256']
    assert all(digest(ROOT / name) == digest(LAYOUT / name) == sha for name, sha in prepared['new_files'].items())
    assert digest(PREP / 'layout-check.log') == prepared['layout_check_sha256']
    with (PREP / 'upload-intent.json').open('x') as stream:
        stream.write('{"purpose":"one source upload; reconcile uncertain outcomes before any retry"}\n')
    commit = HfApi().upload_file(repo_id=REPO, repo_type='dataset', path_or_fileobj=ARCHIVE, path_in_repo=ARCHIVE.name)
    write(PREP / 'upload-receipt.json', {'repo': REPO, 'revision': commit.oid, 'archive': ARCHIVE.name, 'sha256': prepared['sha256']})
    assert digest(hf_hub_download(REPO, ARCHIVE.name, repo_type='dataset', revision=commit.oid)) == prepared['sha256']
    source = {**prepared, 'revision': commit.oid, 'remote_archive_verified': True,
              'preparation_sha256': digest(PREP / 'prepared.json')}
    write(SOURCE, source)
    print({key: source[key] for key in ('archive', 'revision', 'sha256', 'remote_archive_verified')}, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('stage', choices=('prepare', 'upload'))
    globals()[parser.parse_args().stage]()
