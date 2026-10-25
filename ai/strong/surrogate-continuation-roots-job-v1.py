"""HF root-capture shard with measured resources and preserved failure artifacts."""
import argparse
import os
from pathlib import Path
import threading
import time

from huggingface_hub import hf_hub_download
from strategic_collection import ROOT, read, write, digest
from hybrid_search import Model
from population_hybrid_policy import PopulationPolicy
from surrogate_continuation_roots_v1 import PROTOCOL, run, verify_game
from policy_iteration_evidence_archive import upload_evidence

MODEL_PIN = {'repo': 'coyotte508/powergrid-ai-germany-v1',
             'revision': '6b6009756d7b5968bc5b6425efc84a94aab2a1d6',
             'path': 'runs/policy-iteration-training-v2-frozen/ensemble-1/derivative/inference64.onnx'}


class MemorySampler:
    def __init__(self):
        self.stop = threading.Event(); self.peak = self.samples = 0
        self.thread = threading.Thread(target=self.sample, daemon=True)

    def sample(self):
        while not self.stop.is_set():
            pending, seen, total = [os.getpid()], set(), 0
            while pending:
                pid = pending.pop()
                if pid in seen: continue
                seen.add(pid)
                try:
                    status = Path(f'/proc/{pid}/status').read_text()
                    total += int(next(line.split()[1] for line in status.splitlines() if line.startswith('VmRSS:')))*1024
                    pending.extend(map(int, Path(f'/proc/{pid}/task/{pid}/children').read_text().split()))
                except (FileNotFoundError, ProcessLookupError, PermissionError, StopIteration): pass
            self.peak = max(self.peak, total); self.samples += 1; self.stop.wait(.2)


def main(players, start, end, mode):
    p = read(PROTOCOL)
    assert type(players) is int and players in p['player_counts'] and mode in ('root', 'runtime')
    assert type(start) is type(end) is int and 0 <= start < end <= p['deals_per_count']
    if mode == 'runtime': assert players in (2, 6) and (start, end) == (0, 1)
    assert digest(PROTOCOL) == os.environ['PROTOCOL_SHA256']
    manifest = ROOT/'surrogate-continuation-roots-source-manifest.json'
    assert digest(manifest) == os.environ['SOURCE_MANIFEST_SHA256']
    hashes = read(manifest); assert all(digest(ROOT/name) == sha for name, sha in hashes.items())
    case = f'surrogate-continuation-{mode}-v1-{players}p-{start}-{end}'
    out = ROOT/'ai/runs'/case; out.mkdir(parents=True, exist_ok=False)
    status = {'case': case, 'stage': 'running', 'players': players, 'start': start, 'end': end, 'mode': mode,
              'source_revision': os.environ['SOURCE_REVISION'], 'source_sha256': os.environ['SOURCE_SHA256'],
              'source_manifest_sha256': digest(manifest), 'protocol_sha256': digest(PROTOCOL),
              'job_runner_sha256': digest(__file__), 'automatic_retries': False, 'gradients': False,
              'qualification_eligible': False, 'reserved_final_seeds_used': False}
    sampler = MemorySampler(); began, cpu0 = time.perf_counter(), os.times()
    try:
        model_path = hf_hub_download(MODEL_PIN['repo'], MODEL_PIN['path'], revision=MODEL_PIN['revision'])
        assert digest(model_path) == p['focal_model_sha256']; sampler.thread.start()
        result = run(ROOT, model_path, players, start, end, mode, out/'games', p['workers'])
        assert result['stage'] == 'complete' and not result['errors'] and len(result['cases']) == (end-start)*players*4
        assert set(result['cases']) == {str(i) for i in range(start*players*4, end*players*4)}
        assert all(int(episode) == case['episode'] and case['players'] == players and case['mode'] == mode
                   and case['twin_exact'] is (mode == 'runtime') for episode, case in result['cases'].items())
        policy = PopulationPolicy(Model(model_path, threads=1), ROOT/'ai/strong/population-hybrid-policy.cjs', arm='filter')
        try:
            checks = {episode: verify_game(out/'games'/f'game-{episode}', policy) for episode in sorted(result['cases'], key=int)}
        finally: policy.close()
        write(out/'root-audit.json', checks)
        assert all(digest(ROOT/name) == sha for name, sha in hashes.items())
        status.update(stage='complete', games=len(result['cases']), selected_roots=result['selected_roots'],
                      twin_games=sum(c['twin_exact'] for c in result['cases'].values()),
                      eligible_decisions=sum(c['eligible_decisions'] for c in result['cases'].values()), caps=0)
    except BaseException as error:
        status.update(stage='failed', error=type(error).__name__+': '+str(error)); raise
    finally:
        sampler.stop.set()
        if sampler.thread.is_alive(): sampler.thread.join()
        cpu1 = os.times(); status['runtime'] = {'seconds': time.perf_counter()-began,
            'cpu_seconds': sum(cpu1[:4])-sum(cpu0[:4]), 'sampled_peak_total_rss_bytes': sampler.peak,
            'memory_samples': sampler.samples, 'memory_sampling_period_seconds': .2}
        write(out/'job.json', status)
        write(out/'manifest.json', {str(path.relative_to(out)): digest(path) for path in sorted(out.rglob('*')) if path.is_file()})
        evidence = upload_evidence(out); print({'status': status, 'evidence': evidence}, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    for name in ('players', 'start', 'end'): parser.add_argument(name, type=int)
    parser.add_argument('--mode', choices=['root', 'runtime'], required=True)
    args = parser.parse_args(); main(args.players, args.start, args.end, args.mode)
