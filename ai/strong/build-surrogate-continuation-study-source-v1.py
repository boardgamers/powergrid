"""Bundle actual frozen study inputs and selected inference models for HF Jobs."""
import argparse
import ast
import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

from huggingface_hub import HfApi, hf_hub_download
from strategic_collection import ROOT, read, write, digest
from surrogate_continuation_study_v1 import code_hashes, PROTOCOL
from surrogate_continuation_job_v1 import INPUTS, MEMBERS, MANIFEST, validate_inputs
from surrogate_continuation_runtime_v1 import INPUTS as RUNTIME_INPUTS, validate_inputs as validate_runtime

STRONG = ROOT/'ai/strong'
FROZEN = ROOT/'ai/runs/surrogate-continuation-study-inputs-v1'
PREP = ROOT/'ai/runs/surrogate-continuation-study-source-prepared-v1'
ARCHIVE = ROOT/'ai/runs/strong-source-surrogate-continuation-study-v1.tgz'
SOURCE = STRONG/'surrogate-continuation-study-source-v1.json'
PREFLIGHT = ROOT/'ai/runs/surrogate-continuation-study-package-preflight-v1.json'
JOB_PROOF = ROOT/'ai/runs/surrogate-continuation-job-preflight-proof-v1.json'
COST = STRONG/'surrogate-continuation-cost-complete-evidence-v1.json'
ROOTS = STRONG/'surrogate-continuation-roots-complete-evidence-v1.json'
MODEL = ROOT/'ai/runs/policy-iteration-trained-8840u-prepared-v2/local-package-frozen-1/policy.onnx'


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, STRONG/file)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module


def dependencies():
    names = ('surrogate_continuation_job_v1.py', 'surrogate_continuation_analysis_v1.py',
             'surrogate-continuation-analysis-design-v1.json', 'surrogate_continuation_runtime_v1.py',
             'surrogate-continuation-roots-job-v1.py', 'surrogate_continuation_selected_cost_v1.py',
             'build-surrogate-continuation-study-source-v1.py')
    return {**code_hashes(), **{str((STRONG/name).relative_to(ROOT)): digest(STRONG/name) for name in names}}


def prerequisites():
    assert (FROZEN/'frozen.json').exists(), 'Freeze actual audited training selection and complete fresh roots before source preparation'
    selection = load('study_source_selection', 'select-opponent-surrogate-v1.py')
    root_manager = load('study_source_root_manager', 'manage-surrogate-continuation-roots-v1.py')
    frozen_selection, selection_report, selected_policy = selection.verify_frozen()
    root_index = root_manager.index()
    frozen, manifest, roots, policy = validate_inputs(FROZEN)
    assert policy == selected_policy and frozen_selection['learned_surrogate_selected']
    assert frozen['selection_freeze_sha256'] == digest(selection.OUT/'frozen.json')
    assert frozen['surrogate_policy_sha256'] == digest(selection.OUT/'policy.json')
    assert frozen['training_result_sha256'] == selection_report['training_result_sha256'] == digest(selection.TRAINING_RESULT)
    assert frozen['root_index_sha256'] == digest(root_manager.INDEX)
    assert frozen['root_manifest_sha256'] == root_index['root_manifest_sha256']
    assert frozen['preparer_sha256'] == digest(STRONG/'prepare-surrogate-continuation-study-v1.py')
    root_evidence, cost, job, proof = map(read, (ROOTS, COST, JOB_PROOF, PREFLIGHT))
    assert root_evidence['complete'] and root_evidence['remote_archive_verified'] and root_evidence['games'] == 160
    assert root_evidence['root_manifest_sha256'] == frozen['root_manifest_sha256']
    assert cost['complete'] and cost['remote_archive_verified'] and cost['jobs'] == 24 and cost['continuations'] == 768 and cost['caps'] == 0
    assert job['complete'] and job['tests'] == 7 and job['engine_continuations'] == 48 and job['caps'] == 0
    assert job['code_hashes'] == code_hashes() and all(digest(ROOT/name) == sha for name, sha in job['additional_code_hashes'].items())
    assert proof['complete'] and proof['source_code_hashes'] == dependencies()
    assert proof['selected_cost_engine_continuations'] == 16 and proof['caps'] == 0 and proof['surrogate_untrained_fixture'] is True
    runtime_path = ROOT/'ai/runs/surrogate-continuation-cost-source-prepared-v1/layout'/RUNTIME_INPUTS.relative_to(ROOT)
    assert digest(runtime_path) == cost['source']['inputs_sha256']; validate_runtime(read(runtime_path))
    return {'frozen': frozen, 'roots': roots, 'policy': policy, 'root_evidence': root_evidence,
            'cost': cost, 'runtime_path': runtime_path, 'artifacts': selection.COLLECTED/'artifacts'}


def prepare():
    data = prerequisites()
    assert not any(p.exists() for p in (PREP, ARCHIVE, SOURCE)), 'Inspect the original preparation/upload before retrying'
    base = data['root_evidence']['source']['base']; original = ROOT/'ai/runs'/base['archive']
    assert digest(original) == base['sha256'] and base['files'] == 1463
    layout = PREP/'layout'; layout.mkdir(parents=True)
    with tarfile.open(original) as bundle:
        members = bundle.getmembers(); assert len(members) == len({m.name for m in members}) == 1463
        assert all(m.isfile() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts for m in members)
        bundle.extractall(layout, filter='data')
    before = {str(p.relative_to(layout)): digest(p) for p in layout.rglob('*') if p.is_file()}
    assert before == read(ROOT/'ai/runs/reference-opponent-diagnostic-v2/protocol.json')['runtime_hashes']
    added = {}; origins = {}
    def copy(source, name):
        assert source.is_file() and not source.is_symlink()
        if name in before:
            assert digest(source) == before[name]; return
        assert name not in added
        destination = layout/name; destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination); added[name] = digest(destination)
        assert added[name] == digest(source); origins[name] = str(source.relative_to(ROOT))
    for name in sorted(dependencies()): copy(ROOT/name, name)
    for name in ('roots.json', 'policy.json', 'frozen.json'): copy(FROZEN/name, str((INPUTS/name).relative_to(ROOT)))
    copy(data['runtime_path'], str(RUNTIME_INPUTS.relative_to(ROOT)))
    for member in data['policy']['members']:
        path = data['artifacts']/member['path']; assert digest(path) == member['sha256']
        copy(path, str((MEMBERS/member['path']).relative_to(ROOT)))
    manifest = {**before, **added}; manifest_path = layout/MANIFEST.name; write(manifest_path, manifest)
    assert all(digest(layout/name) == sha for name, sha in manifest.items())
    with tarfile.open(ARCHIVE, 'w:gz') as bundle:
        for name in sorted([*manifest, MANIFEST.name]): bundle.add(layout/name, arcname=name, recursive=False)
    frozen = data['frozen']
    descriptor = {'repo': base['repo'], 'archive': ARCHIVE.name, 'sha256': digest(ARCHIVE), 'bytes': ARCHIVE.stat().st_size,
        'manifest_sha256': digest(manifest_path), 'manifest_files': len(manifest), 'unchanged_base_files': 1463,
        'base': base, 'new_files': added, 'origins': origins, 'source_code_hashes': dependencies(),
        'study_inputs_sha256': digest(FROZEN/'frozen.json'), 'root_manifest_sha256': frozen['root_manifest_sha256'],
        'surrogate_policy_sha256': frozen['surrogate_policy_sha256'], 'selected_members': data['policy']['members'],
        'selection_freeze_sha256': frozen['selection_freeze_sha256'], 'training_result_sha256': frozen['training_result_sha256'],
        'runtime_inputs_sha256': digest(data['runtime_path']), 'protocol_sha256': digest(PROTOCOL),
        'root_evidence_sha256': digest(ROOTS), 'cost_evidence_sha256': digest(COST), 'preflight_sha256': digest(PREFLIGHT),
        'roots': len(data['roots']), 'study_continuations': frozen['continuations'], 'runtime_roots': 24,
        'selected_cost_continuations': 384, 'full_study_admitted': False, 'gradients': False,
        'qualification_eligible': False, 'reserved_final_seeds_used': False}
    write(PREP/'prepared.json', descriptor)
    print({k: descriptor[k] for k in ('archive', 'manifest_files', 'roots', 'study_continuations', 'selected_cost_continuations')})


def check_prepared():
    data = prerequisites(); p = read(PREP/'prepared.json')
    assert p['source_code_hashes'] == dependencies() and p['preflight_sha256'] == digest(PREFLIGHT)
    assert p['study_inputs_sha256'] == digest(FROZEN/'frozen.json') and p['surrogate_policy_sha256'] == data['frozen']['surrogate_policy_sha256']
    assert p['training_result_sha256'] == data['frozen']['training_result_sha256']
    assert p['selected_members'] == data['policy']['members'] and digest(ARCHIVE) == p['sha256']
    assert p['root_evidence_sha256'] == digest(ROOTS) and p['cost_evidence_sha256'] == digest(COST)
    assert digest(PREP/'layout'/MANIFEST.name) == p['manifest_sha256']
    for name, sha in read(PREP/'layout'/MANIFEST.name).items(): assert digest(PREP/'layout'/name) == sha
    for name, sha in p['new_files'].items(): assert digest(ROOT/p['origins'][name]) == sha
    return p


def check():
    p = check_prepared(); assert not (PREP/'layout-check.json').exists(), 'Preserve the original layout check'
    reports = {}
    for key, script in (('fresh', 'surrogate_continuation_job_v1.py'), ('runtime', 'surrogate_continuation_selected_cost_v1.py')):
        result = subprocess.run([sys.executable, '-B', 'ai/strong/'+script, '--check-layout', '--model', str(MODEL)],
                                cwd=PREP/'layout', check=True, capture_output=True, text=True)
        (PREP/(key+'-layout.log')).write_text(result.stdout+'\n'+result.stderr)
        report = ast.literal_eval(result.stdout.strip())
        assert report['complete'] and report['new_continuations'] == 0 and report['surrogate_policy_sha256'] == p['surrogate_policy_sha256']
        assert report['package_import_root'] == str((PREP/'layout').resolve()); reports[key] = report
    assert reports['fresh']['public_roots_checked'] == p['roots'] and reports['runtime']['runtime_roots_checked'] == 24
    assert check_prepared() == p
    write(PREP/'layout-check.json', {'complete': True, 'source_sha256': p['sha256'],
          'source_manifest_sha256': p['manifest_sha256'], 'reports': reports, 'new_continuations': 0})
    print({'complete': True, 'fresh_roots_checked': p['roots'], 'runtime_roots_checked': 24, 'package_imports_correct': True})


def upload():
    p = check_prepared(); layout = read(PREP/'layout-check.json')
    assert layout['complete'] and layout['source_sha256'] == p['sha256'] and layout['source_manifest_sha256'] == p['manifest_sha256']
    assert layout['reports']['fresh']['public_roots_checked'] == p['roots'] and layout['reports']['runtime']['runtime_roots_checked'] == 24
    assert not SOURCE.exists()
    with (PREP/'upload-intent.json').open('x') as stream:
        stream.write('{"purpose":"One source upload; reconcile an unknown outcome before retrying."}\n')
    commit = HfApi().upload_file(repo_id=p['repo'], repo_type='dataset', path_or_fileobj=ARCHIVE, path_in_repo=ARCHIVE.name)
    write(PREP/'upload-receipt.json', {'revision': commit.oid, 'sha256': p['sha256']})
    assert digest(hf_hub_download(p['repo'], ARCHIVE.name, repo_type='dataset', revision=commit.oid)) == p['sha256']
    write(SOURCE, {**p, 'revision': commit.oid, 'remote_archive_verified': True, 'layout_sha256': digest(PREP/'layout-check.json')})
    print({'revision': commit.oid, 'sha256': p['sha256'], 'remote_archive_verified': True})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__); parser.add_argument('operation', choices=['prepare', 'check', 'upload'])
    globals()[parser.parse_args().operation]()
