"""Exercise new ONNX architectures through the existing frozen final wrapper.

Synthetic architecture fixtures and disjoint plumbing seeds only. No training,
HF job submission, final games, candidate selection or publication.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

from huggingface_hub import hf_hub_download
from strategic_collection import ROOT, read, write, digest
from policy_iteration_development import verify_report

STRONG = ROOT/'ai/strong'
OUT = ROOT/'ai/runs/policy-iteration-final-runtime-preflight-v2'


def archive_hashes(path):
    with tarfile.open(path) as bundle:
        return {member.name: hashlib.sha256(bundle.extractfile(member).read()).hexdigest()
                for member in bundle.getmembers() if member.isfile()}


def main():
    source = read(STRONG/'final-strategic-runtime-source-v1.json')
    development = read(STRONG/'policy-iteration-development-source-v2.json')
    architecture = read(ROOT/'ai/runs/policy-iteration-8840u-prepared-v2/manifest.json')
    assert architecture['source'] == development and architecture['synthetic_untrained']
    assert architecture['gradients'] is False and architecture['qualification_eligible'] is False
    final_protocol_sha = digest(STRONG/'final-protocol-multiplayer.json')
    protocol = read(STRONG/'policy-iteration-development-protocol-v2.json')
    assert protocol['final_protocol_sha256'] == final_protocol_sha
    # Only this local test's seed namespace differs from the development contract.
    protocol = {**protocol, 'plumbing_seed_template': 'policy-iteration-final-wrapper-plumbing-v2-{players}p'}
    before_ledger = digest(STRONG/'experiments.json')
    paths = {}
    for key, pin in [('final', source), ('development', development)]:
        paths[key] = Path(hf_hub_download('coyotte508/powergrid-ai-training-v1', pin['archive'],
            repo_type='dataset', revision=pin['revision']))
        assert digest(paths[key]) == pin['sha256']
    final_hashes, dev_hashes = archive_hashes(paths['final']), archive_hashes(paths['development'])
    common = set(final_hashes) & set(dev_hashes)
    changes = {name: {'final': final_hashes[name], 'development': dev_hashes[name]}
               for name in common if final_hashes[name] != dev_hashes[name]}
    # These are the provenance wrapper and non-ONNX training/packaging helpers.
    assert set(changes) == {'ai/strong/arena-job.py', 'ai/strong/collect-population-screen.py',
        'ai/strong/export-inference64.py', 'ai/strong/model.py', 'ai/strong/package-serving.py'}
    engine = {name for name in final_hashes if name.startswith('engine/')}
    assert engine == {name for name in dev_hashes if name.startswith('engine/')}
    assert all(final_hashes[name] == dev_hashes[name] for name in engine)
    required = ['ai/core.cjs', 'ai/infer.py', 'ai/strong/evaluate.py', 'ai/strong/infer.py',
        'ai/strong/bridge.cjs', 'ai/strong/worker.cjs', 'ai/strong/encoders.cjs',
        'ai/strong/features-v4_3.cjs', 'ai/strong/feature_contract.py', 'ai/strong/search.cjs',
        'ai/strong/search_scope.py', 'ai/strong/geographic-proposals.cjs', 'ai/pool.py', 'ai/strong/async_pool.py']
    assert all(final_hashes[name] == dev_hashes[name] for name in required)
    for name in ['arena-job.py', 'features-v4_3.cjs', 'encoders.cjs', 'evaluate.py']:
        assert final_hashes['ai/strong/'+name] == digest(STRONG/name)
    OUT.mkdir(exist_ok=False)
    runtime = OUT/'runtime'; runtime.mkdir()
    with tarfile.open(paths['final']) as bundle:
        bundle.extractall(runtime, filter='data')
    write(OUT/'source-comparison.json', {'final_source': source, 'development_source': development,
        'final_files': len(final_hashes), 'development_files': len(dev_hashes), 'common_files': len(common),
        'changed_files': changes, 'required_runtime_files': {name: final_hashes[name] for name in required},
        'engine_files_equal': len(engine), 'synthetic_untrained': True, 'qualification_eligible': False})
    write(OUT/'plumbing-protocol.json', protocol)
    # Exercise the actual wrapper's download, evaluator, engine and provenance.
    # Capture only its final artifact upload locally; there are no job launches.
    wrapper = '''
from pathlib import Path
import os,runpy,shutil
from unittest.mock import patch
from huggingface_hub import HfApi
def save(self, **kwargs):
    assert kwargs['repo_id']==os.environ['HF_MODEL_REPO']
    assert kwargs['path_in_repo']=='runs/'+os.environ['RUN_NAME']+'/evaluation.json'
    assert kwargs['path_or_fileobj']=='evaluation.json'
    shutil.copy2(kwargs['path_or_fileobj'],Path(os.environ['CHECK_OUTPUT'])/'evaluation.json')
with patch.object(HfApi,'upload_file',new=save):
    runpy.run_path('ai/strong/arena-job.py',run_name='__main__')
'''
    report = {'passed': False, 'source': source, 'development_source': development,
        'cases': {}, 'synthetic_untrained': True, 'training_verified': False,
        'gradients': False, 'reserved_final_seeds_used': False, 'candidate_selected': False,
        'qualification_eligible': False, 'final_protocol_sha256': final_protocol_sha,
        'scope': 'Four untrained ONNX architectures through the actual existing final wrapper, '
                 '2p/6p, all four rules, offset4, separate plumbing seeds. Compatibility only.'}
    try:
        assert set(architecture['models']) == {'frozen-0','frozen-1','public-0','public-1'}
        for key, item in architecture['models'].items():
            pin = item['pin']
            assert pin['synthetic_untrained'] and pin['training_verified'] is False
            for n in [2,6]:
                case = key+'-'+str(n)+'p'; directory = OUT/case; directory.mkdir()
                seed = protocol['plumbing_seed_template'].format(players=n)
                assert 'reserved' not in seed and seed != read(STRONG/'final-protocol-multiplayer.json')['seed_prefix']
                env = os.environ.copy()
                for name in ['OPPONENT_MODEL_PATH','OPPONENT_MODEL_REVISION','OPPONENT_MODEL_SHA256']:
                    env.pop(name, None)
                env.update(HF_MODEL_REPO=pin['repo'], MODEL_PATH=pin['prefix']+'/inference64.onnx',
                    MODEL_REVISION=pin['revision'], MODEL_SHA256=pin['files']['inference64.onnx'],
                    SOURCE_ARCHIVE=source['archive'], SOURCE_REVISION=source['revision'], SOURCE_SHA256=source['sha256'],
                    PLAYER_COUNT=str(n), DEAL_OFFSET='4', OPPONENT='economic', GAMES=str(4*n), WORKERS='24',
                    EVAL_SEED=seed, RUN_NAME='policy-iteration-final-wrapper-plumbing-v2-'+case,
                    SEARCH_SCOPE='all', SEARCH_SAMPLES='0', GEOGRAPHY='0', ASYNC_ARENA='0',
                    DISABLE_SEARCH_PROPOSAL='0', CHECK_OUTPUT=str(directory))
                with (directory/'wrapper.log').open('x') as log:
                    subprocess.run([sys.executable,'-c',wrapper],cwd=runtime,env=env,
                        stdout=log,stderr=subprocess.STDOUT,check=True)
                result = read(directory/'evaluation.json')
                summary = verify_report(result, protocol, pin, n, 'economic', 4, 5, 'plumbing')
                assert result['source'] == {name:source[name] for name in ['archive','revision','sha256']}
                assert result['arena_runner_sha256'] == source['arena_runner_sha256']
                assert result['model_repository_revision'] == pin['revision']
                assert result['opponent_repository_revision'] is None
                assert result['run_name'] == env['RUN_NAME'] and result['async_rollout'] is False
                report['cases'][case] = {'model_pin': pin, 'summary': summary,
                    'evaluation_sha256': digest(directory/'evaluation.json')}
                print({'case':case,'games':summary['games'],'provenance_verified':True},flush=True)
        assert all(digest(runtime/name)==sha for name,sha in final_hashes.items())
        assert digest(STRONG/'final-protocol-multiplayer.json') == final_protocol_sha
        assert digest(STRONG/'experiments.json') == before_ledger
        report.update(passed=True,games=sum(item['summary']['games'] for item in report['cases'].values()))
        assert report['games']==128
    finally:
        write(OUT/'check.json',report)
        write(STRONG/'policy-iteration-final-runtime-preflight-v2.json',report)
    print({'passed':report['passed'],'games':report['games'],'reserved_final_seeds_used':False},flush=True)


if __name__ == '__main__':
    main()
