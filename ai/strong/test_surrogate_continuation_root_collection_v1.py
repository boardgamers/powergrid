"""Real shard verification, whole-grid coverage and interruption-safe root freezing."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from strategic_collection import ROOT, read, write, digest
from surrogate_continuation_roots_v1 import contract, object_hash
from surrogate_continuation_root_verification_v1 import verify_artifacts


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT/'ai/strong'/filename)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module


manager = load('root_manager_test', 'manage-surrogate-continuation-roots-v1.py')
launcher = manager.launcher
coordinator = load('root_coordinator_test', 'coordinate-surrogate-continuation-roots-v1.py')
calibration = load('root_calibration_test', 'collect-surrogate-continuation-roots-calibration-v1.py')
REAL = ROOT/'ai/runs/surrogate-continuation-roots-runtime-collected-v1/surrogate-continuation-runtime-v1-2p-0-1'


def reseal(folder, evidence):
    manifest = {str(path.relative_to(folder)): digest(path) for path in sorted(folder.rglob('*')) if path.is_file() and path.name != 'manifest.json'}
    write(folder/'manifest.json', manifest)
    return {**evidence, 'manifest_sha256': digest(folder/'manifest.json'), 'archived_files': len(manifest)+1}


class CollectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.verified = read(REAL/'verified.json'); cls.source = cls.verified['source']; cls.protocol = read(launcher.PROTOCOL)

    def review(self, folder, evidence):
        return verify_artifacts(folder, evidence, self.source, self.protocol, manager.RUNTIME, manager.MODEL, 2, 0, 1, 'runtime')

    def test_real_eight_game_endpoint_matches_original_audit(self):
        review = self.review(REAL/'artifacts', self.verified['evidence'])
        self.assertEqual({key: review[key] for key in self.verified['review']}, self.verified['review'])
        self.assertEqual(len(review['phase_counts']), 12)
        self.assertEqual(review['selected_roots'], 24)

    def test_resealed_incomplete_shard_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)/'artifacts'; shutil.copytree(REAL/'artifacts', folder)
            state = read(folder/'games/status.json'); del state['cases']['0']; write(folder/'games/status.json', state)
            with self.assertRaises(AssertionError): self.review(folder, reseal(folder, self.verified['evidence']))

    def test_resealed_private_root_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)/'artifacts'; shutil.copytree(REAL/'artifacts', folder)
            game = folder/'games/game-0'; roots = read(game/'roots.json'); row = roots['roots']['plant']
            row['request']['state']['seed'] = 'private-game-seed'; row['public_root_sha256'] = object_hash(row['request'])
            for item in roots['eligible']:
                if item['decision'] == row['decision']: item['public_root_sha256'] = row['public_root_sha256']
            write(game/'roots.json', roots); receipt = read(game/'verified.json'); receipt['files']['roots.json'] = digest(game/'roots.json'); write(game/'verified.json', receipt)
            state = read(folder/'games/status.json'); state['cases']['0'] = receipt; write(folder/'games/status.json', state)
            with self.assertRaises(AssertionError): self.review(folder, reseal(folder, self.verified['evidence']))

    def test_fixed_grid_and_measured_admission_preserve_all_games(self):
        for deals, count in [(2, 5), (1, 10)]:
            rows = launcher.cases(self.protocol, deals)
            self.assertEqual(len(rows), count); self.assertEqual(sum(row['games'] for row in rows), 160)
            self.assertEqual(sum(row['maximum_roots'] for row in rows), 480)
        cells = {str(n): {'complete': True, 'games': 4*n, 'twin_games': 4*n, 'caps': 0, 'selected_roots': 12*n,
                         'raw_evidence_bytes': 10000000, 'runtime': {'seconds': 1000., 'cpu_seconds': 7500., 'sampled_peak_total_rss_bytes': 6000000000}} for n in (2, 6)}
        admitted = launcher.measured_admission(cells)
        self.assertEqual(admitted['deals_per_shard'], 2); self.assertEqual(admitted['timeout_hours'], 2)
        large = deepcopy(cells); large['6']['runtime']['seconds'] = 10000.
        self.assertEqual(launcher.measured_admission(large)['deals_per_shard'], 1)
        large['6']['runtime']['sampled_peak_total_rss_bytes'] = 17000000000
        with self.assertRaises(AssertionError): launcher.measured_admission(large)
        with self.assertRaises(AssertionError): launcher.measured_admission({'2': cells['2']})

    def synthetic_grid(self, root):
        collected = root/'collected'; rows = launcher.cases(self.protocol, 2); receipts = {}
        plan = {'shards': rows, 'games': 160, 'maximum_roots': 480, 'source': {'sha256': '1'*64},
                'protocol_sha256': digest(launcher.PROTOCOL), 'admission': {'max_in_flight': 10}}
        for row in rows:
            case = row['case']; receipt = {'verified': True, 'row': row, 'job_id': f'fixture-{row["players"]}',
                'review': {'games': row['games'], 'selected_roots': row['maximum_roots']}, 'evidence': {'fixture_only': True}}
            receipts[case] = receipt
            for episode in range(row['start']*4*row['players'], row['end']*4*row['players']):
                n = row['players']; q = contract(n, episode//(4*n), episode//4 % n, episode % 4, 'root')
                selected = {'roots': {}, 'eligible': [], 'missing_phases': []}
                for i, phase in enumerate(('plant', 'bid', 'building')):
                    candidates = [{'decision': d, 'phase': phase, 'rank': object_hash([q['seed'], episode, phase, d]),
                        'public_root_sha256': '2'*64, 'options': [0, 1], 'round': 1, 'prior_actors': []} for d in (2*i, 2*i+1)]
                    selected['eligible'].extend(candidates); winner = min(candidates, key=lambda r: (r['rank'], r['decision']))
                    selected['roots'][phase] = {**winner, 'identity': q, 'request': {'synthetic_fixture_only': True}}
                folder = collected/case/'artifacts/games'/f'game-{episode}'; folder.mkdir(parents=True)
                write(folder/'roots.json', selected); write(folder/'contract.json', q)
            write(collected/case/'verified.json', receipt)
        plan_path = root/'plan.json'; write(plan_path, plan)
        return plan, receipts, collected, plan_path

    def test_freeze_recovers_after_index_write_interruption(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'ai/runs') as temp:
            root = Path(temp); plan, receipts, collected, plan_path = self.synthetic_grid(root)
            index_path = root/'index.json'; frozen = root/'frozen'; real_write = manager.write

            def fail_final(path, value):
                if path == index_path.with_suffix('.tmp.json'): raise OSError('simulated final index write interruption')
                return real_write(path, value)

            with patch.object(launcher, 'PLAN', plan_path), patch.object(launcher, 'admission'), \
                    patch.object(manager, 'COLLECTED', collected), patch.object(manager, 'FROZEN', frozen), \
                    patch.object(manager, 'INDEX', index_path), patch.object(manager, 'verified_receipt', side_effect=receipts.get):
                with patch.object(manager, 'write', side_effect=fail_final):
                    with self.assertRaises(OSError): manager.index()
                self.assertTrue((frozen/'frozen.json').exists()); self.assertFalse(index_path.exists())
                original = digest(frozen/'roots.json'); result = manager.index()
                self.assertEqual(result['games'], 160); self.assertEqual(result['selected_roots'], 480)
                self.assertEqual(len(result['phase_counts']), 60); self.assertEqual(digest(frozen/'roots.json'), original)
                self.assertEqual(manager.index(), result)
                receipts[next(iter(receipts))]['job_id'] = 'switched-fixture'
                with self.assertRaises(AssertionError): manager.index()

    def test_missing_shard_or_selected_rank_cannot_be_frozen(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); plan, receipts, collected, plan_path = self.synthetic_grid(root)
            with patch.object(launcher, 'PLAN', plan_path), patch.object(manager, 'COLLECTED', collected):
                incomplete = dict(receipts); incomplete.pop(next(iter(incomplete)))
                with self.assertRaises(AssertionError): manager.build_manifest(plan, incomplete)
                case = next(iter(receipts)); folder = collected/case/'artifacts/games/game-0'
                selected = read(folder/'roots.json'); row = selected['roots']['plant']; alternatives = [r for r in selected['eligible'] if r['phase'] == 'plant']
                wrong = max(alternatives, key=lambda r: r['rank']); selected['roots']['plant'] = {**row, **wrong}; write(folder/'roots.json', selected)
                with self.assertRaises(AssertionError): manager.build_manifest(plan, receipts)

    def test_missing_count_rule_phase_is_reported_before_freeze(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); plan, receipts, collected, plan_path = self.synthetic_grid(root)
            case = next(row['case'] for row in plan['shards'] if row['players'] == 2)
            for episode in (1, 5, 9, 13):
                folder = collected/case/'artifacts/games'/f'game-{episode}'; selected = read(folder/'roots.json')
                del selected['roots']['bid']; selected['missing_phases'] = ['bid']
                selected['eligible'] = [row for row in selected['eligible'] if row['phase'] != 'bid']; write(folder/'roots.json', selected)
            receipts[case]['review']['selected_roots'] -= 4
            with patch.object(launcher, 'PLAN', plan_path), patch.object(manager, 'COLLECTED', collected):
                with self.assertRaisesRegex(AssertionError, 'missing coverage'): manager.build_manifest(plan, receipts)

    def test_coordinator_only_launches_missing_jobs_with_capacity(self):
        for capacity in (1, 2):
            with tempfile.TemporaryDirectory() as temp:
                root = Path(temp); guards = root/'guards'; guards.mkdir(); plan_path = root/'plan.json'
                plan = {'shards': [{'case': 'original'}, {'case': 'not-submitted'}], 'admission': {'max_in_flight': capacity}}
                write(plan_path, plan); write(guards/'original.json', {'stage': 'launched', 'plan_sha256': digest(plan_path), 'job_id': 'original-id'})
                state = {}
                with patch.object(coordinator, 'OUT', root), patch.object(coordinator.launcher, 'GUARDS', guards), \
                        patch.object(coordinator.launcher, 'PLAN', plan_path), patch.object(coordinator.manager, 'verified_receipt', return_value=None), \
                        patch.object(coordinator.manager, 'inspect', return_value={'case': 'original', 'authoritative_status': 'RUNNING'}), \
                        patch.object(coordinator.launcher, 'launch') as launch:
                    self.assertFalse(coordinator.cycle(plan, state, lambda: None))
                    if capacity == 1: launch.assert_not_called()
                    else: launch.assert_called_once_with('not-submitted', True)

    def test_coordinator_does_not_replace_failed_original_job(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); guards = root/'guards'; guards.mkdir(); plan_path = root/'plan.json'
            plan = {'shards': [{'case': 'original'}, {'case': 'not-submitted'}], 'admission': {'max_in_flight': 10}}
            write(plan_path, plan); write(guards/'original.json', {'stage': 'launched', 'plan_sha256': digest(plan_path), 'job_id': 'original-id'})
            state = {}
            with patch.object(coordinator, 'OUT', root), patch.object(coordinator.launcher, 'GUARDS', guards), \
                    patch.object(coordinator.launcher, 'PLAN', plan_path), patch.object(coordinator.manager, 'verified_receipt', return_value=None), \
                    patch.object(coordinator.manager, 'inspect', return_value={'case': 'original', 'authoritative_status': 'ERROR'}), \
                    patch.object(coordinator.launcher, 'launch') as launch:
                with self.assertRaises(AssertionError): coordinator.cycle(plan, state, lambda: None)
                launch.assert_not_called(); self.assertEqual(len(state['failed_jobs']), 1)


if __name__ == '__main__': unittest.main()
