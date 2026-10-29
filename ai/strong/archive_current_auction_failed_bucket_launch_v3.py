"""Archive admitted recoveries, exact handles, routing and interrupted collector evidence."""
from pathlib import Path
import json
import shutil

import current_auction_attempt_authentication_v4 as a
import current_auction_attempt_comparison_v4 as c

m = a.failed
OUT = a.ROOT/'ai/runs/current-auction-failed-bucket-launch-evidence-v3'
STATUS = m.STRONG/'current-auction-failed-bucket-launch-v3.json'
REPORT = m.STRONG/'current-auction-attempt-authentication-preflight-v4.json'
DESCRIPTOR = m.STRONG/'current-auction-failed-bucket-launch-evidence-v3.json'


def main():
    a.require(not OUT.exists() and not OUT.with_suffix('.tgz').exists() and not DESCRIPTOR.exists(),
              'Inspect existing archive intent/outcome')
    with m.exclusive(m.old.OUT, 'cycle'), m.exclusive(m.ongoing.OUT, 'cycle'), m.exclusive(m.OUT, 'cycle'):
        report, status = a.read(REPORT), a.read(STATUS)
        a.require(report['passed'] is True and report['code_sha256'] == a.digest(a.__file__)
                  and report['comparison_sha256'] == a.digest(c.__file__)
                  and all(a.digest(a.ROOT/p) == sha for p, sha in report['frozen_input_hashes'].items()), 'Routing proof changed')
        a.require(status['coordinator_state_sha256'] == a.digest(m.OUT/'state.json')
                  and status['old_collection_state_sha256'] == a.digest(m.originals.OUT/'collection-state.json'),
                  'Execution snapshot changed')
        api = m.HfApi(); repo = m.worker.base.retention.REPO
        a.require(api.model_info(repo).private, 'Private archive required')
        a.require(not api.file_exists(repo, 'archives/'+OUT.name+'.tgz'), 'Inspect prior remote archive')
        paths = {Path(__file__), REPORT, STATUS, a.ROOT/'ai/CURRENT-AUCTION-ATTEMPTS-2026-10-29.md',
            a.ROOT/'ai/RESUME.md', m.OUT/'state.json', m.originals.OUT/'collection-state.json',
            m.old.OUT/'STOP.json', m.ongoing.OUT/'STOP.json', m.DECISION, m.SOURCE, m.PREFLIGHT, m.PREP_EVIDENCE,
            a.ROOT/'ai/strong/current-auction-attempt-comparison-evidence-v3.json'}
        paths.update(a.ROOT/p for p in report['frozen_input_hashes'])
        paths.update((a.ROOT/'ai/runs/current-auction-failure-routing-preflight-v4').iterdir())
        paths.update((m.OUT/'cycles').glob('*.json'))
        for name in ('current-auction-retained-collection-v2-fourteenth.log',
            'current-auction-retained-collection-v2-fifteenth.log', 'current-auction-original-retained-completion-check-v3.json',
            'current-auction-failed-bucket-prepare-v3-first.log', 'current-auction-failed-bucket-upload-v3-first.log',
            'current-auction-failed-bucket-tests-v3-first.log', 'current-auction-failed-bucket-cycle-v3-first.log',
            'current-auction-failed-bucket-interrupted-cycle-v3.json', 'current-auction-failed-bucket-dispatch-v3-first.log',
            'current-auction-failed-bucket-collect-v3-first.log', 'current-auction-failure-routing-tests-v4-first.log',
            'current-auction-failure-routing-preflight-v4-first.log'):
            paths.add(a.ROOT/'ai/runs'/name)
        for base in (m.OUT, m.ongoing.OUT, m.old.OUT):
            for folder in (base/'jobs').iterdir():
                for name in ('launch-intent.json', 'launch.json', 'terminal.json', 'review.json', 'promotion-receipt.json'):
                    if (folder/name).is_file(): paths.add(folder/name)
                checks = sorted((folder/'checks').glob('*.json'))
                if checks: paths.add(checks[-1])
        OUT.mkdir()
        for path in sorted(paths):
            a.require(path.is_file() and not path.is_symlink(), 'Unexpected metadata input')
            target = OUT/path.relative_to(a.ROOT); target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target); a.require(a.digest(path) == a.digest(target), 'Metadata changed during copy')
        m.manifest(OUT)
        m.save(OUT.with_suffix('.intent.json'), {'manifest_sha256': a.digest(OUT/'manifest.json'),
            'automatic_retries': False, 'new_jobs': 0})
        archive = m.old.first.upload_evidence(OUT)
        m.save(DESCRIPTOR, {'archive': archive, 'routing_preflight_sha256': a.digest(REPORT),
            'status_sha256': a.digest(STATUS), 'manager_sha256': a.digest(m.__file__),
            'raw_archives_referenced_not_duplicated': True, 'new_jobs_during_archiving': 0,
            'qualified': False, 'reserved_final_seeds_used': False})
        print(json.dumps({'archive': archive, 'new_jobs': 0}), flush=True)


if __name__ == '__main__': main()
