"""Calibration selection, scope and original-submission boundary checks."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from strategic_collection import ROOT, read, write, digest
import surrogate_continuation_runtime_v1 as runtime


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT/'ai/strong'/filename)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module


builder = load('cost_builder_test', 'build-surrogate-continuation-runtime-source-v1.py')
launcher = load('cost_launcher_test', 'launch-surrogate-continuation-cost-v1.py')
manager = load('cost_manager_test', 'manage-surrogate-continuation-cost-v1.py')


class RuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs = builder.inputs(); cls.games = {}
        for n in (2, 6):
            folder = ROOT/f'ai/runs/surrogate-continuation-roots-runtime-collected-v1/surrogate-continuation-runtime-v1-{n}p-0-1/artifacts/games'
            for seat in range(n):
                for rule in range(4): cls.games[(n, seat, rule)] = read(folder/f'game-{seat*4+rule}/roots.json')

    def test_actual_selection_covers_twenty_four_groups_and_is_order_independent(self):
        a = runtime.select_roots(self.games)
        self.assertEqual(a, self.inputs['roots']); self.assertEqual(len(a), 24)
        self.assertEqual(runtime.select_roots(dict(reversed(list(self.games.items())))), a)
        for key, root in a.items():
            n, rule = root['identity']['players'], root['identity']['rule']; phase = root['phase']
            ranks = [g['roots'][phase]['rank'] for (p, _, r), g in self.games.items() if p == n and r == rule and phase in g['roots']]
            self.assertEqual(root['rank'], min(ranks))

    def test_missing_group_or_resealed_rank_is_not_replaced(self):
        games = deepcopy(self.games)
        for seat in range(2):
            row = games[(2, seat, 0)]; del row['roots']['bid']; row['missing_phases'].append('bid')
        with self.assertRaises(AssertionError): runtime.select_roots(games)
        games = deepcopy(self.games); games[(6, 0, 1)]['roots']['plant']['rank'] = '0'*64
        with self.assertRaises(AssertionError): runtime.select_roots(games)

    def test_runtime_selection_never_parses_game_terminal_outcomes(self):
        original = builder.read; reads = []
        def checked(path):
            reads.append(str(path)); self.assertNotEqual(Path(path).name, 'terminal.json'); return original(path)
        with patch.object(builder, 'read', side_effect=checked):
            self.assertEqual(builder.inputs(), self.inputs)
        self.assertTrue(any(path.endswith('/roots.json') for path in reads))

    def test_invalid_scope_private_hash_and_changed_source_refuse_before_work(self):
        for key, value in [('samples', 4), ('max_steps', 1200), ('workers', 2), ('continuations', 32), ('training_eligible', True)]:
            bad = deepcopy(self.inputs); bad[key] = value
            with self.assertRaises(AssertionError): runtime.validate_inputs(bad)
        bad = deepcopy(self.inputs); next(iter(bad['roots'].values()))['request']['state']['seed'] = 'hidden'
        with self.assertRaises(AssertionError): runtime.validate_inputs(bad)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); inp = root/'roots.json'; manifest = root/'manifest.json'
            write(inp, self.inputs); write(manifest, {'changed.txt': '0'*64}); (root/'changed.txt').write_text('changed')
            with patch.multiple(runtime, ROOT=root, INPUTS=inp, MANIFEST=manifest), \
                 patch.object(runtime, 'hf_hub_download') as download, patch.object(runtime, 'upload_evidence') as upload:
                for key in ['unknown', '2p-0-plant']:
                    with self.assertRaises(AssertionError): runtime.run(key)
                download.assert_not_called(); upload.assert_not_called(); self.assertFalse((root/'ai/runs').exists())

    def test_reference_resource_allowance_preserves_fixed_work(self):
        r = read(launcher.REFERENCE); admission = launcher.resources(r)
        self.assertEqual(admission['timeout_hours'], 6); self.assertEqual(admission['workers'], 8)
        r['max_shard_wall_seconds'] = 20000
        with self.assertRaises(AssertionError): launcher.resources(r)

    def fixture(self, folder):
        prepared = read(builder.PREP/'prepared.json'); source = {**prepared, 'revision': 'a'*40}
        original = builder.PREP/'layout/ai/runs/surrogate-continuation-cost-v1-2p-0-plant'
        shutil.copytree(original, folder)
        state = read(folder/'job.json')
        state.update(source_revision=source['revision'], source_sha256=source['sha256'])
        write(folder/'job.json', state)
        return source, self.reseal(folder)

    def reseal(self, folder):
        manifest = {str(p.relative_to(folder)): digest(p) for p in sorted(folder.rglob('*')) if p.is_file() and p.name != 'manifest.json'}
        write(folder/'manifest.json', manifest)
        return {'manifest_sha256': digest(folder/'manifest.json'), 'archived_files': len(manifest)+1}

    def test_actual_packaged_job_independently_audits_all_thirty_two_outcomes(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)/'artifact'; source, evidence = self.fixture(folder)
            result = manager.audit(folder, source, '2p-0-plant', evidence)
            self.assertEqual(result['continuations'], 32); self.assertEqual(result['caps'], 0)
            self.assertTrue(result['paired_worlds_exact'])

    def test_resealed_wrong_terminal_is_rejected_by_local_collector(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)/'artifact'; source, _ = self.fixture(folder)
            mode = 'reference_opponent_v1'; result = read(folder/mode/'result.json'); result['rows'][0]['value'] = .123
            write(folder/mode/'result.json', result)
            status = read(folder/mode/'status.json'); status['result_sha256'] = digest(folder/mode/'result.json'); write(folder/mode/'status.json', status)
            state = read(folder/'job.json'); state['modes'][mode]['status_sha256'] = digest(folder/mode/'status.json'); write(folder/'job.json', state)
            audit = read(folder/'audit.json'); audit['modes'] = state['modes']; write(folder/'audit.json', audit)
            with self.assertRaises(AssertionError): manager.audit(folder, source, '2p-0-plant', self.reseal(folder))
        r = read(launcher.REFERENCE); r['max_sampled_process_rss_bytes'] = 5e9
        with self.assertRaises(AssertionError): launcher.resources(r)

    def guard(self, fail):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); plan = root/'plan.json'; guards = root/'guards'
            p = {'admission': {'max_concurrent': 24, 'flavor': 'cpu-upgrade', 'timeout_hours': 6}}
            write(plan, p); row = {'case': 'surrogate-continuation-cost-v1-2p-0-plant', 'key': '2p-0-plant'}
            source = {'archive': 'fixture.tgz', 'revision': 'r', 'sha256': 'a'*64, 'manifest_sha256': 'b'*64,
                      'manifest_files': 1477, 'inputs_sha256': 'c'*64}; calls = []
            class Api:
                def run_job(self, **kwargs):
                    calls.append(kwargs)
                    if fail: raise TimeoutError('submission observation timeout')
                    return SimpleNamespace(id='original-fixture-handle')
                def inspect_job(self, job_id):
                    assert job_id == 'original-fixture-handle'
                    return SimpleNamespace(status=SimpleNamespace(stage='RUNNING'))
            with patch.multiple(launcher, PLAN=plan, GUARDS=guards), \
                 patch.object(launcher, 'admission', return_value=(p, source, row)), \
                 patch.object(launcher, 'get_token', return_value='fixture-secret'), patch.object(launcher, 'HfApi', Api):
                if fail:
                    with self.assertRaises(TimeoutError): launcher.launch(row['key'], True)
                    self.assertEqual(read(guards/(row['case']+'.json'))['stage'], 'launch_unknown')
                    with self.assertRaises(AssertionError): launcher.launch(row['key'], True)
                else:
                    launcher.launch(row['key'], True); launcher.launch(row['key'], True)
                self.assertEqual(len(calls), 1); self.assertNotIn('HF_TOKEN', calls[0]['env'])
                self.assertEqual(calls[0]['secrets'], {'HF_TOKEN': 'fixture-secret'})

    def test_existing_handle_reused_without_resubmission(self): self.guard(False)

    def test_submission_timeout_preserved_without_resubmission(self): self.guard(True)


if __name__ == '__main__': unittest.main()
