"""Run one immutable HF capture shard and preserve all output, including failures."""
import argparse
import os
from pathlib import Path
import threading
import time

from huggingface_hub import hf_hub_download
from strategic_collection import ROOT, read, write, digest
from opponent_surrogate_collection_v1 import PROTOCOL, run
from policy_iteration_evidence_archive import upload_evidence


class MemorySampler:
    def __init__(self):
        self.stop = threading.Event()
        self.peak = self.samples = 0
        self.thread = threading.Thread(target=self.sample, daemon=True)

    def sample(self):
        while not self.stop.is_set():
            pending, seen, rss = [os.getpid()], set(), 0
            while pending:
                pid = pending.pop()
                if pid in seen: continue
                seen.add(pid)
                try:
                    status = Path(f'/proc/{pid}/status').read_text()
                    rss += int(next(s.split()[1] for s in status.splitlines() if s.startswith('VmRSS:'))) * 1024
                    pending.extend(map(int,Path(f'/proc/{pid}/task/{pid}/children').read_text().split()))
                except (FileNotFoundError, ProcessLookupError, PermissionError, StopIteration):
                    continue
            self.peak = max(self.peak,rss)
            self.samples += 1
            self.stop.wait(.2)


def main(players, start, end, mode):
    assert mode in ('runtime','collection') and type(players) is int and players in range(2,7)
    if mode == 'runtime': assert players in (2,6) and (start,end) == (0,1)
    else: assert 0 <= start < end <= 32
    assert digest(PROTOCOL) == os.environ['PROTOCOL_SHA256']
    manifest = ROOT / 'opponent-surrogate-source-manifest.json'
    assert digest(manifest) == os.environ['SOURCE_MANIFEST_SHA256']
    hashes = read(manifest)
    assert all(digest(ROOT/name)==sha for name,sha in hashes.items())
    protocol = read(PROTOCOL)
    assert digest(ROOT/'ai/strong/capture-reference-opponent-v1.cjs') == protocol['capture_module_sha256']
    case = f'opponent-surrogate-{mode}-v1-{players}p-{start}-{end}'
    output = ROOT / 'ai/runs' / case
    output.mkdir(parents=True,exist_ok=False)
    status = {'case':case,'stage':'running','mode':mode,'players':players,'start':start,'end':end,
              'protocol_sha256':digest(PROTOCOL),'source_revision':os.environ['SOURCE_REVISION'],
              'source_sha256':os.environ['SOURCE_SHA256'],'source_manifest_sha256':digest(manifest),
              'job_runner_sha256':digest(__file__),'automatic_retries':False,'gradients':False,
              'qualification_eligible':False,'reserved_final_seeds_used':False}
    sampler = MemorySampler()
    began, cpu0 = time.perf_counter(), os.times()
    try:
        pin = protocol['focal']['model']
        model = hf_hub_download(pin['repo'],pin['prefix']+'/inference64.onnx',revision=pin['revision'])
        assert digest(model) == pin['files']['inference64.onnx']
        sampler.thread.start()
        result = run(ROOT,model,players,start,end,mode,output/'games',protocol['workers'])
        assert result['stage']=='complete' and not result['errors']
        assert len(result['cases']) == (end-start)*players*4
        assert all(digest(ROOT/name)==sha for name,sha in hashes.items()), 'Source changed during collection'
        status.update(stage='complete',games=len(result['cases']),teacher_rows=result['teacher_rows'],
                      public_replays=result['public_replays'],twin_games=result['twin_games'],caps=0)
    except BaseException as error:
        status.update(stage='failed',error=type(error).__name__+': '+str(error))
        raise
    finally:
        sampler.stop.set()
        if sampler.thread.is_alive(): sampler.thread.join()
        cpu1 = os.times()
        status['runtime'] = {'seconds':time.perf_counter()-began,'cpu_seconds':sum(cpu1[:4])-sum(cpu0[:4]),
                             'sampled_peak_total_rss_bytes':sampler.peak,'memory_samples':sampler.samples,
                             'memory_sampling_period_seconds':.2}
        write(output/'job.json',status)
        write(output/'manifest.json',{str(p.relative_to(output)):digest(p) for p in sorted(output.rglob('*')) if p.is_file()})
        evidence = upload_evidence(output)
        print({'status':status,'evidence':evidence},flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__)
    p.add_argument('players',type=int)
    p.add_argument('start',type=int)
    p.add_argument('end',type=int)
    p.add_argument('--mode',choices=['runtime','collection'],required=True)
    a=p.parse_args()
    main(a.players,a.start,a.end,a.mode)
