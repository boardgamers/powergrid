"""Convert verified trained benchmark evidence for the unchanged final verifier.

No candidate selection, jobs, training, final seeds or publication. All four
models are retained. Full development comparison and selection remain separate.
"""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import tarfile

from huggingface_hub import hf_hub_download
from strategic_collection import ROOT, read, write, digest

STRONG = ROOT/'ai/strong'
OUTPUT = ROOT/'ai/runs/policy-iteration-final-evidence-v2'
SPEC = importlib.util.spec_from_file_location('trained_benchmark', STRONG/'benchmark-policy-iteration-trained-8840u.py')
benchmark = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(benchmark)


def convert(pin, native, target, machine, package, expected_counts):
    """Reject incomplete or cross-wired proofs before mapping report fields."""
    assert pin['training_verified'] is True and not pin.get('synthetic_untrained', False)
    assert pin['qualification_eligible'] is False and pin['feature_revision'] == '4.3-strategic-correction'
    sha = pin['files']['inference64.onnx']
    assert native['model_sha256'] == sha == package['model_sha256']
    assert native['checkpoint_sha256'] == pin['files']['inference64.pt']
    assert native['complete'] and native['all_native_onnx_actions_equal'] and native['all_moves_legal']
    assert native['parent_values_preserved'] and native['cached_parent_proposals_equal']
    assert native['positions'] == pin['strict_parity_positions'] == 2553
    assert native['cached_positions_checked'] == pin['cached_positions_checked'] == 17280
    assert native['by_player_count'] == expected_counts
    assert 0 <= native['max_logit_error'] < 1e-8 and 0 <= native['max_value_error'] < 1e-8
    assert target['model_pin'] == pin and target['all_frozen_runtime_moves_identical']
    assert 0 <= target['maximum_value_difference'] < 1e-6
    assert '8840U' in machine['processor']
    summary = target['summary']
    assert summary['positions'] == 2553 and summary['all_moves_legal']
    assert summary['search_decisions'] == summary['search_evaluations'] == summary['search_truncations'] == 0
    assert {n: group['positions'] for n, group in summary['groups']['players'].items()} == expected_counts
    assert package['all_hashes_match'] and package['all_moves_legal'] and package['files_verified'] > 0
    assert package['positions_verified'] == 80 and package['player_counts'] == [2, 3, 4, 5, 6]
    common = {'model_sha256': sha, 'model_revision': pin['revision'], 'model_pin': pin,
              'candidate_selected': False, 'qualification_eligible': False}
    # Inactive-value zeros are asserted for every batch by the admitted
    # policy_iteration_check.check; its immutable code hash is recorded below.
    parity = {**native, **common, 'all_actions_match': native['all_native_onnx_actions_equal'],
              'inactive_values_zero': True,
              'inactive_values_evidence': 'Complete admitted policy_iteration_check.check assertion on every serving/cache batch'}
    cpu = {**common, 'positions': summary['positions'], 'all_moves_legal': summary['all_moves_legal'],
           'processor_model': machine['processor'], 'machine': machine,
           'search_samples': 0, 'geographic_search': False, 'search_scope': 'all',
           'search_truncated_rollouts': 0, 'by_player_count': summary['groups']['players'],
           'cold_start_ms': summary['cold_start_ms'], 'warm': summary['warm'],
           'groups': summary['groups'], 'maximum_value_difference': target['maximum_value_difference'],
           'all_frozen_runtime_moves_identical': True}
    return {'parity': parity, 'cpu': cpu, 'package': {**package, **common,
             'package_sha256': target['package_sha256']}}


def verify_archive(proof, files):
    """Bind local input receipts to the previously archived immutable evidence."""
    assert proof['remote_archive_verified'] and proof['format'] == 'tar.gz'
    archive = Path(hf_hub_download(proof['repo'], proof['archive_path'], revision=proof['revision']))
    assert digest(archive) == proof['archive_sha256']
    with tarfile.open(archive) as bundle:
        manifest = bundle.extractfile('manifest.json').read()
        assert hashlib.sha256(manifest).hexdigest() == proof['manifest_sha256']
        expected = json.loads(manifest)
        for name, path in files.items():
            assert digest(path) == expected[name]
            assert hashlib.sha256(bundle.extractfile(name).read()).hexdigest() == expected[name]


def prepare():
    # This admission checks the actual training, pinned raw files, hashed
    # verifier and benchmark dependencies. Nothing is written before it passes.
    manifest = benchmark.prepared_manifest()
    report_path = benchmark.OUTPUT/'verified.json'
    report = read(report_path)
    assert report['verified'] and report['training_verified'] and report['synthetic_untrained'] is False
    assert report['gradients'] is False and report['qualification_eligible'] is False
    assert report['candidate_selected'] is False and report['requests'] == 10212
    assert report['manifest_sha256'] == digest(benchmark.PREPARED/'manifest.json')
    assert report['source'] == manifest['source'] and report['scope'] == benchmark.SCOPE
    assert set(report['models']) == set(benchmark.MODELS)
    for name, sha in report['artifacts'].items():
        assert digest(benchmark.OUTPUT/name) == sha
    archive_pin = read(STRONG/'policy-iteration-trained-8840u-evidence-v2.json')
    assert archive_pin['training_verified'] and archive_pin['synthetic_untrained'] is False
    assert archive_pin['prepared_manifest_sha256'] == report['manifest_sha256']
    archived = {'results/verified.json': report_path, 'prepared-manifest.json': benchmark.PREPARED/'manifest.json'}
    for key in benchmark.MODELS:
        for suffix in ['-local-check.json', '-package-manifest.json', '.tgz']:
            archived[key+suffix] = benchmark.PREPARED/(key+suffix)
    verify_archive(archive_pin, archived)

    final_source = read(STRONG/'final-strategic-runtime-source-v1.json')
    archive = hf_hub_download('coyotte508/powergrid-ai-training-v1', final_source['archive'],
                              revision=final_source['revision'], repo_type='dataset')
    assert digest(archive) == final_source['sha256']
    with tarfile.open(archive) as bundle:
        # Check every packaged engine/inference dependency and fixture directly,
        # not merely the successful synthetic wrapper test or its label.
        for name, sha in manifest['runtime_hashes'].items():
            assert hashlib.sha256(bundle.extractfile(name).read()).hexdigest() == sha, name
    fixtures = [json.loads(line) for line in (benchmark.PREPARED/'fixtures.jsonl').open()]
    counts = dict(Counter(str(len(x['request']['state']['players'])) for x in fixtures))
    assert set(counts) == {'2', '3', '4', '5', '6'} and sum(counts.values()) == 2553
    records = {}
    proof_files = {str(path.relative_to(ROOT)): digest(path) for path in archived.values()}
    proof_files[str(STRONG.relative_to(ROOT)/'policy-iteration-trained-8840u-evidence-v2.json')] = digest(
        STRONG/'policy-iteration-trained-8840u-evidence-v2.json')
    for key in benchmark.MODELS:
        pin = manifest['models'][key]['pin']
        head, penalty = key.split('-')
        training_path = ROOT/'ai/runs/policy-iteration-training-verified-v2'/head/'verified.json'
        training = read(training_path)
        assert digest(training_path) == pin['training_verified_sha256']
        ensemble = training['ensembles']['ensemble-'+penalty]
        assert ensemble['files'] == pin['files']
        package_path = benchmark.PREPARED/(key+'-package-manifest.json')
        package_manifest = read(package_path)
        assert package_manifest['model_pin'] == pin and package_manifest['source'] == manifest['source']
        assert package_manifest['training_verified'] and package_manifest['synthetic_untrained'] is False
        assert package_manifest['search_samples'] == 0 and package_manifest['geographic_search'] is False
        assert package_manifest['search_scope'] == 'all'
        local_package = benchmark.PREPARED/('local-package-'+key)
        assert digest(local_package/'manifest.json') == digest(package_path)
        for name, sha in package_manifest['files'].items():
            assert digest(local_package/name) == sha
        target = report['models'][key]
        assert target['package_sha256'] == manifest['models'][key]['package_sha256']
        package = read(benchmark.PREPARED/(key+'-local-check.json'))
        assert package['files_verified'] == len(package_manifest['files'])
        records[key] = convert(pin, ensemble['parity'], target, report['machine'], package, counts)
        proof_files[str(training_path.relative_to(ROOT))] = digest(training_path)
    code_hashes = {str(path.relative_to(ROOT)): digest(path) for path in [Path(__file__),
        STRONG/'policy_iteration_check.py', STRONG/'policy_iteration_training_verification.py',
        STRONG/'benchmark-policy-iteration-trained-8840u.py', STRONG/'verify-final.py']}
    # No candidate.json is created: technical evidence alone does not select a
    # model or authorize spending the reserved test deals.
    OUTPUT.mkdir(exist_ok=False)
    for key, receipts in records.items():
        for kind, receipt in receipts.items():
            write(OUTPUT/(key+'-'+kind+'.json'), {**receipt, 'input_artifacts': proof_files,
                 'code_hashes': code_hashes, 'final_runtime_source': final_source})
    write(OUTPUT/'manifest.json', {'models': benchmark.MODELS, 'files': {
        p.name: digest(p) for p in OUTPUT.iterdir() if p.is_file()}, 'input_artifacts': proof_files,
        'code_hashes': code_hashes, 'source': final_source, 'benchmark_evidence': archive_pin,
        'candidate_selected': False, 'qualification_eligible': False, 'reserved_final_seeds_used': False,
        'scope': 'Exact trained technical receipts only. Full development review, candidate selection and unchanged final strength gate remain.'})
    print({'technical_receipts': 12, 'candidate_selected': False, 'qualification_eligible': False})


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('stage', choices=['check', 'prepare'])
    args = parser.parse_args()
    if args.stage == 'prepare':
        prepare()
    else:
        state = read(benchmark.UPSTREAM)
        print({'training_stage': state['stage'], 'trained_benchmark_verified': (benchmark.OUTPUT/'verified.json').exists(),
               'trained_benchmark_archived': (STRONG/'policy-iteration-trained-8840u-evidence-v2.json').exists(),
               'candidate_selected': False, 'qualification_eligible': False})


if __name__ == '__main__':
    main()
