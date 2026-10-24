"""Package and benchmark all four verified trained ensembles on the actual 8840U.

Explicit stages only: no background coordinator, jobs, gradients, retries,
model selection, final games or publication. The synthetic benchmark is separate.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
from datetime import datetime, timezone

import numpy as np
from huggingface_hub import hf_hub_download
from strategic_collection import ROOT, read, write, digest
from policy_iteration_evidence_archive import upload_evidence

STRONG = ROOT/'ai/strong'
RUNS = ROOT/'ai/runs'
PREPARED = RUNS/'policy-iteration-trained-8840u-prepared-v2'
OUTPUT = RUNS/'policy-iteration-trained-8840u-results-v2'
GUARD = STRONG/'policy-iteration-trained-8840u-launch-v2.json'
UPSTREAM = RUNS/'policy-iteration-training-harvest-v2/state.json'
REMOTE = '/home/coyotte508/powergrid-ai-policy-iteration-trained-v2'
MODELS = ['frozen-0', 'frozen-1', 'public-0', 'public-1']
SCOPE = ('Exact trained standalone ensembles, all 2553 public serving fixtures each, '
         'on the actual AMD8840U. Sequential engineering timing and legal-move/runtime '
         'parity only; no strength, calibration, browser or production claim.')


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def require_trained_handoff(state):
    assert state['stage'] == 'both_heads_verified_and_archived', 'Actual trained outputs are not ready'
    assert state['execute'] and state['local_gradients'] is False
    assert state['qualification_eligible'] is False and state['reserved_final_seeds_used'] is False
    assert set(state['heads_verified']) == {'frozen', 'public'}
    jobs = set()
    for head, evidence in state['heads_verified'].items():
        assert evidence['head_type'] == head and evidence['remote_archive_verified']
        assert evidence['local_gradients'] is False and evidence['qualification_eligible'] is False
        assert evidence['job_id'] not in jobs
        jobs.add(evidence['job_id'])
        assert set(evidence['candidate_pins']) == {head+'-0', head+'-1'}
        for key, item in evidence['candidate_pins'].items():
            pin = item['pin']
            assert pin['key'] == key and pin['training_verified'] is True
            assert not pin.get('synthetic_untrained', False)
            assert pin['training_verified_sha256'] == evidence['verified_sha256']
            assert pin['qualification_eligible'] is False


def admit():
    state = read(UPSTREAM)
    require_trained_handoff(state)
    harvest = module('trained_8840u_admission', STRONG/'harvest-policy-iteration-training.py')
    harvest.check_code(state['code_hashes'])
    training = read(harvest.UPSTREAM)
    assert harvest.upstream_ready(training)
    design, data_pin, training_source = harvest.admission()
    pins, evidence = {}, {}
    for head in harvest.HEADS:
        guard = read(harvest.GUARDS/(head+'.json'))
        harvest.guard_matches(guard, head, training, design, data_pin, training_source)
        record, verified_pins = harvest.verify_outputs(head, guard, data_pin, training_source)
        proof = state['heads_verified'][head]
        assert proof['job_id'] == guard['job_id'] and proof['candidate_pins'] == verified_pins
        assert proof['verified_sha256'] == digest(harvest.VERIFIED/head/'verified.json')
        assert proof['training_artifact_revision'] == record['revision']
        assert proof['training_artifact_prefix'] == record['prefix']
        pins.update({key: item['pin'] for key, item in verified_pins.items()})
        evidence[head] = proof
    assert set(pins) == set(MODELS)
    source = read(STRONG/'policy-iteration-development-source-v2.json')
    preflight = read(STRONG/'policy-iteration-development-preflight-v2.json')
    assert preflight['passed'] and preflight['source'] == source
    return pins, evidence, source


def copied_files():
    strong = ['infer.py', 'worker.cjs', 'encoders.cjs', 'feature_contract.py', 'search_scope.py',
              'features.cjs', 'features-v3_0.cjs', 'features-v4.cjs', 'features-v4_1.cjs',
              'features-v4_1_control.cjs', 'features-v4_2.cjs', 'features-v4_3.cjs',
              'economics.cjs', 'economics-v3_0.cjs', 'economics-v4_1.cjs', 'spatial.cjs',
              'public-graph.cjs', 'geographic-proposals.cjs', 'search.cjs']
    return ['ai/core.cjs', 'ai/infer.py'] + ['ai/strong/'+name for name in strong]


def prepare():
    pins, evidence, source = admit()  # Reject unfinished/synthetic outputs before creating anything.
    PREPARED.mkdir(exist_ok=False)
    archive = hf_hub_download('coyotte508/powergrid-ai-training-v1', source['archive'],
                              repo_type='dataset', revision=source['revision'])
    assert digest(archive) == source['sha256']
    runtime = PREPARED/'frozen-source'
    runtime.mkdir()
    with tarfile.open(archive) as bundle:
        bundle.extractall(runtime, filter='data')
    models = {}
    for key in MODELS:
        pin = pins[key]
        model = hf_hub_download(pin['repo'], pin['prefix']+'/inference64.onnx', revision=pin['revision'])
        assert digest(model) == pin['files']['inference64.onnx']
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp)
            shutil.copytree(runtime/'engine', package/'engine')
            for name in copied_files():
                target = package/name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(runtime/name, target)
            shutil.copy2(ROOT/'ai/requirements-serve.txt', package/'ai/requirements-serve.txt')
            shutil.copy2(model, package/'policy.onnx')
            (package/'serve.py').write_text('''import hashlib,json,os,sys
from pathlib import Path
root=Path(__file__).resolve().parent
assert len(sys.argv)==1
manifest=json.loads((root/'manifest.json').read_text())
model=root/'policy.onnx'
assert hashlib.sha256(model.read_bytes()).hexdigest()==manifest['model_sha256']
os.execv(sys.executable,[sys.executable,str(root/'ai/strong/infer.py'),str(model),'--search-samples','0','--search-scope','all'])
''')
            (package/'START.txt').write_text('Trained Powergrid research ensemble. Strength is unqualified. '
                'Run serve.py with JSONL requests on stdin; requires Node24, Python3.11/3.12 '
                'and ai/requirements-serve.txt. Player money is public input. Values remain '
                'uncalibrated-training-opponents. Not production routing.\n')
            package_manifest = {'model_sha256': digest(model), 'model_repository_revision': pin['revision'],
                'model_pin': pin, 'feature_revision': pin['feature_revision'], 'schema': 4,
                'source': source, 'synthetic_untrained': False, 'training_verified': True,
                'qualification_eligible': False, 'search_samples': 0, 'geographic_search': False,
                'search_scope': 'all', 'files': {str(p.relative_to(package)): digest(p)
                    for p in package.rglob('*') if p.is_file()}}
            for name, sha in package_manifest['files'].items():
                if name.startswith('engine/') or name in copied_files():
                    assert digest(runtime/name) == sha
            write(package/'manifest.json', package_manifest)
            shutil.copy2(package/'manifest.json', PREPARED/(key+'-package-manifest.json'))
            with tarfile.open(PREPARED/(key+'.tgz'), 'w:gz') as bundle:
                for path in sorted(package.rglob('*')):
                    if path.is_file():
                        bundle.add(path, arcname=str(path.relative_to(package)))
            models[key] = {'pin': pin, 'package_sha256': digest(PREPARED/(key+'.tgz')),
                          'package_manifest_sha256': digest(package/'manifest.json')}
    for name in ['probe-strategic-packages-8840u.py', 'probe-search-transfer-8840u.py']:
        shutil.copy2(STRONG/name, PREPARED/name)
    shutil.copy2(runtime/'ai/strong/fixtures/multiplayer-serving-v1.jsonl', PREPARED/'fixtures.jsonl')
    dependencies = [Path(__file__), STRONG/'verify-package.py', ROOT/'ai/requirements-serve.txt']
    runtime_files = [runtime/name for name in copied_files()]
    runtime_files += [p for p in (runtime/'engine').rglob('*') if p.is_file()]
    runtime_files.append(runtime/'ai/strong/fixtures/multiplayer-serving-v1.jsonl')
    manifest = {'models': models, 'source': source, 'trained_evidence': evidence,
        'synthetic_untrained': False, 'training_verified': True, 'gradients': False,
        'qualification_eligible': False, 'scope': SCOPE,
        'harness_sha256': digest(PREPARED/'probe-strategic-packages-8840u.py'),
        'helper_sha256': digest(PREPARED/'probe-search-transfer-8840u.py'),
        'fixtures_sha256': digest(PREPARED/'fixtures.jsonl'),
        'runtime_hashes': {str(p.relative_to(runtime)): digest(p) for p in runtime_files},
        'code_hashes': {str(p.relative_to(ROOT)): digest(p) for p in dependencies}}
    write(PREPARED/'manifest.json', manifest)
    print({'stage': 'prepared', 'models': len(models), 'training_verified': True}, flush=True)


def prepared_manifest():
    pins, evidence, source = admit()
    manifest = read(PREPARED/'manifest.json')
    assert manifest['training_verified'] and manifest['synthetic_untrained'] is False
    assert manifest['gradients'] is False and manifest['qualification_eligible'] is False
    assert manifest['source'] == source and manifest['trained_evidence'] == evidence
    assert manifest['scope'] == SCOPE and set(manifest['models']) == set(MODELS)
    for name, sha in manifest['code_hashes'].items():
        assert digest(ROOT/name) == sha, 'Benchmark code changed; inspect before proceeding'
    assert set(copied_files()) <= set(manifest['runtime_hashes'])
    for name, sha in manifest['runtime_hashes'].items():
        assert digest(PREPARED/'frozen-source'/name) == sha, 'Frozen inference runtime changed'
    for name, field in [('probe-strategic-packages-8840u.py', 'harness_sha256'),
                        ('probe-search-transfer-8840u.py', 'helper_sha256'),
                        ('fixtures.jsonl', 'fixtures_sha256')]:
        assert digest(PREPARED/name) == manifest[field]
    for key, item in manifest['models'].items():
        assert item['pin'] == pins[key]
        assert digest(PREPARED/(key+'.tgz')) == item['package_sha256']
        assert digest(PREPARED/(key+'-package-manifest.json')) == item['package_manifest_sha256']
    return manifest


def run():
    assert not GUARD.exists(), 'Inspect the recorded target process; do not retry a launch'
    manifest = prepared_manifest()
    for key in MODELS:
        package = PREPARED/('local-package-'+key)
        package.mkdir(exist_ok=False)
        with tarfile.open(PREPARED/(key+'.tgz')) as bundle:
            bundle.extractall(package, filter='data')
        with (PREPARED/(key+'-local-check.log')).open('x') as log:
            subprocess.run([sys.executable, str(STRONG/'verify-package.py'), str(package),
                str(PREPARED/'fixtures.jsonl'), '--output', str(PREPARED/(key+'-local-check.json'))],
                cwd='/', stdout=log, stderr=subprocess.STDOUT, check=True)
        check = read(PREPARED/(key+'-local-check.json'))
        assert check['all_hashes_match'] and check['all_moves_legal']
        assert check['player_counts'] == [2,3,4,5,6]
    record = {'host': 'minipc', 'directory': REMOTE, 'stage': 'launch_intent',
        'created_at': datetime.now(timezone.utc).isoformat(), 'manifest_sha256': digest(PREPARED/'manifest.json'),
        'synthetic_untrained': False, 'training_verified': True, 'gradients': False, 'qualification_eligible': False}
    with GUARD.open('x') as stream:
        json.dump(record, stream, indent=2)
    try:
        subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', 'minipc', 'mkdir '+REMOTE], check=True)
        names = ['manifest.json', 'fixtures.jsonl', 'probe-strategic-packages-8840u.py',
                 'probe-search-transfer-8840u.py'] + [key+'.tgz' for key in MODELS]
        subprocess.run(['scp', '-q', *[str(PREPARED/name) for name in names], 'minipc:'+REMOTE+'/'], check=True)
        record['stage'] = 'running'
        write(GUARD, record)
        command = (f'cd {REMOTE}\necho $$ > process.pid\nexec '
            '/home/coyotte508/powergrid-ai-baseline/.venv/bin/python -u '
            'probe-strategic-packages-8840u.py > run.log 2>&1')
        result = subprocess.run(['ssh', '-o', 'BatchMode=yes', 'minipc', command])
        record.update(stage='completed' if result.returncode == 0 else 'observation_or_process_error',
                      returncode=result.returncode)
        result.check_returncode()
    except BaseException as error:
        if record['stage'] != 'observation_or_process_error':
            record['stage'] = 'launch_or_observation_unknown'
        record['error'] = type(error).__name__+': '+str(error)
        raise
    finally:
        write(GUARD, record)
    print({'stage': 'completed', 'target': 'minipc', 'requests': 10212}, flush=True)


def collect():
    manifest = prepared_manifest()
    guard = read(GUARD)
    assert guard['stage'] == 'completed' and guard['returncode'] == 0
    assert guard['host'] == 'minipc' and guard['directory'] == REMOTE
    assert guard['manifest_sha256'] == digest(PREPARED/'manifest.json')
    OUTPUT.mkdir(exist_ok=False)
    names = ['manifest.json', 'fixtures.jsonl', 'machine.json', 'results.json', 'process.pid', 'run.log']
    names += [key+suffix for key in MODELS for suffix in ['.jsonl', '.stderr']]
    subprocess.run(['scp', '-q', *['minipc:'+REMOTE+'/'+name for name in names], str(OUTPUT)+'/'], check=True)
    assert digest(OUTPUT/'manifest.json') == guard['manifest_sha256']
    assert digest(OUTPUT/'fixtures.jsonl') == manifest['fixtures_sha256']
    helpers = module('trained_target_helpers', PREPARED/'probe-search-transfer-8840u.py')
    machine, saved = read(OUTPUT/'machine.json'), read(OUTPUT/'results.json')
    assert '8840U' in machine['processor'] and saved['machine'] == machine
    assert saved['qualification_eligible'] is False and saved['scope'] == SCOPE
    assert set(saved['models']) == set(MODELS)
    fixtures = [json.loads(line) for line in (PREPARED/'fixtures.jsonl').open()]
    models = {}
    for key in MODELS:
        item = manifest['models'][key]
        rows = [json.loads(line) for line in (OUTPUT/(key+'.jsonl')).open()]
        assert len(rows) == len(fixtures) == 2553
        assert [row['fixture_index'] for row in rows] == list(range(2553))
        model = PREPARED/('local-package-'+key)/'policy.onnx'
        assert digest(model) == item['pin']['files']['inference64.onnx']
        worker = subprocess.Popen([sys.executable, str(PREPARED/'frozen-source/ai/strong/infer.py'),
            str(model), '--search-samples', '0', '--search-scope', 'all'], cwd='/',
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
        maximum_difference = 0
        try:
            for row, fixture in zip(rows, fixtures):
                game, result = fixture['request']['state'], row['response']
                helpers.validate(fixture, result, item['pin'])
                assert result['search'] is None
                assert row['players'] == len(game['players']) and row['phase'] == game['phase']
                assert row['rule'] == game['options']['variant']+('/sealed' if game['options'].get('fastBid') else '/open')
                assert np.isfinite(row['roundtrip_ms']) and row['roundtrip_ms'] > 0
                assert np.isfinite(result['elapsedMs']) and 0 <= result['elapsedMs'] <= row['roundtrip_ms']
                worker.stdin.write(json.dumps(fixture['request'])+'\n'); worker.stdin.flush()
                reference = json.loads(worker.stdout.readline())
                helpers.validate(fixture, reference, item['pin'])
                assert result['move'] == reference['move'], (key, row['fixture_index'])
                difference = max(abs(x-y) for x,y in zip(result['winProbabilities'], reference['winProbabilities']))
                assert difference < 1e-6
                maximum_difference = max(maximum_difference, difference)
        finally:
            worker.stdin.close(); worker.wait(timeout=10); worker.stdout.close()
        assert worker.returncode == 0
        summary = helpers.summarize(rows)
        assert summary == saved['models'][key]
        models[key] = {'summary': summary, 'model_pin': item['pin'], 'all_frozen_runtime_moves_identical': True,
                       'maximum_value_difference': maximum_difference, 'package_sha256': item['package_sha256']}
        print({'model': key, 'positions': len(rows), 'warm': summary['warm'], 'identical_moves': True}, flush=True)
    report = {'verified': True, 'machine': machine, 'models': models, 'requests': 10212,
        'source': manifest['source'], 'manifest_sha256': guard['manifest_sha256'], 'training_verified': True,
        'synthetic_untrained': False, 'gradients': False, 'qualification_eligible': False, 'candidate_selected': False,
        'scope': SCOPE, 'artifacts': {p.name: digest(p) for p in OUTPUT.iterdir() if p.is_file()}}
    write(OUTPUT/'verified.json', report)
    write(STRONG/'policy-iteration-trained-8840u-results-v2.json', report)


def archive_results():
    manifest = prepared_manifest()
    report = read(OUTPUT/'verified.json')
    assert report['verified'] and report['training_verified'] and report['synthetic_untrained'] is False
    assert report['requests'] == 10212 and report['manifest_sha256'] == digest(PREPARED/'manifest.json')
    assert report['gradients'] is False and report['qualification_eligible'] is False
    for name, sha in report['artifacts'].items():
        assert digest(OUTPUT/name) == sha
    out = RUNS/'policy-iteration-trained-8840u-evidence-v2'
    out.mkdir(exist_ok=False)
    shutil.copytree(OUTPUT, out/'results')
    for key in MODELS:
        for suffix in ['.tgz', '-package-manifest.json', '-local-check.json', '-local-check.log']:
            shutil.copy2(PREPARED/(key+suffix), out/(key+suffix))
    for name in ['manifest.json', 'probe-strategic-packages-8840u.py', 'probe-search-transfer-8840u.py']:
        shutil.copy2(PREPARED/name, out/('prepared-'+name))
    shutil.copy2(Path(__file__), out/Path(__file__).name)
    shutil.copy2(STRONG/'verify-package.py', out/'verify-package.py')
    shutil.copy2(GUARD, out/'launch-guard.json')
    write(out/'manifest.json', {str(p.relative_to(out)): digest(p) for p in out.rglob('*') if p.is_file()})
    evidence = {**upload_evidence(out), 'requests': 10212, 'models': MODELS,
        'prepared_manifest_sha256': digest(PREPARED/'manifest.json'), 'training_verified': True,
        'synthetic_untrained': False, 'gradients': False, 'qualification_eligible': False, 'scope': manifest['scope']}
    write(STRONG/'policy-iteration-trained-8840u-evidence-v2.json', evidence)
    print(evidence, flush=True)


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('stage', choices=['check', 'prepare', 'run', 'collect', 'archive'])
    args = parser.parse_args()
    if args.stage == 'check':
        state = read(UPSTREAM)
        ready = state['stage'] == 'both_heads_verified_and_archived'
        if ready:
            admit()
        print({'ready': ready, 'upstream_stage': state['stage'], 'local_gradients': False,
               'target_process_started': False, 'qualification_eligible': False}, flush=True)
    else:
        {'prepare': prepare, 'run': run, 'collect': collect, 'archive': archive_results}[args.stage]()


if __name__ == '__main__':
    main()
