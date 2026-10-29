"""Archive the one admitted launch and exact original-batch audit snapshot."""
import json
from pathlib import Path
import shutil

import manage_current_auction_first_bucket_v3 as m

OUT=m.ROOT/'ai/runs/current-auction-first-bucket-launch-evidence-v3'
SNAPSHOT=m.STRONG/'current-auction-first-bucket-launch-v3.json'
DESCRIPTOR=m.STRONG/'current-auction-first-bucket-launch-evidence-v3.json'


def main():
    m.require(not OUT.exists() and not OUT.with_suffix('.tgz').exists() and not DESCRIPTOR.exists(),
        'Inspect previous launch archive intent/outcome')
    with m.exclusive(m.old.OUT,'cycle'):
        source=m.source_checked();guard=m.checked_guard(m.OUT,source);snapshot=m.read(SNAPSHOT)
        m.require(snapshot['job_id']==guard['job_id'] and snapshot['launch_guard_sha256']==m.digest(m.OUT/'launch.json')
            and snapshot['original_collection_state_sha256']==m.digest(m.originals.OUT/'collection-state.json'),
            'Launch or original collection snapshot changed')
        repo=m.worker.base.retention.REPO;api=m.HfApi()
        m.require(api.model_info(repo).private,'Private launch archive required')
        m.require(not api.file_exists(repo,'archives/'+OUT.name+'.tgz'),'Inspect existing launch archive')
        paths=set(m.code_paths()+[Path(__file__),m.SOURCE,m.DECISION,m.TEST_LOG,SNAPSHOT,
            m.ROOT/'ai/CURRENT-AUCTION-FIRST-BUCKET-2026-10-29.md',m.ROOT/'ai/RESUME.md',
            m.originals.REGISTRY,m.originals.OUT/'collection-state.json',m.old.OUT/'STOP.json'])
        paths.update(m.PRE.joinpath('bundle').iterdir())
        paths.update(p for p in m.PRE.iterdir() if p.is_file() and p.suffix in ('.json','.log'))
        paths.update(p for p in m.OUT.iterdir() if p.is_file() and p.suffix in ('.json','.log'))
        paths.update(m.OUT.joinpath('checks').glob('*.json'))
        live=m.STRONG/'current-auction-first-bucket-live-checkpoint-v3.json'
        if live.exists():
            paths.add(live)
            paths.update(p for p in m.OUT.joinpath('first-live-checkpoint').rglob('*') if p.is_file())
        paths.update(m.ROOT.joinpath('ai/runs').glob('current-auction-first-bucket-*-v3-first.log'))
        for suffix in ('sixth','seventh'):
            paths.add(m.ROOT/f'ai/runs/current-auction-retained-post-failure-collection-v2-{suffix}.log')
        for item in m.read(m.originals.REGISTRY)['records']:
            folder=m.old.OUT/'jobs'/item['attempt_id']
            for name in ('launch.json','terminal.json','review.json'):
                if (folder/name).is_file():paths.add(folder/name)
            checks=sorted((folder/'checks').glob('*.json'))
            if checks:paths.add(checks[-1])
        OUT.mkdir()
        for path in sorted(paths):
            m.require(path.is_file() and not path.is_symlink(),'Invalid metadata input')
            destination=OUT/path.relative_to(m.ROOT);destination.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(path,destination);m.require(m.digest(path)==m.digest(destination),'Metadata changed during archive')
        m.save(OUT/'manifest.json',{str(p.relative_to(OUT)):m.digest(p) for p in sorted(OUT.rglob('*')) if p.is_file()})
        m.save(OUT.with_suffix('.intent.json'),{'manifest_sha256':m.digest(OUT/'manifest.json'),'automatic_retries':False,'new_jobs':0})
        evidence=m.old.first.upload_evidence(OUT)
        m.save(DESCRIPTOR,{'archive':evidence,'snapshot_sha256':m.digest(SNAPSHOT),
            'source_descriptor_sha256':m.digest(m.SOURCE),'decision_sha256':m.digest(m.DECISION),
            'job_id':guard['job_id'],'manager_sha256':m.digest(m.__file__),'new_jobs_during_archiving':0,
            'qualified':False,'reserved_final_seeds_used':False})
        print(json.dumps({'archive':evidence,'new_jobs_during_archiving':0}),flush=True)


if __name__=='__main__':main()
