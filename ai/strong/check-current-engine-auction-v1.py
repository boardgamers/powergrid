"""Validate the isolated current engine on fixed serving/search positions.

No job submission, gradients or fresh strength games. Continuations are actual
engineering executions, not observations to add to any strength dataset.
"""
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import time

from public_policy_arena_v1 import PublicPolicyProcess, validate_response, semantic
from public_policy_final_audit_v1 import artifact_identity
from public_policy_development_job_v1 import digest, read
from population_policy_verification import verify_decision as verify_filter
from opponent_auction_verification_v1 import verify_decision as verify_auction

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'ai/runs/current-engine-auction-v1'
OLD = ROOT / 'ai/runs/conservative-auction-development-prepared-v2/source/artifact'
ARTIFACT = OUT / 'artifact'
RESULT = ROOT / 'ai/strong/current-engine-auction-fixtures-v1.json'
ARMS = ('filter', 'conservative_population')


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False); stream.write('\n')


def lines(path): return [json.loads(line) for line in path.read_text().splitlines()]


def main():
    assert not (OUT / 'check-intent.json').exists() and not RESULT.exists(), 'Inspect previous run before retry'
    prep = read(OUT / 'prepared.json')
    assert digest(ARTIFACT / 'manifest.json') == prep['runtime_manifest_sha256']
    assert all(digest(ARTIFACT / name) == sha for name, sha in read(ARTIFACT / 'manifest.json').items())
    assert digest(OLD / 'manifest.json') == prep['original_runtime_manifest_sha256']
    serving = ROOT / 'ai/strong/fixtures/multiplayer-serving-v1.jsonl'
    assert digest(serving) == 'f1c97bf909e38e5df372a89d169d80f5a6f24c00dccefacd60b10b767f1fcfa0'
    cpu = ROOT / 'ai/runs/conservative-auction-8840u-prepared-v2'
    cases = cpu / 'package/cases.json'; cp = read(cpu / 'prepared.json')
    assert digest(cases) == cp['cases_sha256']
    archived = ROOT / 'ai/runs/conservative-auction-8840u-collected-v2/output/receipts.jsonl'
    # The verified 8840U assessment pins the original reference receipts.
    cpu_assessment = ROOT / 'ai/runs/conservative-auction-8840u-collected-v2/assessment.json'
    cpu_archive = ROOT / 'ai/strong/conservative-auction-cpu-results-evidence-v2.json'
    cpu_status = archived.with_name('status.json')
    cpu_manifest = cpu / 'package/benchmark-manifest.json'
    cpu_proof = read(cpu_archive)
    assert cpu_proof['archive']['remote_archive_verified']
    assert digest(cpu_assessment) == cpu_proof['checkpoint']['assessment_sha256']
    assert digest(cpu_status) == read(cpu_assessment)['target_status_sha256']
    assert digest(archived) == read(cpu_status)['output_hashes']['receipts.jsonl']
    assert digest(cpu_manifest) == read(cpu_assessment)['manifest_sha256']
    assert digest(cases) == read(cpu_manifest)['files']['cases.json']
    archived_responses = {(r['arm'], r['case']): r['response'] for r in lines(archived)}
    assert len(archived_responses) == 300
    counter = ROOT / 'ai/runs/current-engine-policy-v1/inputs.json'
    assert digest(counter) == read(ROOT / 'ai/strong/current-engine-policy-results-v1.json')['inputs_sha256']
    natural_paths = [ROOT / f'ai/runs/auction-training-history-v{v}/newly-affordable-roots.jsonl' for v in (1, 2)]
    for v, path in enumerate(natural_paths, 1):
        assert digest(path) == read(ROOT / f'ai/strong/auction-training-history-results-v{v}.json')['artifacts'][path.name]
    fixtures = [{**row, 'name': f'serving-{i}', 'origin': 'serving', 'ordinal': i}
                for i, row in enumerate(lines(serving))]
    assert len(fixtures) == 2553
    benchmarks = read(cases); assert len(benchmarks) == 100
    benchmark_fixtures = [{**case['fixture'], 'name': 'cpu-' + case['name'],
        'origin': 'cpu', 'cpu_case': case['name']} for case in benchmarks]
    extras = [{**row, 'name': f'counterfactual-{i}', 'origin': 'counterfactual-current'}
              for i, row in enumerate(read(counter))]
    for v, path in enumerate(natural_paths, 1):
        extras.extend({**row, 'name': f'natural-v{v}-{i}', 'origin': 'natural-current'}
                      for i, row in enumerate(lines(path)))
    assert len(extras) == 40
    worker = Path(__file__).with_name('current-engine-auction-inputs-v1.cjs')
    inputs = [serving, cases, archived, cpu_assessment, cpu_archive, cpu_status, cpu_manifest, counter, *natural_paths,
              Path(__file__), worker, OUT / 'prepared.json', ARTIFACT / 'manifest.json']
    pins = {str(p.relative_to(ROOT)): digest(p) for p in inputs}
    save(OUT / 'check-intent.json', {'started_at': datetime.now(timezone.utc).isoformat(),
        'input_hashes': pins, 'filter_positions': 2693, 'population_positions': 140,
        'search_settings': prep['descriptors']['conservative_population']['settings'],
        'selection': 'All 2553 original serving fixtures for filter. Both policies also use the separately normalized 100 existing CPU cases, all 30 prior control/cash interventions and all 10 recovered natural roots. No outcome-dependent selection.',
        'scope': 'Engineering compatibility only; full-game/current-wrapper admission remains separate.',
        'new_hf_jobs': 0, 'new_full_games': 0, 'new_gradients': 0,
        'qualification_eligible': False, 'reserved_final_seeds_used': False})
    started = time.monotonic()
    processed = []
    with (OUT / 'inputs.stderr.log').open('x') as log:
        node = subprocess.Popen(['node', str(worker), str(OLD), str(ARTIFACT)], cwd='/tmp',
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=log, text=True)
        try:
            with (OUT / 'inputs.jsonl').open('x') as output:
                for i, fixture in enumerate([*fixtures, *benchmark_fixtures, *extras]):
                    public_check = i >= 2553
                    node.stdin.write(json.dumps({'fixtures': [fixture], 'publicCheck': public_check}) + '\n'); node.stdin.flush()
                    line = node.stdout.readline(); assert line, 'Fixture worker failed; inspect preserved stderr'
                    row = json.loads(line)[0]; processed.append(row)
                    output.write(json.dumps(row, allow_nan=False) + '\n')
        finally:
            node.stdin.close(); code = node.wait(timeout=30); node.stdout.close()
        assert code == 0
    assert len(processed) == 2693
    print(json.dumps({'prepared_positions': len(processed), 'changed_menus': sum(not r['menusEqual'] for r in processed),
                      'public_boundary_checks': sum(r['informationBoundary'] for r in processed)}), flush=True)
    identities = {arm: artifact_identity(ARTIFACT, f'policies/{arm}.json') for arm in ARMS}
    report = {'passed': False, 'scope': 'Fixed-position engineering compatibility; not full-game or wrapper admission.',
        'positions': len(processed), 'menu_changes': [r['name'] for r in processed if not r['menusEqual']],
        'exact_prepared_positions': sum(r['preparedExact'] for r in processed),
        'information_boundary_checks': sum(r['informationBoundary'] for r in processed),
        'counts': {}, 'identities': identities, 'input_hashes': pins,
        'new_hf_jobs': 0, 'new_full_games': 0, 'new_gradients': 0,
        'qualification_eligible': False, 'reserved_final_seeds_used': False}
    responses = {}
    with (OUT / 'decisions.jsonl').open('x') as receipts:
        for arm in ARMS:
            chosen = processed if arm == 'filter' else processed[2553:]
            totals = Counter(); changed = []; migration_changes = []
            with (OUT / (arm + '.stderr.log')).open('x') as log:
                process = PublicPolicyProcess(ARTIFACT, f'policies/{arm}.json', log)
                try:
                    for i, fixture in enumerate(chosen):
                        request = fixture['request']; before = deepcopy(request)
                        response = process.call(request)
                        n, seat = len(request['state']['players']), request['player']
                        order = [(seat + i) % n for i in range(n)]
                        validate_response(response, request, fixture['legal'], order, identities[arm])
                        assert request == before
                        decision = {**response['decision'], 'arenaMoves': fixture['legal']}
                        config = {'players': n, 'arm': 'filter' if arm == 'filter' else 'opponent-auction-v1',
                            'samples': 8, 'model_sha256': response['modelSha256'], 'identity': identities[arm]}
                        totals.update((verify_filter if arm == 'filter' else verify_auction)(decision, config, seat))
                        totals['requests'] += 1
                        if fixture['origin'] == 'cpu':
                            previous = archived_responses[arm, fixture['cpu_case']]
                            if fixture['preparedExact']:
                                assert response['decision']['modelProposal'] == previous['decision']['modelProposal']
                                if arm == 'filter':
                                    assert semantic(response['decision']) == semantic(previous['decision'])
                                    totals['exact_archived_filter_controls'] += 1
                            if response['move'] != previous['move']: migration_changes.append(fixture['cpu_case'])
                        if arm == 'conservative_population':
                            reference = responses[fixture['name']]
                            assert response['decision']['modelProposal'] == reference['decision']['modelProposal']
                            if not response['decision']['search']:
                                assert response['move'] == reference['move']
                            if response['move'] != reference['move']: changed.append(fixture['name'])
                        else: responses[fixture['name']] = response
                        receipts.write(json.dumps({'arm': arm, 'name': fixture['name'], 'request': request,
                            'legal': fixture['legal'], 'response': response}, allow_nan=False) + '\n'); receipts.flush()
                        if (i + 1) % (100 if arm == 'filter' else 5) == 0:
                            print(json.dumps({'arm': arm, 'requests': i+1, 'expected': len(chosen),
                                              'rollouts': totals['rollouts']}), flush=True)
                finally: process.close()
            assert totals['requests'] == len(chosen) and totals['rollout_caps'] == 0
            report['counts'][arm] = dict(totals)
            if arm == 'conservative_population':
                report['search_changes'] = changed
                report['current_vs_historical_search_choice_changes'] = migration_changes
    assert all(digest(ROOT / name) == sha for name, sha in pins.items())
    assert all(digest(ARTIFACT / name) == sha for name, sha in read(ARTIFACT / 'manifest.json').items())
    report.update(passed=True, completed_at=datetime.now(timezone.utc).isoformat(),
        seconds=time.monotonic()-started, prepared_sha256=digest(OUT / 'prepared.json'),
        intent_sha256=digest(OUT / 'check-intent.json'), inputs_sha256=digest(OUT / 'inputs.jsonl'),
        receipts_sha256=digest(OUT / 'decisions.jsonl'))
    save(OUT / 'assessment.json', report); save(RESULT, report)
    print(json.dumps({'passed': True, 'counts': report['counts'], 'seconds': report['seconds']}), flush=True)


if __name__ == '__main__': main()
