"""Replay only the preserved failed pilot prefix, stopping at its missing request.

No learner inference, replacement job, new full game or candidate selection.
The frozen independent opponent is necessarily rerun to reproduce the prefix.
"""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = ROOT/'ai/runs/resource-turn-full-artifact-v3'
JOB = ROOT/'ai/runs/resource-turn-runtime-hf-v1/pg-resource-turn-runtime-v1-anchored-2p'
OUT = ROOT/'ai/runs/resource-turn-boundary-failure-v1'
HANDLE = '6ae20c133fb22a235dd4146f'
RAW_MANIFEST = '466fad853bd4a04ccf0f5756af430321a4568cc9b049830277b1e5fcefabf7b1'
RECEIPT = 'a25de80c6585d70bfd7fa4cca963af1419655b56d92000c86321c9f1f859ffc1'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False); stream.write('\n')


def main():
    assert not OUT.exists(), 'Inspect preserved outcome before retrying'
    raw = JOB/'artifacts'
    assert read(JOB/'launch.json')['job_id'] == HANDLE
    assert read(JOB/'status.json')['stage'] == 'ERROR'
    assert digest(raw/'manifest.json') == RAW_MANIFEST
    manifest = read(raw/'manifest.json')
    assert set(manifest) == {str(p.relative_to(raw)) for p in raw.rglob('*') if p.is_file()}-{'manifest.json'}
    assert all(digest(raw/name) == sha for name, sha in manifest.items())
    status = read(raw/'status.json'); guard = read(JOB/'launch.json')
    assert status['stage'] == 'failed' and status['scope'] == 'runtime-only'
    assert status['provenance']['job'] == guard['row']['job']
    assert digest(raw/'source-manifest.json') == guard['source']['source_manifest_sha256']
    assert digest(raw/'job-spec.json') == guard['row']['job_spec_sha256']
    source = raw/'evaluation/decisions-7.jsonl'
    assert digest(source) == RECEIPT
    rows = [json.loads(line) for line in source.read_text().splitlines()]
    assert len(rows) == 137 and rows[-1]['request']['revision'] == 314
    sys.path.insert(0, str(ARTIFACT/'policy'))
    from resource_turn_full_policy_v3 import DESCRIPTOR, load_artifact
    from resource_turn_full_arena_v3 import Process
    _, spec, _ = load_artifact(ARTIFACT)
    identity = read(raw/'evaluation/game-0.json')['description']['resourceIdentity']
    OUT.mkdir(); shutil.copy2(__file__, OUT/Path(__file__).name)
    save(OUT/'design.json', {'job_id': HANDLE, 'episode': 7, 'recorded_learner_actions': 137,
        'raw_manifest_sha256': RAW_MANIFEST, 'raw_receipt_sha256': RECEIPT,
        'source_sha256': digest(__file__), 'artifact_descriptor_sha256': digest(ARTIFACT/DESCRIPTOR),
        'new_learner_inference': 0, 'opponent_prefix_reexecuted': True, 'new_full_games': 0,
        'new_hf_jobs': 0, 'reserved_final_seeds_used': False})
    arena = None; began = time.perf_counter(); checked = 0
    try:
        arena = Process(['node',str(ARTIFACT/'policy/resource-turn-arena-bridge-v1.cjs'),
            str(ARTIFACT/spec['runtime']['directory'])],OUT/'arena.stderr.log')
        state = arena.call({'op':'reset','n':1,'offset':7,'arenaSeed':'resource-turn-runtime-v1-2p',
            'playerCount':2,'mode':'search_geo','featureRevisions':{'learner':'4.3-strategic-correction'},
            'publicMoves':True,'publicResourceTurns':True,'policyIdentity':identity})
        for row in rows:
            assert not state['ended']
            current = state['observations'][0]
            assert current['request'] == row['request'], f'Public request differs at {checked}'
            assert current['moves'] == row['arenaMoves']
            assert current['playerOrder'] == row['arenaPlayerOrder']
            assert row['executedActions'] == [row['response']['move']]
            state = arena.call({'op':'step','actions':[{'publicMove':row['response']['move']}]})
            checked += 1
            if checked % 25 == 0: print(json.dumps({'replayed_prefix_actions':checked}),flush=True)
        assert not state['ended']
        request = state['observations'][0]['request']
        save(OUT/'failed-request.json', request)
        save(OUT/'failed-observation.json', state['observations'][0])
        assert request['revision'] == 315 and request['state']['phase'] == 'Resources'
        assert request['state']['newTurn'] is False
        last = request['state']['log'][-1]
        assert last['type'] == 'move' and last['player'] == request['player']
        assert last['move']['name'] == 'DiscardPowerPlant'
        # Directly call the unchanged frozen helper: no model or future rollout.
        js = """const fs=require('node:fs');
const q=JSON.parse(fs.readFileSync(process.argv[1],'utf8'));
q.featureRevision='4.3-strategic-correction';
require(process.argv[2]).createResourceTurnAnchor(process.argv[3]).prepare(q);
"""
        reproduced = subprocess.run(['node','-e',js,str(OUT/'failed-request.json'),
            str(ARTIFACT/'policy/resource-turn-anchor-v1.cjs'), str(ARTIFACT/spec['runtime']['directory'])],
            capture_output=True,text=True,check=False)
        (OUT/'anchor-original.stderr.log').write_text(reproduced.stderr)
        assert reproduced.returncode != 0 and 'Purchase history and turn boundary disagree' in reproduced.stderr
        arena.close(); arena = None
        save(OUT/'assessment.json', {'failure_reproduced':True, 'job_id':HANDLE,
            'recorded_prefix_actions_exact':checked,'failed_revision':request['revision'],
            'round':request['state']['round'],'step':request['state']['step'],
            'phase':request['state']['phase'],'newTurn':request['state']['newTurn'],
            'preceding_move':last['move'],'failed_request_sha256':digest(OUT/'failed-request.json'),
            'raw_archive_files_verified':len(manifest),'seconds':time.perf_counter()-began,
            'new_learner_inference':0,'opponent_prefix_reexecuted':True,'new_full_games':0,
            'new_hf_jobs':0,'qualification_eligible':False,'reserved_final_seeds_used':False,
            'output_hashes':{str(p.relative_to(OUT)):digest(p) for p in OUT.rglob('*') if p.is_file()}})
        print(json.dumps(read(OUT/'assessment.json')),flush=True)
    except BaseException as error:
        save(OUT/'failure.json',{'error':type(error).__name__+': '+str(error),
            'prefix_actions_checked':checked})
        raise
    finally:
        if arena is not None: arena.close()


if __name__ == '__main__':
    main()
