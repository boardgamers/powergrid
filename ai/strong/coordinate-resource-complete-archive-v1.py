"""Wait for the original complete comparison, then audit/archive exactly once."""
import os
from pathlib import Path
import subprocess
import sys
import time
from datetime import datetime, timezone

from strategic_collection import ROOT, read, write, digest

COORDINATOR = ROOT/'ai/runs/resource-replanning-development-coordinator-v1/state.json'
OUT = ROOT/'ai/runs/resource-complete-archive-watcher-v1'
EVIDENCE = ROOT/'ai/runs/resource-replanning-development-complete-evidence-v1'
DESCRIPTOR = ROOT/'ai/strong/resource-replanning-development-complete-evidence-v1.json'
COLLECTOR = ROOT/'ai/strong/collect-resource-replanning-development-v1.py'


def main():
    original = read(COORDINATOR)
    assert original['pid'] == 1291091 and original['stage'] in ('waiting_for_jobs', 'collecting', 'comparing', 'comparison_complete')
    assert not original['failed_jobs']
    if original['stage'] != 'comparison_complete': os.kill(original['pid'], 0)
    assert not any(path.exists() for path in (OUT, EVIDENCE, EVIDENCE.with_suffix('.tgz'), DESCRIPTOR)), 'Inspect existing watcher/archive outcomes; never duplicate'
    OUT.mkdir(parents=True)
    hashes = {**original['code_hashes'], str(COLLECTOR.relative_to(ROOT)): digest(COLLECTOR),
              str(Path(__file__).relative_to(ROOT)): digest(__file__)}
    state = {'pid': os.getpid(), 'started_at': datetime.now(timezone.utc).isoformat(),
             'original_coordinator_pid': original['pid'], 'plan_sha256': original['plan_sha256'],
             'code_hashes': hashes, 'stage': 'waiting_for_complete_comparison', 'automatic_retries': False,
             'new_hf_jobs': 0, 'gradient_updates': 0, 'qualification_eligible': False}

    def save():
        state['updated_at'] = datetime.now(timezone.utc).isoformat()
        temporary = OUT/'state.tmp.json'; write(temporary, state); temporary.replace(OUT/'state.json')

    save(); deadline = time.monotonic()+6*3600
    try:
        while time.monotonic() < deadline:
            assert all(digest(ROOT/name) == sha for name, sha in hashes.items())
            current = read(COORDINATOR)
            assert current['pid'] == original['pid'] and current['plan_sha256'] == original['plan_sha256']
            assert not current['failed_jobs'] and current['stage'] not in ('stopped_with_error', 'observation_window_ended')
            state['coordinator_stage'] = current['stage']; state['jobs_verified'] = current.get('jobs_verified', 0); save()
            if current['stage'] == 'comparison_complete':
                assert current['jobs_submitted'] == current['jobs_verified'] == 54
                assert not any(path.exists() for path in (EVIDENCE, EVIDENCE.with_suffix('.tgz'), DESCRIPTOR)), 'Another archive outcome needs reconciliation'
                state['stage'] = 'auditing_and_archiving'; save()
                with (OUT/'collector.log').open('x') as log:
                    subprocess.run([sys.executable, '-u', '-B', str(COLLECTOR), '--archive'],
                                   cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
                result = read(DESCRIPTOR)
                assert result['complete'] and result['remote_archive_verified'] and result['games'] == 3360
                assert result['comparison_sha256'] == current['comparison_sha256']
                state.update(stage='complete', descriptor_sha256=digest(DESCRIPTOR),
                             archive_sha256=result['archive_sha256'], revision=result['revision']); save()
                print({key: state[key] for key in ('stage', 'archive_sha256', 'revision')}, flush=True); return
            time.sleep(min(180, max(0, deadline-time.monotonic())))
        state['stage'] = 'observation_window_ended'; save()
    except BaseException as error:
        state.update(stage='stopped_with_error', error=type(error).__name__+': '+str(error)); save(); raise


if __name__ == '__main__': main()
