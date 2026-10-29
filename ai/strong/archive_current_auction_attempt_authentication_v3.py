"""Preserve mixed-attempt authentication proof and an exact live execution snapshot."""
import json
from pathlib import Path
import shutil

import current_auction_attempt_authentication_v3 as a

m=a.remaining
OUT=a.ROOT/'ai/runs/current-auction-attempt-authentication-evidence-v3'
REPORT=a.ROOT/'ai/strong/current-auction-attempt-authentication-preflight-v3.json'
STATUS=a.ROOT/'ai/strong/current-auction-attempt-authentication-status-v3.json'
DESCRIPTOR=a.ROOT/'ai/strong/current-auction-attempt-authentication-evidence-v3.json'


def main():
    a.require(not OUT.exists() and not OUT.with_suffix('.tgz').exists() and not DESCRIPTOR.exists(),
        'Inspect existing archive intent/outcome')
    with m.exclusive(m.old.OUT,'cycle'),m.exclusive(m.OUT,'cycle'):
        report=a.read(REPORT);status=a.read(STATUS)
        a.require(report['passed'] is True and report['code_sha256']==a.digest(a.__file__)
            and all(a.digest(a.ROOT/p)==sha for p,sha in report['frozen_input_hashes'].items()),'Authentication proof changed')
        a.require(status['current_state_sha256']==a.digest(m.OUT/'state.json')
            and status['original_collection_sha256']==a.digest(m.originals.OUT/'collection-state.json'),'Execution snapshot changed')
        api=m.HfApi();repo=m.worker.base.retention.REPO
        a.require(api.model_info(repo).private,'Private evidence required')
        a.require(not api.file_exists(repo,'archives/'+OUT.name+'.tgz'),'Inspect prior remote archive')
        paths={Path(__file__),Path(a.__file__),Path(a.previous.__file__),Path(a.coverage.__file__),REPORT,STATUS,
            a.ROOT/'ai/strong/preflight_current_auction_attempt_authentication_v3.py',
            a.ROOT/'ai/strong/test_current_auction_attempt_authentication_v3.py',
            a.ROOT/'ai/CURRENT-AUCTION-ATTEMPTS-2026-10-29.md',a.ROOT/'ai/RESUME.md',
            m.OUT/'state.json',m.originals.OUT/'collection-state.json',m.old.OUT/'STOP.json',
            m.SOURCE,m.DECISION,a.first.RESULT,a.first.SOURCE,a.first.originals.REGISTRY,
            a.ROOT/'ai/strong/current-auction-bucket-remaining-launch-v3.json',
            a.ROOT/'ai/strong/current-auction-bucket-remaining-launch-evidence-v3.json'}
        paths.update(a.ROOT/p for p in report['frozen_input_hashes'])
        paths.update((a.ROOT/'ai/runs/current-auction-attempt-authentication-preflight-v3').iterdir())
        for pattern in ('current-auction-attempt-authentication-tests-v3-first.log',
            'current-auction-attempt-authentication-preflight-v3-first.log',
            'current-auction-retained-post-failure-collection-v2-eleventh.log',
            'current-auction-retained-post-failure-collection-v2-twelfth.log',
            'current-auction-bucket-remaining-cycle-v3-second.log',
            'current-auction-bucket-remaining-cycle-v3-third.log',
            'current-auction-bucket-remaining-check-v3-second.log'):
            paths.add(a.ROOT/'ai/runs'/pattern)
        for base in (m.OUT,m.old.OUT):
            for folder in (base/'jobs').iterdir():
                for name in ('launch-intent.json','launch.json','terminal.json','review.json'):
                    if (folder/name).is_file():paths.add(folder/name)
                checks=sorted((folder/'checks').glob('*.json'))
                if checks:paths.add(checks[-1])
        OUT.mkdir()
        for path in sorted(paths):
            a.require(path.is_file() and not path.is_symlink(),'Unexpected metadata input')
            target=OUT/path.relative_to(a.ROOT);target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(path,target);a.require(a.digest(path)==a.digest(target),'Metadata changed while copying')
        m.manifest(OUT);m.save(OUT.with_suffix('.intent.json'),{'manifest_sha256':a.digest(OUT/'manifest.json'),
            'automatic_retries':False,'new_jobs':0})
        evidence=m.old.first.upload_evidence(OUT)
        m.save(DESCRIPTOR,{'archive':evidence,'preflight_sha256':a.digest(REPORT),'status_sha256':a.digest(STATUS),
            'authentication_sha256':a.digest(a.__file__),'new_jobs_during_archiving':0,
            'qualified':False,'reserved_final_seeds_used':False})
        print(json.dumps({'archive':evidence,'new_jobs_during_archiving':0}),flush=True)


if __name__=='__main__':main()
