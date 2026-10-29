"""Reject synthetic missing-game evidence against the real frozen source package.

No actual runner execution, games, inference, HF jobs or reserved-seed use. All
job/status/evidence claims produced here are synthetic negative test fixtures.
"""
from contextlib import redirect_stdout
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import tarfile
from types import SimpleNamespace
from unittest.mock import patch

import public_policy_selected_final_job_v1 as job
import selected_public_policy_final_collection_v1 as collector
from public_policy_final_contract_v1 import admit, object_hash

ROOT = Path(__file__).resolve().parents[2]
STRONG = ROOT / 'ai/strong'
RUNS = ROOT / 'ai/runs'
OUT = RUNS / 'selected-public-policy-final-collection-preflight-v1'
RESULT = STRONG / 'selected-public-policy-final-collection-preflight-v1.json'
SOURCE = RUNS / 'selected-public-policy-final-source-preflight-v1/source'
TRANSPORT = RUNS / 'selected-public-policy-final-dispatch-preflight-v1'


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False); stream.write('\n')


def main():
    assert not OUT.exists() and not RESULT.exists(), 'Inspect existing preflight; no rerun'
    ready = job.read(STRONG / 'selected-public-policy-final-source-preflight-v1.json')
    assert ready['passed'] and ready['validated_jobs'] == 320 and ready['synthetic_candidate_and_allocation_only']
    assert job.digest(SOURCE / job.MANIFEST) == ready['source_manifest_sha256']
    release = job.read(TRANSPORT / 'synthetic-release.json')
    bootstrap = (TRANSPORT / 'final-bootstrap.sh').read_text()
    row = release['plan']['rows'][0]; spec = job.read(SOURCE / row['job'])
    identity = release['plan']['identity']; candidate_path = SOURCE / spec['candidate']
    contract_path = SOURCE / spec['contract']; contract = job.read(contract_path)
    assert job.digest(SOURCE / job.ENTRY) == job.digest(STRONG / job.ENTRY)
    inputs = {p: job.digest(p) for p in (Path(__file__).resolve(), STRONG / 'selected_public_policy_final_collection_v1.py',
        STRONG / 'test_selected_public_policy_final_collection_v1.py', STRONG / job.ENTRY,
        STRONG / 'public_policy_final_audit_v1.py', STRONG / 'public_policy_final_contract_v1.py',
        STRONG / 'selected_public_policy_final_dispatch_v1.py', STRONG / 'selected_public_policy_final_source_v1.py',
        STRONG / 'selected-public-policy-final-source-preflight-v1.json',
        STRONG / 'selected-public-policy-final-source-evidence-v1.json',
        TRANSPORT / 'synthetic-release.json', TRANSPORT / 'final-bootstrap.sh', SOURCE / job.MANIFEST,
        RUNS / 'selected-public-policy-final-collection-tests-v1-first.log',
        RUNS / 'selected-public-policy-final-collection-tests-v1-stage-worker-binding.log')}
    assert 'Ran 16 tests' in (RUNS / 'selected-public-policy-final-collection-tests-v1-stage-worker-binding.log').read_text()
    OUT.mkdir()
    save(OUT / 'SYNTHETIC-ONLY.json', {'purpose':'negative collection test; never real final evidence',
         'actual_games':0,'actual_subprocesses':0,'actual_hf_jobs':0,'reserved_final_seeds_used':False})
    folder = OUT / 'synthetic-job-data'
    binding = {**admit(contract,job.read(candidate_path),job.digest(candidate_path),identity),
        'contract_sha256':job.digest(contract_path),
        'runner_sha256':job.digest(SOURCE / 'artifact/ai/strong/public_policy_final_runner_v1.py'), 'purpose':'final'}
    fake_calls = []

    def fake_runner(command, **kwargs):
        fake_calls.append({'execute_requested_in_mock': '--execute' in command})
        if '--execute' not in command: return
        target = folder / 'evaluation'; target.mkdir()
        shutil.copyfile(candidate_path,target/'candidate.json'); shutil.copyfile(contract_path,target/'contract.json')
        config = {k:row['shard'][k] for k in ('players','start','deals','seed','opponent','opponent_sha256')}
        config.update(identity=identity,arm=identity['backend'],model_sha256=identity['modelSha256'],
                      samples=identity['settings']['samples'],search_workers=identity['settings']['workers'],
                      workers=row['workers'],descriptor=spec['descriptor'])
        # A deliberately lying completion summary: the independent auditor must
        # reject it because no actual game or decision receipts exist.
        job.write(target/'evaluation.json', {'config':config,'passed':True,'all_complete':True,'errors':[],
            'validation_error':None,'qualification_eligible':False,'reserved_final_seeds_used':True,
            'completed_games':row['shard']['games'],'expected_games':row['shard']['games'],
            'results':[],'game_caps':0,'rollout_caps':0,'seconds':0.0,'execution_binding':binding})
        job.write(target/'audit.json', {'counts':{},'reserved_final_seeds_used':True,'execution_binding':binding})

    args = SimpleNamespace(source=SOURCE,job=row['job'],output=folder,
        manifest_sha256=release['source']['source_manifest_sha256'],execute=True,upload=False,
        source_revision=release['source']['revision'],source_archive_sha256=release['source']['sha256'])
    with (OUT/'synthetic-wrapper.log').open('x') as log, redirect_stdout(log), \
            patch.object(job,'__file__',str(SOURCE/job.ENTRY)), patch.object(job.subprocess,'run',side_effect=fake_runner):
        job.run(args)
    assert fake_calls == [{'execute_requested_in_mock':False},{'execute_requested_in_mock':True}]
    archive = OUT/'synthetic-original.tgz'
    with tarfile.open(archive,'w:gz') as bundle:
        for p in sorted(folder.rglob('*')):
            if p.is_file(): bundle.add(p,arcname=str(p.relative_to(folder)))
    evidence = {'repo':'coyotte508/powergrid-ai-germany-v1','revision':'e'*40,
        'archive_path':'archives/'+row['name']+'.tgz','archive_sha256':job.digest(archive),
        'manifest_sha256':job.digest(folder/'manifest.json'),'archived_files':len(job.read(folder/'manifest.json'))+1,
        'format':'tar.gz','remote_archive_verified':True}
    launch = {'stage':'launched','name':row['name'],'job_id':'f'*24,
              'release_sha256':object_hash(release),'row':row}
    save(OUT/'synthetic-evidence-descriptor.json',evidence);save(OUT/'synthetic-launch.json',launch)
    try:
        collector.verify_artifacts(folder,SOURCE,release,launch,evidence,archive,bootstrap,hf_stage='COMPLETED')
    except ValueError as error:
        assert str(error) == 'Missing/duplicate episodes', 'Unexpected rejection boundary: '+str(error)
        rejection = str(error)
    else:
        raise AssertionError('Synthetic summary without actual games was accepted')
    assert all(job.digest(p) == sha for p,sha in inputs.items())
    state = job.read(RUNS/'current-auction-network-resume-v1/state.json')
    command = Path(f"/proc/{state['pid']}/cmdline")
    assert command.exists() and b'coordinate-current-auction-network-resume-v1.py' in command.read_bytes()
    assert all(job.digest(ROOT/n) == sha for n,sha in state['code_hashes'].items())
    report = {'passed':True,'created_at':datetime.now(timezone.utc).isoformat(),'unit_tests':16,
        'real_source_manifest_sha256':ready['source_manifest_sha256'],
        'real_source_and_archive_bindings_reached_independent_raw_audit':True,
        'synthetic_missing_game_summary_rejected':rejection,
        'input_hashes':{str(p.relative_to(ROOT)):sha for p,sha in inputs.items()},
        'synthetic_fixture_hashes':{str(p.relative_to(ROOT)):job.digest(p) for p in OUT.rglob('*') if p.is_file()},
        'owner_observation':{'pid':state['pid'],'live':True,'pins':len(state['code_hashes']),
            'verified_jobs':state['verified_jobs'],'submitted_jobs':state['submitted_jobs']},
        'actual_subprocesses':0,'games_executed':0,'policy_inference_calls':0,'hf_jobs_submitted':0,
        'candidate_selected':False,'qualified':False,'reserved_final_seeds_used':False,
        'scope':'Collection/provenance and negative raw-audit integration over the real frozen artifact. Synthetic candidate, launch and completion claims only. No actual final-game evidence, selection/admission proof or qualification.'}
    save(RESULT,report)
    print(json.dumps({k:report[k] for k in ('passed','unit_tests','synthetic_missing_game_summary_rejected','games_executed','hf_jobs_submitted','owner_observation')}),flush=True)


if __name__ == '__main__':main()
