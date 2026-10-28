"""Verify stateless public-history anchors on existing complete resource turns.

No inference, future continuations, new game trajectories, HF jobs or selection.
"""
from collections import Counter
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

from public_policy_development_job_v1 import read, digest

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT/'ai/runs/resource-replanning-job-source-prepared-v1/layout'
RUNTIME_SHA = 'cebda6cb0ed6a1eff28cad8cd02cb17e37bb62f59595b2237b989337b40a9415'
FULL = ROOT/'ai/runs/resource-turn-full-integration-v2'
FULL_SHA = '7899bc2d35afb3d7486bd9940e4cc17245b0f516b6a7f46ccecbfc17e19d4650'
PRIOR = ROOT/'ai/runs/resource-replanning-development-collected-v1'
ARCHIVE = ROOT/'ai/runs/resource-replanning-development-complete-evidence-v1/manifest.json'
ARCHIVE_SHA = 'fb4cab7da560d86fe1bad88a363c9e83d3bb0aa86344de12368317dc95ae1839'
ROOT_FILES = {
    'resource-turn-full-integration-v1': '0451d6e1189a9c0008386efc13cbcff0d54ab28290a521b19f42fb243b86f227',
    'resource-turn-full-integration-recovered-v1': '61e59190b8084292d757e06febe9a6fa847a183bf6ce1fc80c71bab5ec77b40a',
}
OUT = ROOT/'ai/runs/resource-turn-anchor-v1'
RESULT = ROOT/'ai/strong/resource-turn-anchor-results-v1.json'
PASS = {'name': 'Pass', 'data': True}


def write(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def main():
    assert not OUT.exists() and not RESULT.exists(), 'Inspect existing outcome before retrying'
    assert digest(RUNTIME/'resource-job-manifest.json') == RUNTIME_SHA
    runtime = read(RUNTIME/'resource-job-manifest.json')
    assert all(digest(RUNTIME/name) == sha for name, sha in runtime.items())
    sys.path.insert(0, str(RUNTIME/'ai/strong'))
    from hybrid_search import public_seed
    assert digest(Path(sys.modules['hybrid_search'].__file__)) == runtime['ai/strong/hybrid_search.py']
    assert digest(FULL/'assessment.json') == FULL_SHA
    full = read(FULL/'assessment.json'); assert full['passed'] and full['public_input_turns'] == 334
    inputs = {str((FULL/'assessment.json').relative_to(ROOT)): FULL_SHA}
    cases = []
    for path in sorted(FULL.glob('model-turn-*/decisions-*.jsonl')):
        sha = digest(path); assert sha == full['output_hashes'][str(path.relative_to(FULL))]
        inputs[str(path.relative_to(ROOT))] = sha
        for line in path.read_text().splitlines():
            row = json.loads(line)
            if row['request']['state']['phase'] == 'Resources':
                cases.append({'source': str(path.relative_to(ROOT)), 'family': 'corrected-model',
                    'request': row['request'], 'actions': row['executedActions']})
    assert len(cases) == 334
    assert digest(ARCHIVE) == ARCHIVE_SHA; archive = read(ARCHIVE)
    inputs[str(ARCHIVE.relative_to(ROOT))] = ARCHIVE_SHA
    search_roots = []
    for name, sha in ROOT_FILES.items():
        path = ROOT/'ai/runs'/name/'search-roots.jsonl'; assert digest(path) == sha
        inputs[str(path.relative_to(ROOT))] = sha
        search_roots.extend(json.loads(line) for line in path.read_text().splitlines())
    assert [(r['players'], r['episode']) for r in search_roots] == [(n, e) for n in range(2, 7) for e in range(4)]
    for root in search_roots:
        n, episode = root['players'], root['episode']
        path = PRIOR/f'resource-replanning-development-v1-resource-filter-{n}p-economic-0-4/artifacts/evaluation/decisions-{episode}.jsonl'
        sha = digest(path); assert archive[str(path.relative_to(ROOT))] == sha
        inputs[str(path.relative_to(ROOT))] = sha
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        first = root['recorded_atomic_decision']; start = first['decision'] - 1
        assert rows[start] == first
        actions = []; recorded = []
        for row in rows[start:]:
            assert row['round'] == first['round']
            actions.append(row['move']); recorded.append(row['resourcePlan']['search']['seed'] if row['resourcePlan'] else None)
            if row['move'] == PASS:
                break
        assert actions[-1] == PASS
        cases.append({'source': str(path.relative_to(ROOT)), 'family': 'historical-atomic-search',
            'request': root['request'], 'actions': actions, 'recorded_seeds': recorded})
    assert len(cases) == 354
    OUT.mkdir(); (OUT/'sources').mkdir()
    code = {}
    for name in ('check-resource-turn-anchor-v1.py', 'check-resource-turn-anchor-v1.cjs', 'resource-turn-anchor-v1.cjs'):
        path = ROOT/'ai/strong'/name; code[str(path.relative_to(ROOT))] = digest(path)
        shutil.copy2(path, OUT/'sources'/name)
    write(OUT/'design.json', {
        'selection': 'All 334 resource turns in the already selected 33 corrected-model games, plus the 20 previously selected atomic-search turns. No selection by wins or plan changes.',
        'cases': len(cases), 'samples_per_position': 8, 'input_hashes': inputs, 'code_hashes': code,
        'runtime_manifest_sha256': RUNTIME_SHA,
        'controls': ['exact actual first-decision observation/menu', 'historical state-dependent seeds',
            'fresh anchor instance per request', 'private field and request-ID pollution',
            'duplicate and reverse-ordered requests', 'invalid history/scope rejection', 'untracked resource spending'],
        'new_hf_jobs': 0, 'new_inference': False, 'rollouts': 0, 'new_full_game_trajectories': 0,
        'qualification_eligible': False, 'reserved_final_seeds_used': False,
    })
    began = time.perf_counter(); counts = Counter(); completed = []; coverage = {k: Counter() for k in ('players', 'rules', 'steps', 'rounds', 'families')}
    stderr = (OUT/'worker.stderr.log').open('x')
    worker = subprocess.Popen(['node', str(ROOT/'ai/strong/check-resource-turn-anchor-v1.cjs'), str(RUNTIME)],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=stderr, text=True, bufsize=1)

    def call(value):
        worker.stdin.write(json.dumps(value, allow_nan=False) + '\n'); worker.stdin.flush()
        line = worker.stdout.readline(); assert line, 'Anchor worker exited; inspect preserved stderr'
        return json.loads(line)

    try:
        with (OUT/'positions.jsonl').open('x') as output:
            for index, case in enumerate(cases):
                request = case['request']; state = request['state']
                start = call({'op': 'reset', 'request': request}); seed = public_seed(start)
                local = Counter(); previous = None
                for offset, action in enumerate(case['actions']):
                    result = call({'op': 'inspect', 'seed': seed})
                    assert public_seed(result['anchor']) == seed
                    current = public_seed(result['currentPrepared'])
                    if 'recorded_seeds' in case and case['recorded_seeds'][offset]:
                        assert current == case['recorded_seeds'][offset]
                        local['historical_seeds_reproduced'] += 1
                    if previous is not None:
                        local['purchases'] += 1
                        local['state_dependent_seed_changes'] += current != previous
                    previous = current
                    local.update(positions=1, latent_world_checks=8, private_field_controls=1, duplicate_request_checks=1)
                    output.write(json.dumps({'case': index, 'offset': offset, 'anchor_seed': seed,
                        'current_seed': current, 'anchor': result['anchor']['resourceTurnAnchor'],
                        'worlds': result['worlds']}, allow_nan=False) + '\n'); output.flush()
                    if action == PASS:
                        assert offset == len(case['actions']) - 1
                    else:
                        call({'op': 'move', 'move': action})
                checked = call({'op': 'finish'})
                assert checked['positions'] == len(case['actions'])
                local.update(reversed_request_checks=checked['reversedRequestChecks'],
                    invalid_requests_rejected=checked['invalidRequestsRejected'], untracked_spend_controls=1)
                counts.update(local)
                coverage['players'][str(len(state['players']))] += 1
                coverage['rules'][state['options']['variant'] + ('/sealed' if state['options']['fastBid'] else '/open')] += 1
                coverage['steps'][str(state['step'])] += 1; coverage['rounds'][str(state['round'])] += 1
                coverage['families'][case['family']] += 1
                completed.append({'case': index, 'source': case['source'], 'request_id': request.get('requestId'),
                    'player': request['player'], 'anchor_seed': seed, 'counts': dict(local)})
                if len(completed) % 25 == 0:
                    print(json.dumps({'anchor_turns_checked': len(completed), 'expected': len(cases)}), flush=True)
        worker.stdin.close(); assert worker.wait(timeout=30) == 0; stderr.close()
        assert all(digest(ROOT/name) == sha for name, sha in {**inputs, **code}.items())
        report = {'passed': True, 'turns': len(completed), 'counts': dict(counts),
            'coverage': {k: dict(v) for k, v in coverage.items()}, 'cases': completed,
            'input_hashes': inputs, 'code_hashes': code, 'runtime_manifest_sha256': RUNTIME_SHA,
            'seconds': time.perf_counter() - began,
            'output_hashes': {str(p.relative_to(OUT)): digest(p) for p in OUT.rglob('*') if p.is_file()},
            'new_inference': False, 'new_hf_jobs': 0, 'rollouts': 0, 'new_full_game_trajectories': 0,
            'qualification_eligible': False, 'reserved_final_seeds_used': False,
            'interpretation': 'The public purchase suffix reconstructs the exact first-decision seed and preserves sampled latent assumptions on these turns without process memory. Requires authentic complete public history; does not authenticate arbitrary forged logs. No search policy, causal strength gain or production readiness is established.'}
        write(OUT/'assessment.json', report)
        write(RESULT, {**report, 'assessment_sha256': digest(OUT/'assessment.json')})
        print(json.dumps({k: report[k] for k in ('passed', 'turns', 'counts', 'coverage', 'seconds')}), flush=True)
    except BaseException as error:
        if worker.poll() is None:
            worker.terminate(); worker.wait(timeout=30)
        stderr.close()
        write(OUT/'failure.json', {'error': type(error).__name__ + ': ' + str(error), 'completed_turns': len(completed)})
        raise


if __name__ == '__main__':
    main()
