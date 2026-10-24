"""Existing real receipts plus deliberately corrupted copies; no new games."""
import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from strategic_collection import ROOT
from resource_policy_verification_v1 import verify_decision, verify_evaluation, verify_plan, EXECUTION
from population_policy_verification import verify_evaluation as verify_base_evaluation

BASE = ROOT / 'ai/runs/resource-replanning-v1'


def read(path):
    return json.loads(path.read_text())


class ResourceVerificationTests(unittest.TestCase):
    def sample(self):
        entry = read(BASE / 'replays/6p-recharged-sealed-economic-slow-root.json')
        row, request = entry['reference'], entry['request']
        config = {'players': 6, 'samples': 4, 'arm': 'resource-filter',
                  'model_sha256': row['modelSha256']}
        return row, config, request['player']

    def test_all_existing_phase_and_game_receipts(self):
        phase_count = game_count = rollouts = single_bundle = 0
        for line in (BASE / 'checks-v2/turns.jsonl').read_text().splitlines():
            for decision in json.loads(line)['decisions']:
                row, q = decision['result'], decision['request']
                checked = verify_decision(row, {'players': len(q['state']['players']),
                    'samples': 4, 'arm': row['arm'], 'model_sha256': row['modelSha256']}, q['player'])
                rollouts += checked['rollouts']
                phase_count += 1
        for path in sorted((BASE / 'games').glob('*/config.json')):
            config = read(path)
            for line in (path.parent / f"decisions-{config['episode']}.jsonl").read_text().splitlines():
                row = json.loads(line)
                checked = verify_decision(row, config, 0)
                rollouts += checked['rollouts']
                game_count += 1
                if row['resourcePlan']:
                    single_bundle += len(row['resourcePlan']['bundles']) == 1
        self.assertEqual((phase_count, game_count, rollouts, single_bundle), (112, 540, 11900, 1))

    def test_actual_eight_world_prefix_plan(self):
        plan = read(ROOT / 'ai/runs/resource-turn-search-v1/trained/prefix.json')
        selection = read(ROOT / 'ai/runs/resource-turn-search-v1/selection.json')
        q = selection['selected']['late-6p-recharged-sealed']['request']
        verify_plan(plan, {'players': 6, 'samples': 8, 'model_sha256': plan['modelSha256']}, q['player'])

    def test_unchanged_complete_game_validation(self):
        games = decisions = 0
        for n in range(2, 7):
            path = ROOT / f'ai/runs/population-policy-arena-controls-v1/{n}p'
            config = read(path / 'evaluation.json')['config']
            base = verify_base_evaluation(path, config)
            actual = verify_evaluation(path, config)
            self.assertEqual(base, actual)
            games += actual['games']
            decisions += actual['counts']['decisions']
        self.assertEqual((games, decisions), (80, 10207))

    def test_existing_auction_building_contract_under_resource_envelope(self):
        # This tests envelope composition only: actual existing search receipts
        # are wrapped, without claiming new resource-combined gameplay evidence.
        fixtures = read(ROOT / 'ai/runs/trained-hybrid-probe-v2/selected-fixtures.json')
        path = ROOT / 'ai/runs/population-policy-trained-probe-v1/results.jsonl'
        count = 0
        for line in path.read_text().splitlines():
            case = json.loads(line)
            q = fixtures[case['fixture']]['fixture']['request']
            for arm in ['filter', 'combined']:
                row = {**case['results'][arm], 'arm': 'resource-' + arm,
                       'executionMode': EXECUTION, 'resourcePlan': None}
                verify_decision(row, {'players': len(q['state']['players']), 'arm': row['arm'],
                    'samples': 8, 'model_sha256': row['modelSha256'], 'sealed': True}, q['player'])
                count += 1
        self.assertEqual(count, 8)

    def test_wrong_resource_receipts_rejected(self):
        row, config, seat = self.sample()
        verify_decision(row, config, seat)
        def first(r):
            return r['resourcePlan']['receipts'][0]
        def mean(r):
            p = r['resourcePlan'];p['search']['meanCredits'][p['bundles'][0]['id']] += 1
        def choice(r):
            r['resourcePlan']['selected'] = (r['resourcePlan']['selected'] + 1) % len(r['resourcePlan']['bundles'])
        def model(r):
            r['modelSha256'] = '0' * 64
        def sample_count(r):
            r['resourcePlan']['search']['samples'] = 8
        def missing_world(r):
            del r['resourcePlan']['search']['worlds']['0']
        def world_role(r):
            r['resourcePlan']['search']['worlds']['0']['roles'][seat] = 'rush'
        def pair(r):
            first(r)['initialBelief']['sampledWorldSha256'] = '0' * 64
        def purchase(r):
            p = r['resourcePlan'];p['bundles'][-1]['actions'].insert(0, {'name': 'BuyResource', 'data': {'resource': 'coal'}})
        def money(r):
            first(r)['resourceTurn']['afterPurchases']['money'] += 1
        def stock(r):
            first(r)['resourceTurn']['afterPurchases']['stock'][0] += 1
        def market(r):
            first(r)['resourceTurn']['afterPurchases']['market'][0] += 1
        def cost(r):
            first(r)['resourceTurn']['cost'] += 1
        def winner(r):
            first(r)['value'] = .25
        def terminal(r):
            first(r)['terminal'][seat]['powered'] = 10000
        def nan(r):
            first(r)['value'] = float('nan')
        def missing_receipt(r):
            r['resourcePlan']['receipts'].pop()
        def duplicate_receipt(r):
            r['resourcePlan']['receipts'][1] = copy.deepcopy(first(r))
        def neural_count(r):
            r['resourcePlan']['search']['neuralDecisions'] += 1
        def steps(r):
            first(r)['steps'] += 1
        def nested_search(r):
            first(r)['searchStats']['evaluations'] = 1
        def execution(r):
            r['executionMode'] = 'commit-the-whole-plan'
        def outer_move(r):
            r['move'] = {'name': 'Build', 'data': 'invalid'}
        def outer_proposal(r):
            r['modelProposal'] += 1
        def outer_index(r):
            r['index'] = r['modelProposal'] if r['index'] != r['modelProposal'] else r['index'] + 1
        mutations = [mean, choice, model, sample_count, missing_world, world_role, pair, purchase,
                     money, stock, market, cost, winner, terminal, nan, missing_receipt,
                     duplicate_receipt, neural_count, steps, nested_search, execution,
                     outer_move, outer_proposal, outer_index]
        for mutate in mutations:
            with self.subTest(mutation=mutate.__name__):
                broken = copy.deepcopy(row)
                mutate(broken)
                # Keep the duplicated outer search in sync so corrupt search
                # data reaches the independent recomputation checks.
                broken['search'] = copy.deepcopy(broken['resourcePlan']['search'])
                with self.assertRaises((AssertionError, ValueError)):
                    verify_decision(broken, config, seat)
        self.assertEqual(len(mutations), 24)

    def test_consistent_but_wrong_selected_bundle_rejected(self):
        row, config, seat = self.sample()
        plan = copy.deepcopy(row['resourcePlan'])
        plan['selected'] = (plan['selected'] + 1) % len(plan['bundles'])
        plan['actions'] = plan['bundles'][plan['selected']]['actions']
        plan['firstMove'] = plan['actions'][0]
        with self.assertRaises(AssertionError):
            verify_plan(plan, config, seat)

    def test_deliberate_caps_retained_and_rejected_for_strength(self):
        row = read(BASE / 'checks-v2/cap.json')
        q = read(ROOT / 'ai/runs/resource-turn-search-v1/selection.json')['selected']['late-6p-recharged-sealed']['request']
        config = {'players': 6, 'samples': 4, 'arm': row['arm'], 'model_sha256': row['modelSha256']}
        with self.assertRaises(AssertionError):
            verify_decision(row, config, q['player'], horizon=1)
        check = verify_decision(row, config, q['player'], horizon=1, allow_caps=True)
        self.assertGreater(check['rollout_caps'], 0)

    def test_report_pairing_winner_missing_and_receipt_corruption_rejected(self):
        source = ROOT / 'ai/runs/population-policy-arena-controls-v1/2p'
        for mutation in ['pair', 'winner', 'receipt', 'missing']:
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temp:
                folder = Path(temp) / 'report'
                shutil.copytree(source, folder)
                report = read(folder / 'evaluation.json')
                if mutation == 'pair':
                    report['results'][1] = copy.deepcopy(report['results'][0])
                elif mutation == 'missing':
                    report['results'].pop()
                elif mutation == 'receipt':
                    path = folder / 'decisions-0.jsonl';path.write_text(path.read_text() + '\n')
                else:
                    row = report['results'][0]
                    row['terminal']['value'] = [1 - v for v in row['terminal']['value']]
                    row['terminal']['win'] = row['terminal']['value'][row['terminal']['seat']]
                    (folder / 'game-0.json').write_text(json.dumps(row))
                (folder / 'evaluation.json').write_text(json.dumps(report))
                with self.assertRaises((AssertionError, ValueError)):
                    verify_evaluation(folder, report['config'])


if __name__ == '__main__':
    unittest.main()
