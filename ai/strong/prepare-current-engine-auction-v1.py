"""Derive an isolated current-engine copy of the completed auction recipe.

Preserve weights, features, search settings and all original evidence. This
operation does not infer, simulate, upload or submit a job.
"""
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil

from public_policy_development_job_v1 import digest, read

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'ai/runs/current-engine-auction-v1'
OLD = ROOT / 'ai/runs/conservative-auction-development-prepared-v2/source/artifact'
ENGINE = ROOT / 'ai/runs/current-engine-compatibility-v1'
ARMS = ('filter', 'conservative_population')
RESULT = ROOT / 'ai/strong/current-engine-auction-prepared-v1.json'


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False); stream.write('\n')


def main():
    assert not OUT.exists() and not RESULT.exists(), 'Inspect prior preparation before retry'
    comparison = ROOT / 'ai/strong/conservative-auction-comparison-evidence-v2.json'
    evidence = read(comparison)
    assert evidence['games'] == 10080 and evidence['archive']['remote_archive_verified']
    summary = ROOT / 'ai/strong/conservative-auction-development-summary-v2.json'
    assert digest(summary) == evidence['summary_sha256']
    identities = read(summary)['identities']
    manifest = read(OLD / 'manifest.json')
    assert digest(OLD / 'manifest.json') == identities['filter']['runtimeManifestSha256']
    assert all(digest(OLD / name) == sha for name, sha in manifest.items())
    engine_evidence = ROOT / 'ai/strong/current-engine-compatibility-evidence-v1.json'
    proof = read(engine_evidence); build = read(ENGINE / 'build.json'); design = read(ENGINE / 'design.json')
    assert proof['archive']['remote_archive_verified']
    assert digest(ENGINE / 'build.json') == proof['build_sha256']
    assert digest(ENGINE / 'design.json') == proof['design_sha256']
    assert design['current_engine_commit'] == '3adad0cc0d1d31352aa7a9059bd15efa79647269'
    assert all(digest(ENGINE / 'source' / name) == sha for name, sha in design['source_files'].items())
    assert all(digest(ENGINE / 'source/engine' / name) == sha for name, sha in build['compiled_files'].items())
    scope = Path(__file__).with_name('current_engine_scope_v1.py')
    OUT.mkdir(); artifact = OUT / 'artifact'; artifact.mkdir()
    # Copy only pinned runtime files and the two selected research descriptors.
    # No stale convenience descriptors or old declaration files are retained.
    for name in manifest:
        if name.startswith('engine/dist/'):
            continue
        target = artifact / name; target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(OLD / name, target)
    for name in build['compiled_files']:
        target = artifact / 'engine' / name; target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ENGINE / 'source/engine' / name, target)
    scope_target = artifact / 'ai/strong' / scope.name
    shutil.copyfile(scope, scope_target)
    entry = artifact / 'ai/strong/public_policy_runtime_v1.py'
    original = entry.read_text()
    replacements = (
        ('import time\n', 'import time\nimport current_engine_scope_v1\n'),
        ('modules = [hybrid_search, population_hybrid_policy, infer, pool, feature_contract]',
         'modules = [hybrid_search, population_hybrid_policy, infer, pool, feature_contract, current_engine_scope_v1]'),
        ('        before = encode(request)\n',
         '        current_engine_scope_v1.validate_request_scope(request)\n        before = encode(request)\n'))
    changed = original
    for before, after in replacements:
        assert changed.count(before) == 1, 'Unexpected frozen transport version'
        changed = changed.replace(before, after)
    entry.write_text(changed)
    new = {str(p.relative_to(artifact)): digest(p) for p in sorted(artifact.rglob('*')) if p.is_file()}
    save(artifact / 'manifest.json', new)
    (artifact / 'policies').mkdir()
    for arm in ARMS:
        spec = read(OLD / f'policies/{arm}.json')
        assert digest(OLD / f'policies/{arm}.json') == identities[arm]['policySha256']
        spec['runtime_manifest']['sha256'] = digest(artifact / 'manifest.json')
        save(artifact / f'policies/{arm}.json', spec)
    differences = sorted(name for name in set(manifest) & set(new) if manifest[name] != new[name])
    assert all(name.startswith('engine/dist/') or name == 'ai/strong/public_policy_runtime_v1.py'
               for name in differences)
    assert new['policy.onnx'] == manifest['policy.onnx']
    assert all(new[name] == sha for name, sha in manifest.items()
               if not name.startswith('engine/dist/') and name != 'ai/strong/public_policy_runtime_v1.py')
    result = {'created_at': datetime.now(timezone.utc).isoformat(), 'stage': 'prepared_not_admitted',
        'comparison_evidence_sha256': digest(comparison), 'comparison_summary_sha256': digest(summary),
        'current_engine_commit': design['current_engine_commit'], 'engine_evidence_sha256': digest(engine_evidence),
        'engine_build_sha256': digest(ENGINE / 'build.json'), 'engine_design_sha256': digest(ENGINE / 'design.json'),
        'original_runtime_manifest_sha256': digest(OLD / 'manifest.json'),
        'runtime_manifest_sha256': digest(artifact / 'manifest.json'),
        'original_descriptors': {arm: read(OLD / f'policies/{arm}.json') for arm in ARMS},
        'descriptors': {arm: read(artifact / f'policies/{arm}.json') for arm in ARMS},
        'policy_sha256': {arm: digest(artifact / f'policies/{arm}.json') for arm in ARMS},
        'changed_files': differences, 'added_files': sorted(set(new) - set(manifest)),
        'removed_files': sorted(set(manifest) - set(new)),
        'unchanged_files': sum(new.get(name) == sha for name, sha in manifest.items()),
        'preparer_sha256': digest(__file__), 'scope_checker_sha256': digest(scope),
        'model_sha256': new['policy.onnx'], 'current_engine_typechecked': False,
        'scope': 'Isolated current engine, same trained weights/features/shortlist/selection and exact search settings. Explicit option rejection only; no production routing.',
        'new_hf_jobs': 0, 'new_games': 0, 'new_inference': 0, 'new_gradients': 0,
        'qualification_eligible': False, 'reserved_final_seeds_used': False}
    save(OUT / 'prepared.json', result); save(RESULT, result)
    print(json.dumps({'prepared': True, 'manifest_sha256': result['runtime_manifest_sha256'],
        'changed_files': differences, 'added_files': result['added_files'],
        'removed_declarations': len(result['removed_files']), 'unchanged_files': result['unchanged_files']}), flush=True)


if __name__ == '__main__': main()
