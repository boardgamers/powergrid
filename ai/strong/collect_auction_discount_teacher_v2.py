"""Bounded bulk collection of completed teacher jobs, with independent audits."""
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from fractions import Fraction
import json
from pathlib import Path
import tarfile
import tempfile

from huggingface_hub import HfApi
from checkpoint_bucket_archives_v3 import BUCKET, checked_receipt, verify_archive
from checkpoint_bucket_transport_v3 import BucketTransport
from current_auction_resource_job_v2 import tree
from prepare_auction_discount_teacher_v2 import ROOT, PROTOCOL, digest, read, save
from audit_auction_discount_teacher_v2 import audit

OUT=ROOT/'ai/runs/auction-discount-teacher-collection-v2'
REPORT=ROOT/'ai/strong/auction-discount-teacher-results-v2.json'
PREP=ROOT/'ai/runs/auction-discount-teacher-prepared-v2/bundle'


def metadata(api, entries):
    paths=[r['path'] for r in entries];assert len(paths)==len(set(paths))
    objects=list(api.get_bucket_paths_info(BUCKET,paths));assert len(objects)==len(entries)
    by_path={o.path:o for o in objects};assert set(by_path)==set(paths)
    for r in entries:
        o=by_path[r['path']];assert o.xet_hash==r['xet_hash'] and o.size==r['bytes']
    return by_path


def collect_shard(job, protocol, identity):
    shard=job['shard'];folder=OUT/f'shard-{shard:02d}';entry=protocol['shards'][shard]
    report=folder/'audit.json';receipts=read(folder/'receipts.json')
    assert job['stage']=='COMPLETED' and job['final']['complete'] and job['final']['executed']
    assert job['final']['shard']==shard and job['final']['roots']==entry['roots']==len(receipts)
    assert job['final']['rollouts']==entry['rollouts']
    assert digest(PREP/entry['file'])==entry['sha256'];roots=read(PREP/entry['file'])
    assert [r['rootId'] for r in roots]==[r['rootId'] for r in receipts]
    for i,r in enumerate(receipts):checked_receipt(r['bucket_evidence'],f"{entry['name']}-root-{i:03d}")
    if report.exists():
        saved=read(report);assert saved['protocol_sha256']==digest(PROTOCOL)
        assert saved['auditor_sha256']==digest(ROOT/'ai/strong/audit_auction_discount_teacher_v2.py')
        assert saved['receipts_sha256']==digest(folder/'receipts.json')
        for i,r in enumerate(receipts):tree(folder/f'roots/{i:03d}','manifest.json',r['bucket_evidence']['manifest_sha256'])
        return saved
    api=HfApi();transport=BucketTransport(api);transport.private(BUCKET)
    entries=[r['bucket_evidence'] for r in receipts]
    before=transport.observe(lambda:metadata(api,entries));archives=folder/'archives';archives.mkdir(exist_ok=True)
    needed=[]
    for i,r in enumerate(entries):
        target=archives/f'{i:03d}.tgz'
        if target.exists():assert digest(target)==r['archive_sha256'] and target.stat().st_size==r['bytes']
        else:needed.append((before[r['path']],target))
    # SDK batches metadata and Xet transfers; avoid thousands of individual HTTP calls.
    if needed:api.download_bucket_files(BUCKET,needed,raise_on_missing_files=True)
    after=transport.observe(lambda:metadata(api,entries));transport.private(BUCKET)
    assert all(after[k].xet_hash==v.xet_hash and after[k].size==v.size for k,v in before.items())
    summaries=[];(folder/'roots').mkdir(exist_ok=True)
    for i,(root,r) in enumerate(zip(roots,entries)):
        archive=archives/f'{i:03d}.tgz';assert digest(archive)==r['archive_sha256'] and archive.stat().st_size==r['bytes']
        verify_archive(archive,r['manifest_sha256']);dest=folder/f'roots/{i:03d}'
        if not dest.exists():
            with tempfile.TemporaryDirectory(dir=folder/'roots') as temp:
                staged=Path(temp)/'tree';staged.mkdir()
                with tarfile.open(archive,'r:gz') as bundle:bundle.extractall(staged,filter='data')
                tree(staged,'manifest.json',r['manifest_sha256']);staged.rename(dest)
        tree(dest,'manifest.json',r['manifest_sha256'])
        assert read(dest/'root.json')==root
        result=read(dest/'result.json');assert result['shard']==shard
        summary=audit(root,result,digest(PROTOCOL),identity)
        summary.update(shard=shard,index=i,result_sha256=digest(dest/'result.json'))
        summaries.append(summary)
    data={'complete':True,'job_id':job['job_id'],'shard':shard,'roots':len(summaries),
        'rollouts':sum(s['rollouts'] for s in summaries),'job_program_seconds':job['final']['seconds'],
        'protocol_sha256':digest(PROTOCOL),'auditor_sha256':digest(ROOT/'ai/strong/audit_auction_discount_teacher_v2.py'),
        'receipts_sha256':digest(folder/'receipts.json'),'log_sha256':digest(folder/'job.log'),
        'summaries':summaries,'raw_audited':True,'training_ready':False,'qualified':False}
    assert data['rollouts']==entry['rollouts'];save(report,data)
    print(json.dumps({k:data[k] for k in ('shard','roots','rollouts')}),flush=True)
    return data


def summarize(rows):
    confident=consistent=negative=half_match=0;advantages=[];seconds=0.
    for r in rows:
        half_match+=r['half_best_sets_overlap'];seconds+=r['seconds']
        for a,d in r['actions'].items():
            if int(a)==r['baseline']:continue
            margin=float(Fraction(d['paired_mean_margin']));halves=[float(Fraction(v)) for v in d['half_margins']]
            negative+=margin<0
            if abs(margin)>.025:
                confident+=1;consistent+=halves[0]*halves[1]>0
        advantages.append(max(float(Fraction(d['paired_mean_margin'])) for d in r['actions'].values()))
    return {'roots':len(rows),'half_best_sets_overlap':half_match,
        'nonbaseline_actions_abs_margin_over_0025':confident,'same_sign_in_both_halves':consistent,
        'negative_action_margins':negative,'mean_best_sampled_advantage':sum(advantages)/len(advantages),
        'continuation_seconds':seconds,'scope':'Diagnostic simulated targets, not whole-game strength or calibrated confidence.'}


def main():
    assert not REPORT.exists(), 'Inspect completed collection before rerunning'
    state=read(OUT/'state.json');protocol=read(PROTOCOL)
    launch=read(ROOT/'ai/strong/auction-discount-teacher-launch-v2.json')
    assert len(state['jobs'])==len(launch['jobs'])==60 and state['stages']=={'COMPLETED':60}
    assert [(j['shard'],j['job_id']) for j in state['jobs']]==[(j['shard'],j['job_id']) for j in launch['jobs']]
    identity=read(ROOT/'ai/strong/auction-discount-teacher-preflight-v2.json')['identity']
    with ThreadPoolExecutor(max_workers=4) as pool:
        shards=list(pool.map(lambda j:collect_shard(j,protocol,identity),state['jobs']))
    rows=[r for s in shards for r in s['summaries']]
    assert len(rows)==len({r['rootId'] for r in rows})==protocol['roots']==5770
    assert Counter(r['split'] for r in rows)==protocol['splits']
    assert sum(r['rollouts'] for r in rows)==protocol['planned_rollouts']
    groups=defaultdict(list)
    for r in rows:
        for key in ('all',r['split'],'kind/'+r['kind'],'players/'+str(r['players'])):groups[key].append(r)
    report={'created_at':datetime.now(timezone.utc).isoformat(),'complete':True,'jobs':60,'roots':5770,
        'rollouts':sum(r['rollouts'] for r in rows),'splits':protocol['splits'],'caps':0,
        'protocol_sha256':digest(PROTOCOL),'source':read(ROOT/'ai/strong/auction-discount-teacher-source-v2.json'),
        'launch_sha256':digest(ROOT/'ai/strong/auction-discount-teacher-launch-v2.json'),
        'state_sha256':digest(OUT/'state.json'),'auditor_sha256':digest(ROOT/'ai/strong/audit_auction_discount_teacher_v2.py'),
        'collector_sha256':digest(__file__),'independently_audited':True,
        'job_program_seconds':sum(s['job_program_seconds'] for s in shards),
        'groups':{k:summarize(v) for k,v in sorted(groups.items())},
        'shards':[{'shard':s['shard'],'job_id':s['job_id'],'audit_sha256':digest(OUT/f"shard-{s['shard']:02d}/audit.json")} for s in shards],
        'new_gradient_updates':0,'qualified':False,'reserved_final_seeds_used':False}
    save(REPORT,report);print(json.dumps({k:report[k] for k in ('roots','rollouts','caps','job_program_seconds','groups')}),flush=True)


if __name__=='__main__':main()
