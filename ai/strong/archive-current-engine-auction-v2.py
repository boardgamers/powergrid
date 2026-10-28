"""Preserve current-engine checks and exact runtime deltas without rerunning games.

Recover the original artifact from its immutable dataset archive, apply the v1
file removals/additions/replacements, then the v2 pending-membership repair.
Every resulting runtime file is bound by its full manifest. Raw checks and the
two failed diagnostic harnesses are included; original study games stay archived.
"""
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path

from huggingface_hub import HfApi
from policy_iteration_evidence_archive import upload_evidence
from public_policy_arena_v1 import semantic, validate_response
from public_policy_final_audit_v1 import artifact_identity
from public_policy_development_job_v1 import digest, read
from population_policy_verification import verify_decision as verify_filter
from opponent_auction_verification_v1 import verify_decision as verify_auction

ROOT = Path(__file__).resolve().parents[2]
NAME = 'current-engine-auction-evidence-v2'
OUT = ROOT / 'ai/runs' / NAME
RESULT = ROOT / 'ai/strong' / (NAME + '.json')
ARMS = ('filter', 'conservative_population')


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False); stream.write('\n')


def audit_receipts(run, report, reference=None):
    assert digest(run / 'decisions.jsonl') == report['receipts_sha256']
    assert digest(run / 'prepared.json') == report['prepared_sha256']
    artifact = run / 'artifact'
    identities = {a: artifact_identity(artifact, f'policies/{a}.json') for a in ARMS}
    assert identities == report['identities']
    totals = {a: Counter() for a in ARMS}; canonical = {}; seen = set()
    with (run / 'decisions.jsonl').open() as stream:
        for line in stream:
            row = json.loads(line); arm = row['arm']; q = row['request']; r = row['response']
            key = (arm, row['name']); assert key not in seen; seen.add(key)
            n, seat = len(q['state']['players']), q['player']
            validate_response(r, q, row['legal'], [(seat+i) % n for i in range(n)], identities[arm])
            config = {'players': n, 'arm': 'filter' if arm == 'filter' else 'opponent-auction-v1',
                      'samples': 8, 'model_sha256': identities[arm]['modelSha256'], 'identity': identities[arm]}
            totals[arm].update((verify_filter if arm == 'filter' else verify_auction)(
                {**r['decision'], 'arenaMoves': row['legal']}, config, seat))
            totals[arm]['requests'] += 1
            if arm == 'conservative_population':
                canonical[row['name']] = {'request': q, 'legal': row['legal'], 'decision': semantic(r['decision'])}
                if reference is not None and row['name'] in reference:
                    assert canonical[row['name']] == reference[row['name']]
    for arm, count in totals.items():
        assert all(report['counts'][arm][k] == v for k, v in count.items())
        assert count['rollout_caps'] == 0
    if reference is not None:
        assert set(reference) <= set(canonical) and len(reference) == 140
        assert len(canonical) == 160 and totals['filter']['requests'] == 20
    return {a: dict(c) for a, c in totals.items()}, canonical


def main():
    for p in (OUT, OUT.with_suffix('.tgz'), OUT.with_suffix('.intent.json'), RESULT):
        assert not p.exists(), 'Inspect prior archive intent/outcome before retrying'
    runs = {v: ROOT / f'ai/runs/current-engine-auction-v{v}' for v in (1, 2)}
    prep = {v: read(runs[v] / 'prepared.json') for v in runs}
    reports = {v: read(runs[v] / 'assessment.json') for v in runs}
    for v, report in reports.items():
        assert report['passed'] and report['new_hf_jobs'] == report['new_full_games'] == report['new_gradients'] == 0
        assert not report['qualification_eligible'] and not report['reserved_final_seeds_used']
        assert digest(runs[v] / 'artifact/manifest.json') == prep[v]['runtime_manifest_sha256']
        assert all(digest(runs[v] / 'artifact' / p) == sha for p, sha in read(runs[v] / 'artifact/manifest.json').items())
    one, canonical = audit_receipts(runs[1], reports[1])
    two, _ = audit_receipts(runs[2], reports[2], canonical)
    assert one['filter']['requests'] == 2693 and one['conservative_population']['requests'] == 140
    order = read(runs[2] / 'order-assessment.json')
    assert order['passed'] and order['canonical_positions_exact'] == 2693 and order['wrapper_cases'] == 20
    assert order['previously_failing_cases_fixed'] == 16
    assert digest(runs[1] / 'inputs.jsonl') == reports[1]['inputs_sha256'] == order['inputs_sha256']
    assert 'Ran 4 tests' in (runs[1] / 'scope-tests.log').read_text()
    assert (runs[1] / 'scope-tests.log').read_text().rstrip().endswith('OK')
    base_source = ROOT / 'ai/strong/conservative-auction-development-source-v2.json'
    base = read(base_source)
    original = ROOT / 'ai/runs/conservative-auction-development-prepared-v2/source/artifact'
    assert digest(original / 'manifest.json') == prep[1]['original_runtime_manifest_sha256']
    recovery = {'base': {k: base[k] for k in ('repo', 'revision', 'archive', 'sha256', 'source_manifest_sha256')},
        'repo_type': 'dataset', 'base_artifact_subdirectory': 'artifact',
        'base_runtime_manifest_sha256': digest(original / 'manifest.json'),
        'base_copy_only': sorted([*read(original / 'manifest.json'), 'manifest.json',
                                 *(f'policies/{a}.json' for a in ARMS)]),
        'base_copy_note': 'Do not copy unrelated source controls or the unused dual-policy descriptor.', 'steps': []}
    sources = {Path(__file__).resolve(), base_source}
    for v in runs:
        manifest = read(runs[v] / 'artifact/manifest.json')
        parent = read((original if v == 1 else runs[1] / 'artifact') / 'manifest.json')
        changed = sorted(p for p in manifest if p not in parent or manifest[p] != parent[p])
        removed = sorted(set(parent) - set(manifest))
        assert changed == sorted(prep[v]['changed_files'] + prep[v].get('added_files', []))
        assert removed == prep[v].get('removed_files', [])
        for p in changed: sources.add(runs[v] / 'artifact' / p)
        sources.add(runs[v] / 'artifact/manifest.json')
        sources.update(runs[v] / f'artifact/policies/{a}.json' for a in ARMS)
        sources.update(p for p in runs[v].rglob('*') if p.is_file() and not p.is_relative_to(runs[v] / 'artifact'))
        recovery['steps'].append({'version': v, 'replacement_prefix': str((runs[v] / 'artifact').relative_to(ROOT)),
            'remove': removed, 'replace_or_add': changed, 'descriptors': [f'policies/{a}.json' for a in ARMS],
            'runtime_manifest_sha256': prep[v]['runtime_manifest_sha256'],
            'verify': 'Every file in the complete recovered manifest must match before use; replace manifest and the two policy descriptors too.'})
    for v in (1, 2, 3):
        folder = ROOT / f'ai/runs/current-engine-auction-wrapper-diagnostic-v{v}'
        sources.update(p for p in folder.rglob('*') if p.is_file())
        sources.add(ROOT / f'ai/strong/check-current-engine-auction-wrapper-v{v}.cjs')
    sources.update(ROOT / p for p in (
        'ai/CURRENT-ENGINE-AUCTION-2026-10-28.md', 'ai/RESUME.md',
        'ai/strong/check-current-engine-auction-v1.py', 'ai/strong/check-current-engine-auction-v2.py',
        'ai/strong/check-current-auction-order-v2.cjs', 'ai/strong/current-engine-auction-inputs-v1.cjs',
        'ai/strong/prepare-current-engine-auction-v1.py', 'ai/strong/prepare-current-engine-auction-v2.py',
        'ai/strong/current_engine_scope_v1.py', 'ai/strong/test_current_engine_scope_v1.py',
        'ai/strong/current-engine-auction-fixtures-v1.json', 'ai/strong/current-engine-auction-fixtures-v2.json',
        'ai/strong/current-engine-auction-prepared-v1.json', 'ai/strong/current-engine-auction-prepared-v2.json',
        'ai/strong/current-engine-compatibility-evidence-v1.json', 'ai/strong/current-engine-policy-evidence-v1.json',
        'ai/strong/conservative-auction-comparison-evidence-v2.json', 'ai/strong/conservative-auction-cpu-results-evidence-v2.json',
        'ai/strong/policy_iteration_evidence_archive.py', 'ai/strong/strategic_collection.py',
        'ai/runs/current-engine-auction-fixtures-v1-first.log', 'ai/runs/current-engine-auction-fixtures-v2-first.log',
        'ai/runs/current-engine-auction-order-v2-first.log'))
    assert all(p.is_file() and not p.is_symlink() for p in sources)
    api = HfApi(); repo = 'coyotte508/powergrid-ai-germany-v1'
    assert api.model_info(repo).private and not api.file_exists(repo, 'archives/' + NAME + '.tgz')
    OUT.mkdir(); manifest = {}
    for p in sorted(sources):
        name = str(p.relative_to(ROOT)); target = OUT / name
        target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(p.read_bytes()); manifest[name] = digest(target)
    save(OUT / 'runtime-recovery.json', recovery); manifest['runtime-recovery.json'] = digest(OUT / 'runtime-recovery.json')
    audit = {'passed': True, 'counts': {'v1': one, 'v2': two}, 'exact_full_canonical_search_decisions': 140,
             'new_inference': 0, 'new_full_games': 0, 'new_hf_jobs': 0}
    save(OUT / 'independent-receipt-audit.json', audit)
    manifest['independent-receipt-audit.json'] = digest(OUT / 'independent-receipt-audit.json')
    save(OUT / 'manifest.json', manifest)
    intent = {'created_at': datetime.now(timezone.utc).isoformat(), 'stage': 'prepared_for_upload',
              'manifest_sha256': digest(OUT / 'manifest.json')}
    save(OUT.with_suffix('.intent.json'), intent)
    print(json.dumps({'stage': 'uploading', 'files': len(manifest)+1}), flush=True)
    archive = upload_evidence(OUT)
    save(RESULT, {'status': 'current_engine_fixed_position_and_wrapper_search_verified',
        'runtime_manifest_sha256': prep[2]['runtime_manifest_sha256'],
        'reports': {str(v): {'path': str((runs[v] / 'assessment.json').relative_to(ROOT)),
                           'sha256': digest(runs[v] / 'assessment.json')} for v in runs},
        'counts': audit['counts'], 'independent_receipt_audit_sha256': digest(OUT / 'independent-receipt-audit.json'),
        'runtime_recovery_sha256': digest(OUT / 'runtime-recovery.json'),
        'exact_full_canonical_search_decisions': 140, 'wrapper_cases': 20, 'previously_failing_cases_fixed': 16,
        'preserved_diagnostic_harness_failures': 2, 'new_hf_jobs': 0, 'new_full_games': 0, 'new_gradients': 0,
        'qualification_eligible': False, 'reserved_final_seeds_used': False, 'archive': archive})
    OUT.with_suffix('.intent.json').write_text(json.dumps({**intent, 'stage': 'uploaded_download_verified',
        'archive': archive, 'descriptor_sha256': digest(RESULT)}, indent=2) + '\n')
    print(json.dumps(archive), flush=True)


if __name__ == '__main__': main()
