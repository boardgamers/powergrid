"""Freeze a checked training package only after all 160 teacher shards verify."""
import argparse
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path
from huggingface_hub import HfApi, hf_hub_download
from strategic_collection import ROOT, read, write, digest

NAMES = [
    'model.py', 'model_strategic.py', 'features-v4_3.cjs', 'encoders.cjs',
    'export-inference64.py', 'package-serving.py', 'evaluate.py',
    'strategic_correction_data.py', 'strategic_correction_targets.py',
    'train-strategic-correction.py', 'check-strategic-correction-data.py',
    'test_model_strategic.py', 'test_strategic_correction_targets.py',
    'test-strategic-correction-features.cjs', 'preflight-strategic-correction.py',
    'check-strategic-correction-arena.py',
    'strategic-correction-design-v1.json', 'strategic-teacher-training-source-v1.json',
    'strategic-teacher-training-results-v1.json',
]


def require_complete(manifest):
    expected = {f'{n}p-{family}-{mode}-{start}-{start+2}'
        for n in range(2, 7) for family in ['economic', 'snapshot0']
        for mode in ['neural', 'neural_economic'] for start in range(0, 16, 2)}
    assert manifest['all_shards_verified'], 'Full verified label grid required before freezing or uploading training source'
    assert manifest['verified_shards'] == 160 and not manifest['pending']
    assert manifest['complete_mixture_roots'] == 1920 and set(manifest['cases']) == expected


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--code-only', action='store_true',
        help='Check code against the frozen engine; never upload source or admit training')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    base = read(ROOT/'ai/strong/strategic-teacher-training-source-v1.json')
    manifest_path = ROOT/'ai/strong/strategic-teacher-training-results-v1.json'
    manifest = read(manifest_path)
    if not args.code_only:
        require_complete(manifest)
    out = (args.output or ROOT/('ai/runs/strategic-correction-code-preflight-v1' if args.code_only
                               else 'ai/runs/strategic-correction-source-v1')).resolve()
    assert not out.exists(), 'Preserve previous package and checks'
    archive = hf_hub_download('coyotte508/powergrid-ai-training-v1', base['archive'],
        repo_type='dataset', revision=base['revision'])
    assert digest(archive) == base['sha256']
    out.mkdir(parents=True)
    with tarfile.open(archive) as bundle:
        bundle.extractall(out, filter='data')
    before = {str(p.relative_to(out)): digest(p) for p in out.rglob('*') if p.is_file()}
    overlays = {}
    for name in NAMES:
        relative = 'ai/strong/'+name
        shutil.copy2(ROOT/relative, out/relative)
        overlays[relative] = digest(out/relative)
    unchanged = {name: sha for name, sha in before.items() if name not in overlays}
    # The training runtime keeps the teacher engine, menu, features and parent byte-identical.
    for name in ['features-v4.cjs', 'features-v4_1.cjs', 'features-v4_2.cjs', 'model_v4.py',
                 'model_discard.py', 'bridge.cjs', 'economics.cjs', 'search.cjs',
                 'strategic_training_labels.py', 'strategic-teacher-training-protocol-v1.json']:
        assert 'ai/strong/'+name in unchanged
    logs = out/'ai/runs/source-checks'
    logs.mkdir(parents=True)
    commands = [
        ['node', '--test', 'ai/strong/test-strategic-correction-features.cjs'],
        [sys.executable, 'ai/strong/test_model_strategic.py'],
        [sys.executable, 'ai/strong/test_strategic_correction_targets.py'],
        [sys.executable, 'ai/strong/preflight-strategic-correction.py', '--output',
         'ai/runs/source-zero-correction'],
        [sys.executable, 'ai/strong/check-strategic-correction-arena.py',
         'ai/runs/source-zero-correction/derivative/inference64.onnx',
         'ai/runs/source-arena-check'],
    ]
    if not args.code_only:
        commands.append([sys.executable, 'ai/strong/check-strategic-correction-data.py',
            'ai/strong/strategic-teacher-training-results-v1.json', 'ai/runs/source-checks/data.json'])
    for index, command in enumerate(commands):
        print('Checking', command[1], flush=True)
        with (logs/f'{index}.log').open('w') as log:
            subprocess.run(command, cwd=out, stdout=log, stderr=subprocess.STDOUT, check=True)
    assert all(digest(out/name) == sha for name, sha in unchanged.items())
    assert all(digest(out/name) == sha for name, sha in overlays.items())
    report = {'passed': True, 'code_only': args.code_only, 'overlays': overlays,
        'base': {k: base[k] for k in ['archive', 'revision', 'sha256']},
        'unchanged_base_file_count': len(unchanged),
        'parent_preflight': read(out/'ai/strong/strategic-correction-preflight-v1.json'),
        'arena_preflight': read(out/'ai/runs/source-arena-check/check.json'),
        'design_sha256': overlays['ai/strong/strategic-correction-design-v1.json'],
        'manifest_sha256': overlays['ai/strong/strategic-teacher-training-results-v1.json'],
        'gradients': 0, 'qualification_eligible': False}
    if args.code_only:
        write(logs/'preflight.json', report)
        print({'code_only': True, 'passed': True, 'output': str(out), 'training_admitted': False})
        return
    report['data_preflight'] = read(logs/'data.json')
    target = ROOT/'ai/runs/strong-source-strategic-correction-20261023-v1.tgz'
    assert not target.exists()
    with tarfile.open(target, 'w:gz') as bundle:
        # Include only frozen base files and explicit overlays, never cached data or check outputs.
        for name in sorted(set(before) | set(overlays)):
            bundle.add(out/name, arcname=name, recursive=False)
    commit = HfApi().upload_file(repo_id='coyotte508/powergrid-ai-training-v1', repo_type='dataset',
        path_or_fileobj=target, path_in_repo=target.name)
    source = {'archive': target.name, 'revision': commit.oid, 'sha256': digest(target),
        'bytes': target.stat().st_size, 'base': report['base'], 'overlays': overlays,
        'unchanged_base_file_count': len(unchanged), 'design_sha256': report['design_sha256'],
        'data_manifest_sha256': report['manifest_sha256'], 'qualification_eligible': False}
    write(ROOT/'ai/strong/strategic-correction-source-v1.json', source)
    report.update(source_revision=source['revision'], source_sha256=source['sha256'])
    write(ROOT/'ai/strong/strategic-correction-source-preflight-v1.json', report)
    print({k: v for k, v in source.items() if k not in ['overlays', 'base']})


if __name__ == '__main__':
    main()
