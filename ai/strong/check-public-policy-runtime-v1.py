"""Verify standalone transport against saved, audited policy decisions.

No gradients, fresh strength games, reserved seeds or job submissions.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'ai/runs/public-policy-runtime-preflight-v1'
BASE = ROOT/'ai/runs/population-policy-8840u-prepared-v2/package'
REFERENCE = ROOT/'ai/runs/population-policy-local-reference-v2'
ENTRY = 'ai/strong/public_policy_runtime_v1.py'


def read(path):
    return json.loads(Path(path).read_text())


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')


def semantic(value):
    if isinstance(value, dict):
        return {k: semantic(v) for k, v in value.items() if k != 'elapsedMs'}
    if isinstance(value, list):
        return [semantic(v) for v in value]
    return value


def prepare():
    assert not OUT.exists(), 'Inspect the original preflight before retrying'
    old = read(BASE/'manifest.json')
    assert all(digest(BASE/name) == sha for name, sha in old['files'].items())
    reference = read(REFERENCE/'status.json')
    assert reference['passed'] and reference['manifest_sha256'] == digest(BASE/'manifest.json')
    assert all(digest(REFERENCE/name) == sha for name, sha in reference['output_hashes'].items())
    package = OUT/'package'; package.mkdir(parents=True)
    copied = {}
    for name, sha in old['files'].items():
        if name.startswith(('engine/', 'ai/')) or name == 'policy.onnx':
            destination = package/name; destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(BASE/name, destination); copied[name] = sha
    destination = package/ENTRY
    assert not destination.exists()
    shutil.copy2(ROOT/ENTRY, destination)
    manifest = {**copied, ENTRY: digest(destination)}
    assert all(digest(package/name) == sha for name, sha in manifest.items())
    write(package/'manifest.json', manifest)
    descriptors = {}
    for arm, threads, workers in [('model', 1, 1), ('filter', 1, 1), ('combined', 1, 1), ('combined', 4, 4)]:
        name = f'{arm}-{threads}-{workers}.json'
        descriptor = {'version': 1, 'backend': 'population-v1', 'feature_revision': '4.3-strategic-correction',
                      'model': {'path': 'policy.onnx', 'sha256': manifest['policy.onnx']},
                      'runtime_manifest': {'path': 'manifest.json', 'sha256': digest(package/'manifest.json')},
                      'settings': {'arm': arm, 'samples': 8, 'workers': workers, 'threads': threads, 'max_steps': 2400}}
        write(package/name, descriptor); descriptors[name] = digest(package/name)
    shutil.copy2(package/'filter-1-1.json', package/'policy.json')
    write(OUT/'prepared.json', {'base_manifest_sha256': digest(BASE/'manifest.json'),
          'reference_status_sha256': digest(REFERENCE/'status.json'), 'unchanged_runtime_files': len(copied),
          'entry_sha256': digest(destination), 'manifest_sha256': digest(package/'manifest.json'),
          'descriptors': descriptors, 'fixtures_sha256': digest(BASE/'fixtures.jsonl'),
          'selected_fixtures_sha256': digest(BASE/'selected-fixtures.json'),
          'checker_sha256': digest(__file__), 'qualification_eligible': False})
    with (OUT/'verify.log').open('x') as log:
        subprocess.run([sys.executable, '-u', '-B', str(Path(__file__).resolve()), 'verify'],
                       cwd='/tmp', stdout=log, stderr=subprocess.STDOUT, check=True,
                       env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
    print({k: read(OUT/'result.json')[k] for k in ('complete', 'model_filter_positions', 'search_cases', 'caps')})


def verify():
    package = OUT/'package'; prepared = read(OUT/'prepared.json')
    assert prepared['checker_sha256'] == digest(__file__)
    assert prepared['entry_sha256'] == digest(package/ENTRY) == digest(ROOT/ENTRY)
    assert prepared['manifest_sha256'] == digest(package/'manifest.json')
    assert prepared['reference_status_sha256'] == digest(REFERENCE/'status.json')
    assert all(digest(REFERENCE/name) == sha for name, sha in read(REFERENCE/'status.json')['output_hashes'].items())
    before_protocol = digest(ROOT/'ai/strong/final-protocol-multiplayer.json')
    before_ledger = digest(ROOT/'ai/strong/experiments.json')
    fixtures = [json.loads(line) for line in (BASE/'fixtures.jsonl').read_text().splitlines()]
    expected = [json.loads(line) for line in (REFERENCE/'model-filter.jsonl').read_text().splitlines()]
    assert len(fixtures) == len(expected) == 2553
    sys.path.insert(0, str(package/'ai/strong'))
    from public_policy_runtime_v1 import PublicPolicyService, load_artifact, encode
    services = []
    counts = {'model_filter_positions': 0, 'search_cases': 0, 'search_rollouts': 0, 'caps': 0,
              'warm_repeats': 0, 'cold_repeats': 0}
    by_count = {str(n): 0 for n in range(2, 7)}
    began = time.perf_counter()
    def check(response, fixture, reference):
        assert 'error' not in response, response
        q = fixture['request']; n = len(q['state']['players'])
        assert response['requestId'] == q['requestId'] and response['revision'] == q['revision']
        assert response['playerOrder'] == [(q['player']+i) % n for i in range(n)]
        assert response['move'] == fixture['legal'][response['decision']['index']]
        assert semantic(response['decision']) == semantic(reference)
        assert response['qualification_eligible'] is False and 'winProbabilities' not in response
        assert response['modelSha256'] == reference['modelSha256']
        assert response['featureRevision'] == reference['featureRevision']
    try:
        services = [PublicPolicyService(lambda arm=arm: load_artifact(package, f'{arm}-1-1.json')) for arm in ('model', 'filter')]
        with (OUT/'model-filter.jsonl').open('x') as stream:
            for i, (fixture, gold) in enumerate(zip(fixtures, expected)):
                assert gold['index'] == i and gold['requestId'] == fixture['request']['requestId']
                for arm, service in zip(('model', 'filter'), services):
                    response = service.decide(fixture['request'], diagnostics=True)
                    check(response, fixture, gold['results'][arm])
                    assert response['policySha256'] == prepared['descriptors'][f'{arm}-1-1.json']
                    stream.write(encode({'index': i, 'arm': arm, 'response': response})+'\n')
                    counts['model_filter_positions'] += 1
                    by_count[str(len(fixture['request']['state']['players']))] += 1
        print({'model_filter_positions': counts['model_filter_positions'], 'by_player_count': by_count}, flush=True)
        repeats = [next(i for i, row in enumerate(fixtures) if len(row['request']['state']['players']) == n) for n in range(2, 7)]
        for index in reversed(repeats):
            fixture = fixtures[index]
            for arm, service in zip(('model', 'filter'), services):
                check(service.decide(fixture['request'], diagnostics=True), fixture, expected[index]['results'][arm])
                counts['warm_repeats'] += 1
        for service in services:
            service.close()
        services = []
        for index in repeats:
            service = PublicPolicyService(lambda: load_artifact(package, 'filter-1-1.json')); services = [service]
            check(service.decide(fixtures[index]['request'], diagnostics=True), fixtures[index], expected[index]['results']['filter'])
            counts['cold_repeats'] += 1; service.close(); services = []
        selected = read(BASE/'selected-fixtures.json')
        searches = [json.loads(line) for line in (REFERENCE/'search.jsonl').read_text().splitlines()]
        with (OUT/'search.jsonl').open('x') as stream:
            for threads, workers in [(1, 1), (4, 4)]:
                descriptor = f'combined-{threads}-{workers}.json'
                service = PublicPolicyService(lambda descriptor=descriptor: load_artifact(package, descriptor)); services = [service]
                for gold in [row for row in searches if row['threads'] == threads and row['workers'] == workers]:
                    fixture = selected[gold['fixture']]['fixture']
                    response = service.decide(fixture['request'], diagnostics=True)
                    check(response, fixture, gold['result'])
                    search = response['decision']['search']; assert search['usable'] and search['truncated'] == 0
                    counts['search_cases'] += 1; counts['search_rollouts'] += search['evaluations']; counts['caps'] += search['truncated']
                    stream.write(encode({'fixture': gold['fixture'], 'threads': threads, 'workers': workers, 'response': response})+'\n'); stream.flush()
                    print({'fixture': gold['fixture'], 'threads': threads, 'workers': workers, 'seconds': response['elapsedMs']/1000}, flush=True)
                service.close(); services = []
        # Actual JSON-lines process: errors retain request metadata and a later
        # valid request still reproduces the same move, even after engine failure.
        q = fixtures[repeats[-1]]['request']
        broken = {'requestId': 'bad-state', 'revision': 4, 'player': 0, 'state': {'players': [{}, {}]}}
        lines = [encode(q), '[]', '{"requestId":1e999}', encode(broken), encode(q)]
        completed = subprocess.run([sys.executable, '-u', '-B', str(package/ENTRY), str(package), '--diagnostics'],
                                   input='\n'.join(lines)+'\n', text=True, capture_output=True, check=True, cwd='/tmp')
        (OUT/'cli.stderr.log').write_text(completed.stderr)
        responses = [json.loads(line) for line in completed.stdout.splitlines()]; assert len(responses) == len(lines)
        for index in (0, 4):
            check(responses[index], fixtures[repeats[-1]], expected[repeats[-1]]['results']['filter'])
        assert all('error' in responses[index] for index in (1, 2, 3))
        assert responses[3]['requestId'] == 'bad-state' and responses[3]['revision'] == 4
        write(OUT/'cli-responses.json', responses)
        bad = read(package/'policy.json'); bad['runtime_manifest']['sha256'] = '0'*64
        write(package/'bad-descriptor.json', bad)
        bad_run = subprocess.run([sys.executable, '-u', '-B', str(package/ENTRY), str(package), '--descriptor', 'bad-descriptor.json'],
                                 input=encode(q)+'\n', text=True, capture_output=True, check=True, cwd='/tmp')
        bad_response = json.loads(bad_run.stdout); assert 'Artifact pin mismatch' in bad_response['error']
        write(OUT/'bad-artifact-response.json', bad_response)
        assert all(digest(package/name) == sha for name, sha in read(package/'manifest.json').items())
        assert before_protocol == digest(ROOT/'ai/strong/final-protocol-multiplayer.json')
        assert before_ledger == digest(ROOT/'ai/strong/experiments.json')
        assert counts['model_filter_positions'] == 5106 and counts['search_cases'] == 8 and counts['caps'] == 0
        result = {'complete': True, 'checked_at': datetime.now(timezone.utc).isoformat(), **counts,
                  'by_player_count': by_count, 'standalone_cli_requests': len(lines), 'invalid_artifact_rejected': True,
                  'manifest_sha256': prepared['manifest_sha256'], 'prepared_sha256': digest(OUT/'prepared.json'),
                  'entry_sha256': prepared['entry_sha256'], 'checker_sha256': digest(__file__),
                  'reference_status_sha256': prepared['reference_status_sha256'], 'seconds': time.perf_counter()-began,
                  'new_hf_jobs': 0, 'new_strength_games': 0, 'gradients': False, 'qualification_eligible': False,
                  'reserved_final_seeds_used': False,
                  'scope': 'Standalone transport parity for current research population policies, including exact saved search outcomes. Not a selected-policy final adapter or AMD benchmark.'}
        result['output_hashes'] = {p.name: digest(p) for p in OUT.iterdir() if p.is_file() and p.name not in ('result.json', 'verify.log')}
        write(OUT/'result.json', result)
    finally:
        for service in services:
            service.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__); parser.add_argument('operation', choices=['prepare', 'verify'])
    globals()[parser.parse_args().operation]()
