"""Audit and archive both original root-calibration endpoints before full collection."""
import argparse
import importlib.util
import json
from pathlib import Path
import shutil

from strategic_collection import ROOT, read, write, digest
from policy_iteration_evidence_archive import upload_evidence
from surrogate_continuation_root_verification_v1 import verify_artifacts

STRONG = ROOT/'ai/strong'
spec = importlib.util.spec_from_file_location('root_endpoint', STRONG/'collect-surrogate-continuation-roots-runtime-v1.py')
endpoint = importlib.util.module_from_spec(spec); spec.loader.exec_module(endpoint)
OUT = ROOT/'ai/runs/surrogate-continuation-roots-calibration-evidence-v1'
DESCRIPTOR = STRONG/'surrogate-continuation-roots-calibration-evidence-v1.json'


def audit():
    paths = {n: endpoint.COLLECTED/f'surrogate-continuation-runtime-v1-{n}p-0-1/verified.json' for n in (2, 6)}
    assert all(path.exists() for path in paths.values()), 'Both original endpoints must verify before archive or admission'
    source, protocol, _ = endpoint.launcher.prerequisites(); cells = {}; jobs = set()
    for n, path in paths.items():
        verified = read(path)
        assert verified['verified'] is True and verified['authoritative_status'] == 'COMPLETED'
        assert verified['source'] == source and verified['protocol_sha256'] == digest(endpoint.launcher.PROTOCOL)
        assert verified['plan_sha256'] == digest(endpoint.launcher.PLAN)
        assert all(digest(ROOT/name) == sha for name, sha in verified['collector_code_hashes'].items())
        guard = endpoint.launcher.GUARDS/(verified['case']+'.json')
        assert verified['guard_sha256'] == digest(guard) and read(guard)['job_id'] == verified['job_id']
        assert verified['job_id'] not in jobs; jobs.add(verified['job_id'])
        assert verified['evidence']['remote_archive_verified'] is True
        assert all(verified[key] is False for key in ('gradients', 'qualification_eligible', 'reserved_final_seeds_used'))
        review = verify_artifacts(path.parent/'artifacts', verified['evidence'], source, protocol,
                                  endpoint.RUNTIME, endpoint.MODEL, n, 0, 1, 'runtime')
        assert {key: review[key] for key in verified['review']} == verified['review']
        assert review['games'] == review['twin_games'] == 4*n
        cells[str(n)] = {'job_id': verified['job_id'], 'case': verified['case'], 'review': review,
                        'evidence': verified['evidence'], 'verified_sha256': digest(path)}
    files = [Path(__file__), STRONG/'surrogate_continuation_root_verification_v1.py',
             STRONG/'collect-surrogate-continuation-roots-runtime-v1.py', STRONG/'surrogate_continuation_roots_v1.py']
    return {'complete': True, 'jobs': 2, 'games': 32, 'paired_executions': 64, 'twin_games': 32,
            'selected_roots': sum(c['review']['selected_roots'] for c in cells.values()),
            'eligible_decisions': sum(c['review']['eligible_decisions'] for c in cells.values()),
            'caps': 0, 'cells': cells, 'source': source, 'admission': read(endpoint.launcher.PLAN),
            'protocol_sha256': digest(endpoint.launcher.PROTOCOL), 'admission_sha256': digest(endpoint.launcher.PLAN),
            'code_hashes': {str(path.relative_to(ROOT)): digest(path) for path in files},
            'training_eligible': False, 'collection_admitted': False, 'gradients': False,
            'qualification_eligible': False, 'reserved_final_seeds_used': False,
            'scope': 'Complete paired HF root-capture calibration with every selected public root and fixed action pair independently rechecked. Excluded from fresh fidelity roots, training and playing-strength qualification.'}


def main(archive=False):
    review = audit()
    if not archive: print(json.dumps(review, indent=2)); return
    assert not any(path.exists() for path in (OUT, OUT.with_suffix('.tgz'), DESCRIPTOR)), 'Reconcile earlier archive outcome before retry'
    files = [ROOT/name for name in review['code_hashes']]
    files += [ROOT/name for name in review['source']['new_files']]
    files += [endpoint.launcher.SOURCE, endpoint.launcher.PLAN, endpoint.launcher.LAYOUT,
              STRONG/'launch-surrogate-continuation-roots-runtime-v1.py', STRONG/'test_surrogate_continuation_roots_jobs_v1.py',
              STRONG/'test_surrogate_continuation_root_collection_v1.py', STRONG/'policy_iteration_evidence_archive.py',
              STRONG/'population_policy_verification.py', STRONG/'strategic_collection.py']
    files += list(endpoint.launcher.GUARDS.glob('*.json'))
    files += [path for path in endpoint.COLLECTED.rglob('*') if path.is_file()]
    files += [path for path in (ROOT/'ai/runs/surrogate-continuation-roots-preflight-v1').rglob('*') if path.is_file()]
    files += [ROOT/'ai/runs'/name for name in ('surrogate-continuation-roots-checkpoint-v1.json',
              'surrogate-continuation-roots-tests-v1.log', 'surrogate-continuation-roots-tests-initial-v1.log',
              'surrogate-continuation-roots-job-tests-v1.log', 'surrogate-continuation-root-collection-tests-v1.log',
              'surrogate-continuation-root-collection-tests-initial-v1.log')]
    OUT.mkdir()
    for path in sorted(set(files)):
        assert path.is_file() and not path.is_symlink()
        destination = OUT/path.relative_to(ROOT); destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination); assert digest(path) == digest(destination)
    write(OUT/'review.json', review)
    write(OUT/'manifest.json', {str(path.relative_to(OUT)): digest(path) for path in sorted(OUT.rglob('*')) if path.is_file()})
    write(DESCRIPTOR, {**review, **upload_evidence(OUT)})
    print({key: read(DESCRIPTOR)[key] for key in ('revision', 'archive_sha256', 'archived_files', 'remote_archive_verified')})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__); parser.add_argument('--archive', action='store_true')
    main(parser.parse_args().archive)
