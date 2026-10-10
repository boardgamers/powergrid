"""Final-harness contract tests only: no HF submissions or reserved game play."""
import contextlib
import copy
import fcntl
import hashlib
import io
import importlib.util
import json
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
STRONG = ROOT/'ai/strong'
read = lambda p: json.loads(p.read_text())
write = lambda p, d: p.write_text(json.dumps(d))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


class LaunchContracts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name)
        self.folder = self.root/'ai/strong'; self.folder.mkdir(parents=True)
        for name in ['launch-final.py', 'launch-multiplayer-arena.sh', 'arena-job.py']:
            shutil.copy2(STRONG/name, self.folder/name)
        self.archive = self.root/'runtime.tgz'
        with tarfile.open(self.archive, 'w:gz') as t:
            t.add(self.folder/'arena-job.py', arcname='ai/strong/arena-job.py')
        self.model = self.root/'unit-test-model-bytes'; self.model.write_bytes(b'contract fixture, never evaluated')
        self.protocol = read(STRONG/'final-protocol-multiplayer.json')
        self.protocol['seed_prefix'] = 'contract-test-only-not-reserved'
        self.protocol_path = self.root/'protocol.json'; write(self.protocol_path, self.protocol)
        self.candidate = {'status': 'selected', 'feature_revision': '4.2-discard-correction',
            'model_path': 'fixture.onnx', 'model_revision': 'a'*40, 'model_sha256': sha(self.model),
            'search_samples': 48, 'search_max_steps': 2400, 'search_scope': 'all', 'geographic_search': True,
            'source': {'archive': 'fixture.tgz', 'revision': 'b'*40, 'sha256': sha(self.archive)},
            'arena_runner_sha256': sha(self.folder/'arena-job.py'), 'arena_timeout_hours': 4, 'async_rollout': False}
        self.candidate_path = self.root/'candidate-fixture.json'; write(self.candidate_path, self.candidate)
        write(self.folder/'experiments.json', {'jobs': {}, 'final_seed_prefix_used': False})

    def tearDown(self): self.tmp.cleanup()

    def invoke(self, submit, launch=True):
        argv = [str(self.folder/'launch-final.py'), str(self.candidate_path), '--protocol', str(self.protocol_path)]
        if launch: argv.append('--launch')
        def download(*args, **kwargs): return str(self.archive if kwargs.get('repo_type') == 'dataset' else self.model)
        with patch.object(sys, 'argv', argv), patch('huggingface_hub.hf_hub_download', side_effect=download), \
             patch('subprocess.run', side_effect=submit), contextlib.redirect_stdout(io.StringIO()):
            runpy.run_path(str(self.folder/'launch-final.py'), run_name='__main__')

    def test_current_feature_and_all_shards_have_pinned_runtime(self):
        calls = []
        def submit(command, **kw):
            calls.append((command, kw['env']))
            self.assertEqual(kw['env']['SOURCE_SHA256'], sha(self.archive))
            self.assertEqual(kw['env']['MODEL_SHA256'], sha(self.model))
            self.assertEqual(kw['env']['ASYNC_ARENA'], '0')
            self.assertEqual(kw['env']['TIMEOUT_HOURS'], '4')
            return subprocess.CompletedProcess(command, 0, stdout=f'{len(calls):024x}', stderr='')
        self.invoke(submit)
        self.assertEqual(len(calls), 320)
        self.assertEqual(sum(int(c[0][-2]) for c in calls), 20160)
        self.assertEqual({int(env['PLAYER_COUNT']) for _, env in calls}, {2, 3, 4, 5, 6})
        self.invoke(lambda *a, **k: self.fail('Duplicate submission'))

    def test_ambiguous_launch_blocks_duplicate_submission(self):
        with self.assertRaisesRegex(RuntimeError, 'ambiguous'):
            self.invoke(lambda command, **kw: subprocess.CompletedProcess(command, 0, stdout='no job id', stderr=''))
        ledger = read(self.folder/'experiments.json'); entry = next(iter(ledger['final_runs'].values()))
        self.assertEqual(len(entry['jobs']), 1)
        self.assertEqual(next(iter(entry['jobs'].values()))['stage'], 'launch_intent')
        with self.assertRaisesRegex(RuntimeError, 'Unresolved launch intent'):
            self.invoke(lambda *a, **k: self.fail('Must not retry an unresolved submission'))

    def test_dry_run_cannot_submit_or_spend_seeds(self):
        with self.assertRaises(SystemExit) as error:
            self.invoke(lambda *a, **k: self.fail('Dry run submitted'), launch=False)
        self.assertEqual(error.exception.code, 0)
        self.assertFalse(read(self.folder/'experiments.json')['final_seed_prefix_used'])

    def test_old_runtime_is_rejected_before_submission(self):
        self.candidate['arena_runner_sha256'] = '0'*64; write(self.candidate_path, self.candidate)
        with self.assertRaises(AssertionError): self.invoke(lambda *a, **k: self.fail('Wrong runtime submitted'))
        self.assertFalse(read(self.folder/'experiments.json')['final_seed_prefix_used'])

    def test_concurrent_launch_is_rejected_before_submission(self):
        with (self.folder/'.final-launch.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaisesRegex(RuntimeError, 'Another final launcher'):
                self.invoke(lambda *a, **k: self.fail('Concurrent submission'))
        self.assertFalse(read(self.folder/'experiments.json')['final_seed_prefix_used'])


class VerificationContracts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name)
        self.report = read(ROOT/'ai/runs/search-transfer-verified-v1/10102-heuristic-2p/search.json')
        source = read(STRONG/'search-transfer-source-v1.json')
        self.candidate = {'status': 'selected', 'model_sha256': self.report['model_sha256'],
            'feature_revision': '4.2-discard-correction', 'model_revision': 'b115a2d78aae095e51fb72a5535b3507abdf90c0',
            'source': source, 'arena_runner_sha256': sha(STRONG/'arena-job.py'),
            'search_samples': 48, 'search_max_steps': 2400, 'search_scope': 'all',
            'geographic_search': True, 'async_rollout': False}
        # Synthetic provenance/CPU/parity wrappers test validation logic around
        # real development rows. They are temporary unit fixtures, not evidence.
        self.report.update(source={k: source[k] for k in ['archive', 'revision', 'sha256']},
            arena_runner_sha256=self.candidate['arena_runner_sha256'],
            model_repository_revision=self.candidate['model_revision'], opponent_repository_revision=None)
        self.protocol = read(STRONG/'final-protocol-multiplayer.json')
        self.protocol['seed_prefix'] = 'discard-opponents-games-v1'
        self.protocol['opponents'] = [{'name': 'heuristic', 'independent_deals_per_count': 16,
                                     'counts': {'2': {'games': 128, 'minimum_win_rate': .775}}}]
        identity = {'model_sha256': self.candidate['model_sha256']}
        artifacts = {'candidate': self.candidate, 'protocol': self.protocol,
            'parity': {**identity, 'positions': 2553, 'all_actions_match': True, 'inactive_values_zero': True,
                       'by_player_count': {str(n): {} for n in range(2, 7)}},
            'cpu': {**identity, 'positions': 2553, 'all_moves_legal': True, 'processor_model': 'unit fixture 8840U',
                    'search_samples': 48, 'search_scope': 'all', 'geographic_search': True, 'search_truncated_rollouts': 0,
                    'by_player_count': {str(n): {} for n in range(2, 7)}},
            'package': {**identity, 'all_hashes_match': True, 'files_verified': 1,
                        'positions_verified': 80, 'player_counts': [2, 3, 4, 5, 6]}}
        for name, artifact in artifacts.items(): write(self.root/(name+'.json'), artifact)

    def tearDown(self): self.tmp.cleanup()

    def verify(self, report):
        write(self.root/'report.json', report)
        command = [sys.executable, str(STRONG/'verify-final.py'), str(self.root/'candidate.json'),
                   str(self.root/'report.json'), '--output', str(self.root/'output.json')]
        for name in ['protocol', 'parity', 'cpu', 'package']: command += ['--'+name, str(self.root/(name+'.json'))]
        r = subprocess.run(command, capture_output=True, text=True)
        if not (self.root/'output.json').exists(): self.fail(r.stdout+r.stderr)
        result = read(self.root/'output.json'); self.assertEqual(r.returncode, 0 if result['passed'] else 1)
        (self.root/'output.json').unlink(); return result

    def test_valid_development_fixture_contract_and_specific_rejections(self):
        self.assertTrue(self.verify(self.report)['passed'])
        for fault, expected in [('source', 'runtime provenance'), ('runner', 'arena runner'),
                                ('deal', 'exact reserved deal set'), ('episode', 'exact episode set'),
                                ('search_cap', 'truncated search rollouts'), ('search_absent', 'search was not executed')]:
            bad = copy.deepcopy(self.report)
            if fault == 'source': bad['source']['sha256'] = '0'*64
            elif fault == 'runner': bad['arena_runner_sha256'] = '0'*64
            elif fault == 'deal':
                old = bad['results'][0]['gameSeed']
                for row in bad['results']:
                    if row['gameSeed'] == old: row['gameSeed'] = 'discard-opponents-games-v1-2p-999'
            elif fault == 'episode': bad['results'][0]['episode'] = -1
            elif fault == 'search_cap': bad['results'][0]['searchStats']['learner']['truncated'] = 1
            else:
                for row in bad['results']: row['searchStats']['learner']['evaluations'] = 0
            with self.subTest(fault=fault):
                result = self.verify(bad); self.assertFalse(result['passed'])
                self.assertTrue(any(expected in e for e in result['errors']), result['errors'])


class MergeContracts(VerificationContracts):
    def setUp(self):
        super().setUp()
        spec = importlib.util.spec_from_file_location('merge_arena_contract', STRONG/'merge-arena-reports.py')
        self.module = importlib.util.module_from_spec(spec); spec.loader.exec_module(self.module)
        self.shards = []
        for deal in range(2):
            report = copy.deepcopy(self.report)
            report['results'] = [r for r in report['results'] if r['episode']//8 == deal]
            report.update(deal_offset=deal, games=8, run_name=f'unit-contract-{deal}',
                          win_rate=sum(r['win'] for r in report['results'])/8)
            self.shards.append(report)

    def merged(self, reports):
        paths = []
        for i, report in enumerate(reports):
            path = self.root/f'shard-{i}.json'; write(path, report); paths.append(path)
        return self.module.merge(paths)

    def test_recompute_from_raw_disjoint_games(self):
        merged = self.merged(self.shards[::-1])
        self.assertEqual(merged['games'], 16)
        self.assertEqual(merged['independent_seeds'], 2)
        self.assertEqual([r['episode'] for r in merged['results']], list(range(16)))
        self.assertEqual(merged['win_rate'], sum(r['win'] for s in self.shards for r in s['results'])/16)
        self.assertFalse(merged['qualification_checked'])
        self.assertNotIn('inference_p95_ms', merged)  # Percentiles cannot be averaged.

    def test_reject_mixed_or_incomplete_shards(self):
        for fault in ['duplicate', 'gap', 'missing', 'source', 'pairing', 'caps']:
            reports = copy.deepcopy(self.shards)
            if fault == 'duplicate': reports[1] = copy.deepcopy(reports[0])
            elif fault == 'gap': reports[1]['deal_offset'] = 2
            elif fault == 'missing': reports[1]['results'].pop()
            elif fault == 'source': reports[1]['source']['sha256'] = '0'*64
            elif fault == 'pairing':
                rows = reports[1]['results']; rows[0]['episode'], rows[1]['episode'] = rows[1]['episode'], rows[0]['episode']
            else: reports[1]['results'][0]['searchStats']['learner']['truncated'] = 1
            with self.subTest(fault=fault), self.assertRaises(ValueError): self.merged(reports)


if __name__ == '__main__': unittest.main()
