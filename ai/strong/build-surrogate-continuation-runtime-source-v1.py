"""Package outcome-independent runtime roots and unchanged reference engine."""
import argparse
from pathlib import Path
import shutil
import tarfile

from huggingface_hub import HfApi, hf_hub_download
from strategic_collection import ROOT, read, write, digest
from surrogate_continuation_study_v1 import code_hashes, PROTOCOL
from surrogate_continuation_runtime_v1 import select_roots, validate_inputs, INPUTS, MODES

STRONG = ROOT/'ai/strong'
PREP = ROOT/'ai/runs/surrogate-continuation-cost-source-prepared-v1'
SOURCE = STRONG/'surrogate-continuation-cost-source-v1.json'
ARCHIVE = ROOT/'ai/runs/strong-source-surrogate-continuation-cost-v1.tgz'
CALIBRATION = STRONG/'surrogate-continuation-roots-calibration-evidence-v1.json'
PREFLIGHT = ROOT/'ai/runs/surrogate-continuation-study-preflight-proof-v1.json'


def prerequisites():
    p = read(PREFLIGHT); c = read(CALIBRATION)
    assert p['complete'] and p['tests'] == 8 and p['integration']['complete_continuations'] == 96 and p['integration']['caps'] == 0
    assert p['code_hashes'] == code_hashes()
    assert all(digest(ROOT/name) == sha for name, sha in p['additional_code_hashes'].items())
    assert digest(ROOT/p['integration']['status']) == p['integration']['status_sha256']
    assert c['complete'] and c['remote_archive_verified'] and c['games'] == 32 and c['caps'] == 0
    assert all(digest(ROOT/name) == sha for name, sha in c['code_hashes'].items())
    archive = ROOT/'ai/runs/surrogate-continuation-roots-calibration-evidence-v1.tgz'
    assert digest(archive) == c['archive_sha256']
    return p, c


def inputs():
    _, c = prerequisites(); games = {}; provenance = {}
    for n in (2, 6):
        cell = c['cells'][str(n)]; folder = ROOT/'ai/runs/surrogate-continuation-roots-runtime-collected-v1'/cell['case']
        verified = read(folder/'verified.json'); assert digest(folder/'verified.json') == cell['verified_sha256']
        assert verified['verified'] and verified['evidence'] == cell['evidence']
        artifacts = folder/'artifacts'; manifest = read(artifacts/'manifest.json')
        assert digest(artifacts/'manifest.json') == cell['evidence']['manifest_sha256']
        assert all(digest(artifacts/name) == sha for name, sha in manifest.items())
        for seat in range(n):
            for rule in range(4):
                path = artifacts/'games'/f'game-{seat*4+rule}'/'roots.json'
                games[(n, seat, rule)] = read(path)
                provenance[f'{n}/{seat}/{rule}'] = {'roots_sha256': digest(path), 'job_id': cell['job_id']}
    result = {'version': 1, 'roots': select_roots(games), 'provenance': provenance,
              'protocol_sha256': digest(PROTOCOL), 'focal_model_sha256': read(PROTOCOL)['focal_model_sha256'],
              'calibration_sha256': digest(CALIBRATION), 'modes': list(MODES), 'samples': 8,
              'max_steps': 2400, 'workers': 8, 'continuations': 768,
              'selection': 'Minimum pre-existing eligible root rank in each endpoint/rule/phase group, then episode and decision ordinal. No game outcomes, continuation outcomes or surrogate values are read for selection.',
              'scope': 'Separate runtime calibration roots; not fresh fidelity-study roots or playing-strength evidence.',
              'training_eligible': False, 'qualification_eligible': False, 'reserved_final_seeds_used': False}
    validate_inputs(result); return result


def prepare():
    proof, calibration = prerequisites(); roots = inputs()
    assert not any(p.exists() for p in (PREP, SOURCE, ARCHIVE)), 'Reconcile original preparation before retry'
    base = calibration['source']['base']; original = ROOT/'ai/runs'/base['archive']
    assert digest(original) == base['sha256']
    layout = PREP/'layout'; layout.mkdir(parents=True)
    with tarfile.open(original) as bundle:
        members = bundle.getmembers(); assert len(members) == len({m.name for m in members}) == 1463
        assert all(m.isfile() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts for m in members)
        bundle.extractall(layout, filter='data')
    before = {str(p.relative_to(layout)): digest(p) for p in layout.rglob('*') if p.is_file()}
    reference = read(ROOT/'ai/runs/reference-opponent-diagnostic-v2/protocol.json')
    assert before == reference['runtime_hashes']
    paths = [ROOT/name for name in proof['code_hashes']]
    paths += [Path(__file__), STRONG/'surrogate_continuation_runtime_v1.py', STRONG/'surrogate-continuation-roots-job-v1.py']
    added = {}
    for path in sorted(set(paths)):
        name = str(path.relative_to(ROOT))
        if name in before:
            assert digest(path) == before[name]; continue
        shutil.copy2(path, layout/name); added[name] = digest(path)
    name = str(INPUTS.relative_to(ROOT)); assert name not in before
    write(layout/name, roots); added[name] = digest(layout/name)
    manifest = {**before, **added}; path = layout/'surrogate-continuation-runtime-source-manifest.json'; write(path, manifest)
    assert all(digest(layout/name) == sha for name, sha in manifest.items())
    with tarfile.open(ARCHIVE, 'w:gz') as bundle:
        for name in sorted([*manifest, path.name]): bundle.add(layout/name, arcname=name, recursive=False)
    result = {'repo': base['repo'], 'archive': ARCHIVE.name, 'sha256': digest(ARCHIVE), 'bytes': ARCHIVE.stat().st_size,
              'manifest_sha256': digest(path), 'manifest_files': len(manifest), 'unchanged_base_files': 1463,
              'base': base, 'new_files': added, 'inputs_sha256': digest(layout/INPUTS.relative_to(ROOT)),
              'calibration_sha256': digest(CALIBRATION), 'preflight_sha256': digest(PREFLIGHT), 'protocol_sha256': digest(PROTOCOL),
              'roots': 24, 'continuations': 768, 'calibration_only': True,
              'gradients': False, 'qualification_eligible': False, 'reserved_final_seeds_used': False}
    write(PREP/'prepared.json', result)
    print({k: result[k] for k in ('archive', 'sha256', 'manifest_files', 'roots', 'continuations')})


def upload():
    prerequisites(); p = read(PREP/'prepared.json'); layout = read(PREP/'layout-check.json')
    assert layout['complete'] and layout['public_roots_checked'] == 24 and layout['source_sha256'] == p['sha256']
    assert layout['source_manifest_sha256'] == p['manifest_sha256'] and layout['inputs_sha256'] == p['inputs_sha256']
    assert not SOURCE.exists() and digest(ARCHIVE) == p['sha256']
    for name, sha in p['new_files'].items():
        assert digest(PREP/'layout'/name) == sha
        if name != str(INPUTS.relative_to(ROOT)): assert digest(ROOT/name) == sha
    with (PREP/'upload-intent.json').open('x') as stream:
        stream.write('{"purpose":"One source upload; reconcile an unknown result before retrying."}\n')
    commit = HfApi().upload_file(repo_id=p['repo'], repo_type='dataset', path_or_fileobj=ARCHIVE, path_in_repo=ARCHIVE.name)
    write(PREP/'upload-receipt.json', {'revision': commit.oid, 'sha256': p['sha256']})
    assert digest(hf_hub_download(p['repo'], ARCHIVE.name, repo_type='dataset', revision=commit.oid)) == p['sha256']
    write(SOURCE, {**p, 'layout_sha256': digest(PREP/'layout-check.json'), 'revision': commit.oid, 'remote_archive_verified': True})
    print({'revision': commit.oid, 'sha256': p['sha256'], 'remote_archive_verified': True})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__); parser.add_argument('operation', choices=['prepare', 'upload'])
    globals()[parser.parse_args().operation]()
