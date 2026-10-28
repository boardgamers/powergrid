"""Measured runtime-only full-game job around the immutable v3 resource artifact.

Default is validation only. No submission, retry, policy selection or final seeds.
Failures retain partial evidence and, when requested, upload that evidence once.
"""
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import threading
import time

from public_policy_development_job_v1 import checked,digest,read,write,require

ENTRY='resource_turn_runtime_job_v1.py'
MANIFEST='source-manifest.json'
PROTOCOL='runtime-protocol.json'


class MemorySampler:
    # Same process-tree RSS sampler as the previous measured HF jobs. Shared
    # pages can be counted more than once; this is not a hard memory bound.
    def __init__(self):
        self.stop=threading.Event();self.peak=self.samples=0
        self.thread=threading.Thread(target=self.sample,daemon=True)

    def sample(self):
        while not self.stop.is_set():
            pending,seen,total=[os.getpid()],set(),0
            while pending:
                pid=pending.pop()
                if pid in seen:continue
                seen.add(pid)
                try:
                    status=Path(f'/proc/{pid}/status').read_text()
                    total+=int(next(line.split()[1] for line in status.splitlines() if line.startswith('VmRSS:')))*1024
                    pending.extend(map(int,Path(f'/proc/{pid}/task/{pid}/children').read_text().split()))
                except (FileNotFoundError,ProcessLookupError,PermissionError,StopIteration):pass
            self.peak=max(self.peak,total);self.samples+=1;self.stop.wait(.2)


def configuration(args):
    source=args.source.resolve();output=args.output.resolve()
    require(re.fullmatch('[a-f0-9]{64}',args.manifest_sha256) is not None,'Invalid manifest hash')
    require(digest(checked(source,MANIFEST))==args.manifest_sha256,'Source manifest changed')
    pins=read(source/MANIFEST)
    require(set(pins)|{MANIFEST}=={str(p.relative_to(source)) for p in source.rglob('*') if p.is_file()},'Source file set changed')
    require(all(digest(checked(source,name))==sha for name,sha in pins.items()),'Source bytes changed')
    require(Path(__file__).resolve()==checked(source,ENTRY),'Run the exact bundled job entry')
    require(not output.is_relative_to(source) and not source.is_relative_to(output),'Output overlaps frozen source')
    protocol=read(checked(source,PROTOCOL));job=read(checked(source,args.job))
    require(protocol['revision']=='resource-turn-runtime-v1' and protocol['scope']=='runtime-only','Wrong runtime protocol')
    require(protocol['new_strength_games']==0 and protocol['qualification_eligible'] is False
        and protocol['reserved_final_seeds_used'] is False and protocol['automatic_retries'] is False,'Invalid runtime scope')
    require(args.job in protocol['jobs'] and job==protocol['jobs'][args.job],'Unadmitted job')
    require(job['players'] in (2,6) and job['games']==4*job['players'] and job['workers']==4,'Invalid pilot size')
    require(job['start']==0 and job['deals']==1,'Runtime pilot must be one complete paired deal')
    if job['control']:
        require(job['mode']=='filter' and job['players']==2 and job['opponent']=='economic'
            and job['seed']=='resource-replanning-development-v1-2p' and job['reference'] is not None,'Wrong replay control')
    else:
        require(job['mode'] in ('atomic-search-corrected','atomic-search-anchored','search-turn')
            and job['opponent']=='search_geo' and job['seed']==f"resource-turn-runtime-v1-{job['players']}p"
            and job['reference'] is None,'Wrong experimental runtime cell')
    artifact=checked(source,'artifact',directory=True)
    sys.path.insert(0,str(artifact/'policy'))
    from resource_turn_full_policy_v3 import load_artifact,DESCRIPTOR
    root,spec,_=load_artifact(artifact)
    require(digest(root/DESCRIPTOR)==protocol['artifact_descriptor_sha256'],'Wrong artifact')
    require(digest(root/'manifest.json')==protocol['artifact_manifest_sha256'],'Wrong artifact manifest')
    require(spec['settings']=={'samples':8,'workers':1,'threads':1,'max_steps':2400},'Policy settings changed')
    if args.source_revision is not None or args.source_archive_sha256 is not None or args.upload:
        require(isinstance(args.source_revision,str) and re.fullmatch('[a-f0-9]{40}',args.source_revision),'Missing source revision')
        require(isinstance(args.source_archive_sha256,str) and re.fullmatch('[a-f0-9]{64}',args.source_archive_sha256),'Missing source archive hash')
    require(not args.upload or args.execute,'Validation cannot upload evidence')
    require(not os.environ.get('NODE_OPTIONS') and not os.environ.get('PG_TRACE_PATH'),'Unpinned engine override')
    command=[sys.executable,'-u','-B',str(artifact/'policy/resource_turn_full_arena_v3.py'),
        '--artifact',str(artifact),'--mode',job['mode'],'--players',str(job['players']),
        '--opponent',job['opponent'],'--seed',job['seed'],'--start','0','--deals','1',
        '--workers',str(job['workers']),'--output',str(output/'evaluation')]
    provenance={'source_manifest_sha256':args.manifest_sha256,'protocol_sha256':digest(source/PROTOCOL),
        'entry_sha256':digest(source/ENTRY),'job_spec_sha256':digest(source/args.job),
        'artifact_descriptor_sha256':protocol['artifact_descriptor_sha256'],
        'artifact_manifest_sha256':protocol['artifact_manifest_sha256'],
        'source_revision':args.source_revision,'source_archive_sha256':args.source_archive_sha256,'job':job}
    return source,artifact,output,command,provenance


def checked_replay(source,report,folder,job):
    if job['reference'] is None:return None
    reference=read(checked(source,job['reference']));decisions=0
    require(set(reference)=={str(i) for i in range(8)},'Incomplete recorded control')
    for record in report['results']:
        expected=reference[str(record['episode'])]
        require(record['terminal']==expected['terminal'],'Control terminal differs from recorded game')
        rows=[json.loads(line) for line in (folder/f"decisions-{record['episode']}.jsonl").read_text().splitlines()]
        require(len(rows)==len(expected['decisions']),'Control decision count changed')
        for row,original in zip(rows,expected['decisions']):
            require(row['response']['kind']=='atomic','Expected atomic control')
            actual={k:v for k,v in row['response']['decision'].items() if k!='elapsedMs'}
            gold={k:v for k,v in original.items() if k not in ('elapsedMs','decision','round')}
            require(actual==gold and row['executedActions']==[original['move']],'Control action/receipt differs')
            decisions+=1
    return {'exact_games':8,'exact_decisions':decisions,'reference_sha256':digest(source/job['reference'])}


def run(args):
    source,artifact,output,command,provenance=configuration(args)
    if not args.execute:
        print(json.dumps({'valid_job':True,'execute':False,'provenance':provenance}),flush=True);return
    output.mkdir(parents=True,exist_ok=False)
    shutil.copy2(source/MANIFEST,output/MANIFEST);shutil.copy2(source/args.job,output/'job-spec.json')
    status={'stage':'running','case':provenance['job']['name'],'scope':'runtime-only',
        'started_at':datetime.now(timezone.utc).isoformat(),'provenance':provenance,
        'gradient_updates':0,'automatic_retries':False,'new_strength_games':0,
        'qualification_eligible':False,'reserved_final_seeds_used':False}
    write(output/'status.json',status);sampler=MemorySampler();sampler.thread.start()
    began,cpu0=time.perf_counter(),os.times()
    try:
        with (output/'evaluation.log').open('x') as log:
            with subprocess.Popen(command,cwd='/tmp',stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True) as process:
                for line in process.stdout:
                    log.write(line);log.flush();print(json.dumps({'game_progress':line.rstrip()}),flush=True)
                if process.wait():raise subprocess.CalledProcessError(process.returncode,command)
        with (output/'audit.log').open('x') as log:
            subprocess.run([sys.executable,'-u','-B',str(artifact/'policy/resource_turn_full_audit_v3.py'),
                str(output/'evaluation/evaluation.json')],cwd='/tmp',stdout=log,stderr=subprocess.STDOUT,check=True)
        require(configuration(args)[4]==provenance,'Source changed during execution')
        report=read(output/'evaluation/evaluation.json');audit=read(output/'evaluation/independent-audit.json')
        require(report['all_complete'] and not report['errors'] and audit['passed'],'Incomplete runtime games')
        require(report['completed_games']==report['expected_games']==audit['games']==provenance['job']['games'],'Wrong game count')
        require(audit['counts']['rollout_caps']==0 and audit['paired_schedule_checked'],'Caps or incomplete pairing')
        replay=checked_replay(source,report,output/'evaluation',provenance['job'])
        status.update(stage='complete',games=audit['games'],counts=audit['counts'],replay=replay,
            evaluation_sha256=digest(output/'evaluation/evaluation.json'),
            audit_sha256=digest(output/'evaluation/independent-audit.json'))
    except BaseException as error:
        status.update(stage='failed',failure_type=type(error).__name__);raise
    finally:
        sampler.stop.set();sampler.thread.join();cpu1=os.times()
        status['measurement']={'seconds':time.perf_counter()-began,'cpu_seconds':sum(cpu1[:4])-sum(cpu0[:4]),
            'sampled_peak_total_rss_bytes':sampler.peak,'memory_samples':sampler.samples,
            'memory_sampling_period_seconds':.2,'includes_startup_and_validation':True}
        write(output/'status.json',status)
        write(output/'manifest.json',{str(p.relative_to(output)):digest(p) for p in sorted(output.rglob('*')) if p.is_file()})
        if args.upload:
            intent=output.with_suffix('.upload-intent.json')
            with intent.open('x') as stream:json.dump({'case':output.name,'manifest_sha256':digest(output/'manifest.json')},stream)
            sys.path.insert(0,str(artifact/'runtime/ai/strong'))
            from policy_iteration_evidence_archive import upload_evidence
            evidence=upload_evidence(output)
            write(output.with_suffix('.upload-receipt.json'),evidence)
            print(json.dumps({'case':output.name,'status':status,'evidence':evidence}),flush=True)
        else:print(json.dumps(status),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument('--source',type=Path,required=True);parser.add_argument('--manifest-sha256',required=True)
    parser.add_argument('--job',required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--source-revision');parser.add_argument('--source-archive-sha256')
    parser.add_argument('--execute',action='store_true');parser.add_argument('--upload',action='store_true')
    run(parser.parse_args())
