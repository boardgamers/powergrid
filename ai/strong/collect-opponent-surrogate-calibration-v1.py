"""Archive the complete two-endpoint HF calibration before collection admission."""
import argparse
import importlib.util
import json
from pathlib import Path
import shutil

from strategic_collection import ROOT,read,write,digest
from opponent_surrogate_verification_v1 import verify_artifacts
from policy_iteration_evidence_archive import upload_evidence

STRONG=ROOT/'ai/strong'
spec=importlib.util.spec_from_file_location('surrogate_endpoint_collector',STRONG/'collect-opponent-surrogate-runtime-v1.py')
endpoint=importlib.util.module_from_spec(spec)
spec.loader.exec_module(endpoint)
OUT=ROOT/'ai/runs/opponent-surrogate-calibration-evidence-v1'
DESCRIPTOR=STRONG/'opponent-surrogate-calibration-evidence-v1.json'


def audit():
    paths={n:endpoint.COLLECTED/f'opponent-surrogate-runtime-v1-{n}p-0-1/verified.json' for n in (2,6)}
    assert all(p.exists() for p in paths.values()), 'Both original HF endpoints must verify before admission or archive'
    source,protocol=endpoint.launcher.prerequisites()
    cells={};jobs=set()
    for n,path in paths.items():
        verified=read(path);folder=path.parent
        assert verified['verified'] is True and verified['authoritative_status']=='COMPLETED'
        assert verified['source']==source and verified['protocol_sha256']==digest(endpoint.launcher.PROTOCOL)
        assert verified['plan_sha256']==digest(endpoint.launcher.PLAN)
        assert all(digest(ROOT/name)==sha for name,sha in verified['collector_code_hashes'].items())
        guard=endpoint.launcher.GUARDS/(verified['case']+'.json')
        assert verified['guard_sha256']==digest(guard) and read(guard)['job_id']==verified['job_id']
        assert verified['job_id'] not in jobs;jobs.add(verified['job_id'])
        assert verified['evidence']['remote_archive_verified'] is True
        for key in ('gradients','qualification_eligible','reserved_final_seeds_used'):assert verified[key] is False
        review=verify_artifacts(folder/'artifacts',protocol,source,n,0,1,'runtime',verified['evidence'])
        assert review==verified['review'] and review['games']==review['twin_games']==4*n
        replays=verified['local_public_replays']
        assert {r['episode'] for r in replays}==set(range(4*n))
        for replay in replays:
            file=folder/'local-public-replays'/f"game-{replay['episode']}.json"
            assert digest(file)==replay['sha256']
            assert read(file)==read(folder/'artifacts/games'/f"game-{replay['episode']}"/'verification.json')
        assert sum(r['public_replays'] for r in replays)==review['public_replays']
        cells[str(n)]={'job_id':verified['job_id'],'case':verified['case'],'review':review,
                       'evidence':verified['evidence'],'verified_sha256':digest(path)}
    return {'complete':True,'jobs':2,'games':32,'paired_executions':64,'twin_games':32,
            'teacher_rows':sum(c['review']['teacher_rows'] for c in cells.values()),
            'teacher_rollouts':sum(c['review']['teacher_rollouts'] for c in cells.values()),
            'public_teacher_replays_hf':sum(c['review']['public_replays'] for c in cells.values()),
            'public_teacher_replays_local':sum(c['review']['public_replays'] for c in cells.values()),
            'caps':0,'cells':cells,'source':source,'admission':read(endpoint.launcher.PLAN),
            'protocol_sha256':digest(endpoint.launcher.PROTOCOL),'admission_sha256':digest(endpoint.launcher.PLAN),
            'collector_sha256':digest(__file__),'endpoint_code_hashes':read(paths[2])['collector_code_hashes'],
            'training_eligible':False,'collection_admitted':False,'gradients':False,
            'qualification_eligible':False,'reserved_final_seeds_used':False,
            'scope':'Complete runtime calibration, with every raw input/target checked, all games paired on HF and sampled public teacher calls repeated locally. Runtime-only deals are excluded from training and playing strength. Timings are HF CPU execution, not AMD8840U serving latency.'}


def main(archive=False):
    review=audit()
    if not archive:
        print(json.dumps(review,indent=2))
        return
    assert not any(p.exists() for p in (OUT,OUT.with_suffix('.tgz'),DESCRIPTOR)), 'Inspect earlier archive outcomes before any retry'
    files=[Path(__file__),STRONG/'opponent_surrogate_verification_v1.py',STRONG/'collect-opponent-surrogate-runtime-v1.py',
           STRONG/'test_opponent_surrogate_verification_v1.py',STRONG/'test_opponent_surrogate_calibration_v1.py',
           STRONG/'opponent-surrogate-source-v1.json',STRONG/'launch-opponent-surrogate-runtime-v1.py',
           STRONG/'opponent-surrogate-runtime-admission-v1.json',STRONG/'policy_iteration_evidence_archive.py',
           STRONG/'population_policy_verification.py',STRONG/'strategic_collection.py']
    files += [ROOT/name for name in review['source']['new_files']]
    files += list(endpoint.launcher.GUARDS.glob('*.json'))
    files += [p for p in endpoint.COLLECTED.rglob('*') if p.is_file()]
    files += [p for p in (ROOT/'ai/runs/opponent-surrogate-collection-preflight-v1').rglob('*') if p.is_file()]
    files += [p for p in (ROOT/'ai/runs/opponent-surrogate-source-prepared-v1').glob('layout-*') if p.is_file()]
    files += [ROOT/'ai/runs'/name for name in ('opponent-surrogate-source-preflight-v1.json',
              'opponent-surrogate-contract-tests-v1.log','opponent-surrogate-job-boundary-tests-v1.log',
              'opponent-surrogate-verification-tests-v1.log','opponent-surrogate-calibration-tests-v1.log',
              'opponent-surrogate-collector-preflight-v1.json','opponent-surrogate-runtime-2p-collection-v1.log',
              'opponent-surrogate-runtime-2p-collection-recheck-v1.log','opponent-surrogate-runtime-launched-v1.json')]
    OUT.mkdir()
    for path in sorted(set(files)):
        assert path.is_file() and not path.is_symlink()
        destination=OUT/path.relative_to(ROOT);destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(path,destination);assert digest(path)==digest(destination)
    write(OUT/'review.json',review)
    write(OUT/'manifest.json',{str(p.relative_to(OUT)):digest(p) for p in sorted(OUT.rglob('*')) if p.is_file()})
    write(DESCRIPTOR,{**review,**upload_evidence(OUT)})
    print({k:read(DESCRIPTOR)[k] for k in ('revision','archive_sha256','archived_files','remote_archive_verified')})


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('--archive',action='store_true')
    main(p.parse_args().archive)
