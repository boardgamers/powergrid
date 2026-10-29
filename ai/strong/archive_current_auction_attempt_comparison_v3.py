"""Archive comparison integration and a fixed execution snapshot; no new jobs."""
from pathlib import Path
import json
import shutil

import current_auction_attempt_comparison_v3 as c

m = c.auth.remaining
OUT = c.ROOT/'ai/runs/current-auction-attempt-comparison-evidence-v3'
REPORT = m.STRONG/'current-auction-attempt-comparison-preflight-v3.json'
STATUS = m.STRONG/'current-auction-attempt-comparison-status-v3.json'
DESCRIPTOR = m.STRONG/'current-auction-attempt-comparison-evidence-v3.json'


def main():
    c.require(not OUT.exists() and not OUT.with_suffix('.tgz').exists() and not DESCRIPTOR.exists(),
              'Inspect existing archive intent/outcome')
    with m.exclusive(m.old.OUT, 'cycle'), m.exclusive(m.OUT, 'cycle'):
        report, status = c.read(REPORT), c.read(STATUS)
        c.require(report['passed'] is True and report['code_sha256'] == c.digest(c.__file__)
                  and all(c.digest(c.ROOT/p) == sha for p, sha in report['input_hashes'].items()), 'Integration proof changed')
        c.require(status['current_state_sha256'] == c.digest(m.OUT/'state.json')
                  and status['original_collection_sha256'] == c.digest(m.originals.OUT/'collection-state.json'),
                  'Execution snapshot changed')
        api = m.HfApi(); repo = m.worker.base.retention.REPO
        c.require(api.model_info(repo).private, 'Private archive required')
        c.require(not api.file_exists(repo, 'archives/'+OUT.name+'.tgz'), 'Inspect prior remote archive')
        paths = {Path(__file__), REPORT, STATUS, c.ROOT/'ai/CURRENT-AUCTION-ATTEMPTS-2026-10-29.md',
                 c.ROOT/'ai/RESUME.md', m.OUT/'state.json', m.originals.OUT/'collection-state.json', m.old.OUT/'STOP.json',
                 c.ROOT/'ai/strong/current-auction-attempt-authentication-evidence-v3.json'}
        paths.update(c.ROOT/p for p in report['input_hashes'])
        preflight = c.ROOT/'ai/runs/current-auction-attempt-comparison-preflight-v3'
        paths.update(preflight.iterdir())
        for case in c.read(preflight/'intent.json')['cases']:
            receipt = c.ROOT/case['receipt_file']; paths.add(receipt)
            folder = (c.originals.manager('confirmation').OUT/case['name'] if case['backend'] == 'original'
                      else c.auth.locations(case['name'], case['backend'])['folder'])
            paths.add(folder/'launch.json')
        for name in ('current-auction-attempt-comparison-preflight-v3-first.log',
                     'current-auction-retained-collection-v2-thirteenth.log', 'current-auction-bucket-cycle-v3-fourth.log'):
            paths.add(c.ROOT/'ai/runs'/name)
        for base in (m.OUT, m.old.OUT):
            for folder in (base/'jobs').iterdir():
                for name in ('launch-intent.json', 'launch.json', 'terminal.json', 'review.json', 'promotion-receipt.json'):
                    if (folder/name).is_file(): paths.add(folder/name)
        OUT.mkdir()
        for path in sorted(paths):
            c.require(path.is_file() and not path.is_symlink(), 'Unexpected metadata input')
            target = OUT/path.relative_to(c.ROOT); target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target); c.require(c.digest(path) == c.digest(target), 'Metadata changed during copy')
        m.manifest(OUT)
        m.save(OUT.with_suffix('.intent.json'), {'manifest_sha256': c.digest(OUT/'manifest.json'),
                                               'automatic_retries': False, 'new_jobs': 0})
        archive = m.old.first.upload_evidence(OUT)
        m.save(DESCRIPTOR, {'archive': archive, 'preflight_sha256': c.digest(REPORT), 'status_sha256': c.digest(STATUS),
            'comparison_code_sha256': c.digest(c.__file__), 'new_jobs_during_archiving': 0,
            'raw_archives_referenced_not_duplicated': True, 'qualified': False, 'reserved_final_seeds_used': False})
        print(json.dumps({'archive': archive, 'new_jobs': 0}), flush=True)


if __name__ == '__main__': main()
