"""Audit both complete HF runtime endpoints and archive their joint evidence."""
import argparse
import importlib.util
import json
from pathlib import Path
import shutil

from strategic_collection import ROOT, read, write, digest
from policy_iteration_evidence_archive import upload_evidence

STRONG = ROOT / 'ai/strong'
spec = importlib.util.spec_from_file_location('resource_endpoint_collector', STRONG / 'collect-resource-replanning-hf-runtime-v1.py')
endpoint = importlib.util.module_from_spec(spec)
spec.loader.exec_module(endpoint)
OUT = ROOT / 'ai/runs/resource-hf-calibration-evidence-v1'
DESCRIPTOR = STRONG / 'resource-hf-calibration-evidence-v1.json'


def summarize(results):
    assert set(results) == {2, 6}, 'Both complete endpoints are required'
    assert len({row['job_id'] for row in results.values()}) == 2, 'Endpoint jobs must be distinct'
    assert results[2]['source'] == results[6]['source'], 'Endpoint source differs'
    for key in ('admission_sha256', 'local_pilot_descriptor_sha256', 'code_hashes'):
        assert results[2][key] == results[6][key], key
    cells = {}
    for players, row in results.items():
        assert row['verified'] is True and row['authoritative_status'] == 'COMPLETED'
        assert row['case'] == f'resource-replanning-hf-runtime-v1-{players}p-resource-filter'
        assert row['strength_eligible'] is row['qualification_eligible'] is row['reserved_final_seeds_used'] is False
        assert row['new_strength_games'] == 0 and row['parity']['exact'] is True
        assert row['summary']['games'] == row['parity']['games'] == 4 * players
        assert row['summary']['counts']['rollout_caps'] == 0
        assert row['parity']['learner_decisions'] == row['summary']['counts']['decisions']
        assert row['parity']['resource_decisions'] == row['summary']['counts']['resource_search_decisions'] == row['resource_latency']['count']
        assert row['parity']['resource_rollouts'] == row['summary']['counts']['rollouts']
        assert row['evidence']['remote_archive_verified'] is True
        cells[str(players)] = {key: row[key] for key in ('case', 'job_id', 'summary', 'runtime', 'parity', 'resource_latency', 'evidence')}
    return {'complete': True, 'jobs': 2, 'games': 32, 'caps': 0, 'exact_local_hf_parity': True,
            'learner_decisions': sum(row['parity']['learner_decisions'] for row in results.values()),
            'resource_decisions': sum(row['parity']['resource_decisions'] for row in results.values()),
            'resource_rollouts': sum(row['parity']['resource_rollouts'] for row in results.values()),
            'source': results[2]['source'], 'admission_sha256': results[2]['admission_sha256'],
            'local_pilot_descriptor_sha256': results[2]['local_pilot_descriptor_sha256'],
            'endpoint_code_hashes': results[2]['code_hashes'], 'cells': cells,
            'new_strength_games': 0, 'gradients': False, 'development_admitted': False,
            'qualification_eligible': False, 'reserved_final_seeds_used': False,
            'scope': 'Two complete runtime-only HF endpoint deals with exact archived local/HF behavior. Measures remote cost, not playing strength or target serving latency. Separate measured development admission remains required.'}


def audit():
    # Refuse partial calibration before any network access or archival mutation.
    for players in (2, 6):
        folder = endpoint.COLLECTED / f'resource-replanning-hf-runtime-v1-{players}p-resource-filter'
        path = folder / 'verified.json'
        assert path.exists(), 'Collect both completed endpoint jobs first'
        saved = read(path)
        assert saved.get('verified') is True and saved['authoritative_status'] == 'COMPLETED'
    results = {players: endpoint.collect(players) for players in (2, 6)}
    review = summarize(results)
    admission = read(endpoint.launcher.ADMISSION)
    assert review['admission_sha256'] == digest(endpoint.launcher.ADMISSION)
    assert admission['games'] == 32 and admission['players'] == [2, 6]
    assert admission['development_admitted'] is False
    return {**review, 'admission': admission, 'collector_sha256': digest(__file__)}


def main(archive):
    review = audit()
    if not archive:
        print(json.dumps({key: value for key, value in review.items() if key not in ('source', 'cells')}, indent=2))
        return
    assert not OUT.exists() and not OUT.with_suffix('.tgz').exists() and not DESCRIPTOR.exists(), 'Inspect any previous archive attempt before retrying'
    files = [Path(__file__), Path(endpoint.__file__), Path(endpoint.launcher.__file__), endpoint.launcher.ADMISSION,
             endpoint.launcher.PILOT, endpoint.launcher.SOURCE, endpoint.launcher.PREFLIGHT, endpoint.launcher.PROTOCOL,
             STRONG / 'resource_policy_verification_v1.py', STRONG / 'population_policy_verification.py',
             STRONG / 'test_resource_hf_calibration_collection_v1.py',
             STRONG / 'policy_iteration_evidence_archive.py', STRONG / 'strategic_collection.py']
    for cell in review['cells'].values():
        files.append(endpoint.launcher.GUARDS / (cell['case'] + '.json'))
        files += [p for p in (endpoint.COLLECTED / cell['case']).rglob('*') if p.is_file()]
    OUT.mkdir()
    for file in sorted(set(files)):
        assert file.is_file() and not file.is_symlink()
        dest = OUT / file.relative_to(ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file, dest)
        assert digest(file) == digest(dest)
    write(OUT / 'review.json', review)
    write(OUT / 'manifest.json', {str(p.relative_to(OUT)): digest(p) for p in sorted(OUT.rglob('*')) if p.is_file()})
    write(DESCRIPTOR, {**review, **upload_evidence(OUT)})
    print({key: read(DESCRIPTOR)[key] for key in ('revision', 'archive_sha256', 'archived_files', 'remote_archive_verified')})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--archive', action='store_true')
    main(parser.parse_args().archive)
