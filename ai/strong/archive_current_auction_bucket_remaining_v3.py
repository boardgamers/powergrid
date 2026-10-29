"""Archive completed first proof and the exact bounded remaining-launch snapshot."""
import json
from pathlib import Path
import shutil

import manage_current_auction_bucket_remaining_v3 as m

OUT=m.ROOT/'ai/runs/current-auction-bucket-remaining-launch-evidence-v3'
SNAPSHOT=m.STRONG/'current-auction-bucket-remaining-launch-v3.json'
DESCRIPTOR=m.STRONG/'current-auction-bucket-remaining-launch-evidence-v3.json'


def main():
    m.require(not OUT.exists() and not OUT.with_suffix('.tgz').exists() and not DESCRIPTOR.exists(),
        'Inspect prior launch archive intent/outcome')
    with m.exclusive(m.old.OUT,'cycle'),m.exclusive(m.OUT,'cycle'):
        source=m.source_checked();snapshot=m.read(SNAPSHOT)
        m.require(snapshot['source_descriptor_sha256']==m.digest(m.SOURCE)
            and snapshot['state_sha256']==m.digest(m.OUT/'state.json')
            and snapshot['original_collection_state_sha256']==m.digest(m.originals.OUT/'collection-state.json')
            and snapshot['first_bucket_result_sha256']==m.digest(m.first.RESULT),'Snapshot inputs changed')
        api=m.HfApi();repo=m.worker.base.retention.REPO
        m.require(api.model_info(repo).private,'Private recovery archive required')
        m.require(not api.file_exists(repo,'archives/'+OUT.name+'.tgz'),'Inspect existing recovery archive')
        paths=set(m.code_paths()+[Path(__file__),SNAPSHOT,m.SOURCE,m.DECISION,m.PREFLIGHT,m.PREP_EVIDENCE,m.TEST_LOG,
            m.first.RESULT,m.first.SOURCE,m.first.OUT/'raw-review.json',m.first.OUT/'terminal.json',
            m.first.OUT/'promotion-intent.json',m.first.OUT/'promotion-receipt.json',
            m.ROOT/'ai/CURRENT-AUCTION-BUCKET-REMAINING-2026-10-29.md',
            m.ROOT/'ai/CURRENT-AUCTION-FIRST-BUCKET-2026-10-29.md',m.ROOT/'ai/RESUME.md',
            m.OUT/'state.json',m.originals.REGISTRY,m.originals.OUT/'collection-state.json',m.old.OUT/'STOP.json'])
        paths.update(p for p in m.PRE.iterdir() if p.is_file() and p.suffix in ('.json','.log'))
        paths.update(m.ROOT.joinpath('ai/runs').glob('current-auction-bucket-remaining-*-v3-first.log'))
        paths.add(m.ROOT/'ai/runs/current-auction-first-bucket-collection-v3-first.log')
        for suffix in ('eighth','ninth','tenth'):
            paths.add(m.ROOT/f'ai/runs/current-auction-retained-post-failure-collection-v2-{suffix}.log')
        for base in (m.OUT,m.old.OUT):
            for folder in (base/'jobs').iterdir():
                for name in ('launch-intent.json','launch.json','terminal.json','review.json'):
                    if (folder/name).is_file():paths.add(folder/name)
                checks=sorted((folder/'checks').glob('*.json'))
                if checks:paths.add(checks[-1])
        OUT.mkdir()
        for path in sorted(paths):
            m.require(path.is_file() and not path.is_symlink(),'Invalid recovery metadata input')
            dest=OUT/path.relative_to(m.ROOT);dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(path,dest);m.require(m.digest(path)==m.digest(dest),'Metadata changed during archive')
        m.manifest(OUT);m.save(OUT.with_suffix('.intent.json'),{'manifest_sha256':m.digest(OUT/'manifest.json'),
            'automatic_retries':False,'new_jobs':0})
        archived=m.old.first.upload_evidence(OUT)
        m.save(DESCRIPTOR,{'archive':archived,'snapshot_sha256':m.digest(SNAPSHOT),
            'source_descriptor_sha256':m.digest(m.SOURCE),'first_bucket_result_sha256':m.FIRST_RESULT_SHA,
            'first_complete_collection_archive':m.read(m.first.RESULT)['versioned_collection_archive'],
            'new_jobs_during_archiving':0,'qualified':False,'reserved_final_seeds_used':False})
        print(json.dumps({'archive':archived,'new_jobs_during_archiving':0}),flush=True)


if __name__=='__main__':main()
