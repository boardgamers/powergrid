"""Freeze the provenance wrapper and exercise real models on plumbing-only deals."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
from huggingface_hub import HfApi, hf_hub_download
from strategic_collection import ROOT, read, write, digest


def main():
    base = read(ROOT/'ai/strong/strategic-correction-screen-source-v1.json')
    archive = hf_hub_download('coyotte508/powergrid-ai-training-v1', base['archive'],
        repo_type='dataset', revision=base['revision'])
    assert digest(archive) == base['sha256']
    out = ROOT/'ai/runs/final-strategic-runtime-source-v1'
    out.mkdir(exist_ok=False)
    with tarfile.open(archive) as bundle:
        bundle.extractall(out, filter='data')
    before = {str(p.relative_to(out)): digest(p) for p in out.rglob('*') if p.is_file()}
    relative = 'ai/strong/arena-job.py'
    assert relative in before and 'evaluation.json' not in before
    shutil.copy2(ROOT/relative, out/relative)
    for name in ['features-v4_3.cjs', 'encoders.cjs', 'evaluate.py']:
        assert digest(out/'ai/strong'/name) == digest(ROOT/'ai/strong'/name)
    unchanged = {name: sha for name, sha in before.items() if name != relative}
    assert all(digest(out/name) == sha for name, sha in unchanged.items())
    target = ROOT/'ai/runs/strong-source-final-strategic-runtime-20261023-v1.tgz'
    assert not target.exists()
    with tarfile.open(target, 'w:gz') as bundle:
        for name in sorted(before):
            bundle.add(out/name, arcname=name, recursive=False)
    commit = HfApi().upload_file(repo_id='coyotte508/powergrid-ai-training-v1', repo_type='dataset',
        path_or_fileobj=target, path_in_repo=target.name)
    source = {'archive': target.name, 'revision': commit.oid, 'sha256': digest(target),
        'base': {k:base[k] for k in ['archive','revision','sha256']},
        'overlays': {relative:digest(out/relative)}, 'old_runner_sha256': before[relative],
        'arena_runner_sha256': digest(out/relative), 'unchanged_base_file_count':len(unchanged),
        'qualification_eligible':False,
        'scope':'Only the provenance wrapper changes. Engine, features, inference, search and evaluator bytes match the frozen development source.'}
    write(ROOT/'ai/strong/final-strategic-runtime-source-v1.json', source)
    print({'source_revision':source['revision'], 'source_sha256':source['sha256']}, flush=True)
    checks = ROOT/'ai/runs/final-strategic-runtime-preflight-v1'
    checks.mkdir(exist_ok=False)
    spec = importlib.util.spec_from_file_location('wrapper_contract', ROOT/'ai/strong/collect-population-screen.py')
    contract = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(contract)
    # Only artifact publication is replaced. The wrapper downloads the real pinned
    # model and invokes the real evaluator/engine as it does on HF Jobs.
    wrapper = '''
from pathlib import Path
import os, runpy, shutil
from unittest.mock import patch
from huggingface_hub import HfApi
def save(self, **kwargs):
    assert kwargs['repo_id'] == os.environ['HF_MODEL_REPO']
    assert kwargs['path_in_repo'] == 'runs/'+os.environ['RUN_NAME']+'/evaluation.json'
    assert kwargs['path_or_fileobj'] == 'evaluation.json'
    shutil.copy2(kwargs['path_or_fileobj'], Path(os.environ['CHECK_OUTPUT'])/'evaluation.json')
with patch.object(HfApi, 'upload_file', new=save):
    runpy.run_path('ai/strong/arena-job.py', run_name='__main__')
'''
    report = {'passed':False, 'source':source, 'cases':{}, 'reserved_final_seeds_used':False,
        'candidate_selected':False, 'qualification_eligible':False,
        'scope':'Real local wrapper/evaluator/engine/model execution; only HF artifact upload is captured locally. Separate plumbing deals with offset4; no gradients, selection or strength claims.'}
    try:
        for key in ['11101','11102']:
            pin = read(ROOT/'ai/strong/strategic-correction-screen-pins-v1'/(key+'.json'))
            assert pin['training_verified'] and pin['feature_revision'] == '4.3-strategic-correction'
            for n in [2,6]:
                case_name = key+'-'+str(n)+'p'
                directory = checks/case_name
                directory.mkdir()
                seed = 'strategic-wrapper-plumbing-v1-'+case_name
                assert 'reserved' not in seed
                env = os.environ.copy()
                for name in ['OPPONENT_MODEL_PATH','OPPONENT_MODEL_REVISION','OPPONENT_MODEL_SHA256']:
                    env.pop(name, None)
                env.update(HF_MODEL_REPO=pin['repo'], MODEL_PATH=pin['prefix']+'/inference64.onnx',
                    MODEL_REVISION=pin['revision'], MODEL_SHA256=pin['files']['inference64.onnx'],
                    SOURCE_ARCHIVE=source['archive'], SOURCE_REVISION=source['revision'],
                    SOURCE_SHA256=source['sha256'], PLAYER_COUNT=str(n), DEAL_OFFSET='4',
                    OPPONENT='economic', GAMES=str(4*n), WORKERS='24', EVAL_SEED=seed,
                    RUN_NAME=seed, SEARCH_SCOPE='all', SEARCH_SAMPLES='0', GEOGRAPHY='0',
                    ASYNC_ARENA='0', DISABLE_SEARCH_PROPOSAL='0', CHECK_OUTPUT=str(directory))
                with (directory/'wrapper.log').open('w') as log:
                    subprocess.run([sys.executable, '-c', wrapper], cwd=out, env=env,
                        stdout=log, stderr=subprocess.STDOUT, check=True)
                result = read(directory/'evaluation.json')
                summary = contract.verify_report(result,
                    {'players':n, 'games':4*n, 'opponent':'economic', 'deal_offset':4},
                    {'hashes':{'latest.onnx':pin['files']['inference64.onnx']}},
                    {'seed_template':seed, 'deal_offsets':[4]}, pin['feature_revision'])
                assert result['source'] == {k:source[k] for k in ['archive','revision','sha256']}
                assert result['arena_runner_sha256'] == source['arena_runner_sha256']
                assert result['model_repository_revision'] == pin['revision']
                assert result['opponent_repository_revision'] is None and result['run_name'] == seed
                assert result['async_rollout'] is False
                assert {r['episode'] for r in result['results']} == set(range(4*4*n,5*4*n))
                report['cases'][case_name] = {'model_pin':pin, 'summary':summary,
                    'evaluation_sha256':digest(directory/'evaluation.json')}
                print({'case':case_name, 'games':4*n, 'provenance_verified':True}, flush=True)
        assert all(digest(out/name) == sha for name, sha in unchanged.items())
        assert digest(out/relative) == source['arena_runner_sha256']
        report.update(passed=True, games=64, unchanged_base_file_count=len(unchanged))
    finally:
        write(checks/'check.json', report)
        write(ROOT/'ai/strong/final-strategic-runtime-preflight-v1.json', report)
    print({'passed':report['passed'], 'games':report['games'], 'reserved_final_seeds_used':False})


if __name__ == '__main__':
    main()
