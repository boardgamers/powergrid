"""Pairing, complete-data, public-root and terminal-credit regression checks."""
from copy import deepcopy
from fractions import Fraction
import importlib.util
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from strategic_collection import ROOT, read, write, digest
from hybrid_search import Model
from surrogate_continuation_roots_v1 import object_hash
from surrogate_continuation_study_v1 import (STRONG, MODES, check_root, exact_credit, paired_root,
                                            verify_result, verify_chunk, code_hashes, PROTOCOL, policy_digest, run_chunk)
from surrogate_opponent_continuations_v1 import SurrogateContinuationProbe

REAL = ROOT/'ai/runs/surrogate-continuation-roots-runtime-collected-v1/surrogate-continuation-runtime-v1-2p-0-1/artifacts/games'
MODEL = ROOT/'ai/runs/policy-iteration-trained-8840u-prepared-v2/local-package-frozen-1/policy.onnx'


def synthetic(root, mode, begin=0, count=8):
    rows = []; n = root['identity']['players']; seat = root['identity']['seat']
    for sample in range(begin, begin+count):
        roles = ['neural' if p == seat else ('search_geo' if mode == 'reference_opponent_v1' else 'surrogate' if mode == 'surrogate_opponent_v1' else 'economic') for p in range(n)]
        for action in range(2):
            terminal = [{'powered': 17, 'money': 1, 'cities': 17} for _ in range(n)]
            if action: terminal[seat]['money'] = 2
            rows.append({'env': len(rows), 'sample': sample, 'actionIndex': root['options'][action],
                'steps': 1, 'truncated': False, 'value': float(exact_credit(terminal, seat, n)),
                'roles': roles, 'searchStats': {'decisions': 0, 'evaluations': 0, 'truncated': 0},
                'policyDecisions': {'neural': 1, 'forced': 0},
                'initialBelief': {'kind': mode, 'committed': [{'actor': p, 'role': roles[p], 'action': {'name': 'Pass', 'data': True}} for p in root['prior_actors']]},
                'diagnostic': {'sampledWorldSha256': object_hash(['synthetic', sample]),
                               'priorSearchStats': {'decisions': 0, 'evaluations': 0, 'truncated': 0}, 'terminal': terminal}})
    return {'mode': mode, 'options': root['options'], 'samples': 8, 'begin': begin, 'count': count,
            'rows': rows, 'inference_decisions': {'neural': 2*count, 'surrogate': 0}, 'seconds': .01,
            'caps': 0, 'outer_caps': 0, 'nested_caps': 0, 'usable': True,
            'worker_sha256': digest(STRONG/'surrogate-opponent-continuations-v1.cjs'), 'qualification_eligible': False}


class StudyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = read(REAL/'game-0/roots.json')['roots']['bid']

    def modes(self): return {mode: [synthetic(self.root, mode)] for mode in MODES}

    def test_public_roots_recompute_all_twenty_four_focal_pairs(self):
        proof = read(ROOT/'ai/runs/reference-opponent-diagnostic-v2/protocol.json')
        os.environ['PG_REFERENCE_RUNTIME'] = proof['runtime']
        model = Model(MODEL, threads=1); probe = SurrogateContinuationProbe(model, None)
        try:
            roots = [root for path in sorted(REAL.glob('game-*/roots.json')) for root in read(path)['roots'].values()]
            self.assertEqual(len(roots), 24)
            for root in roots: check_root(root, probe)
            for edit in ('private', 'proposal', 'alternative', 'rank'):
                root = deepcopy(self.root)
                if edit == 'private':
                    root['request']['state']['seed'] = 'private-game-seed'; root['public_root_sha256'] = object_hash(root['request'])
                elif edit == 'proposal': root['model_proposal'] = (root['model_proposal']+1) % len(root['moves'])
                elif edit == 'alternative': root['options'].reverse()
                else: root['rank'] = '0'*64
                with self.assertRaises(AssertionError): check_root(root, probe)
        finally: probe.close()

    def test_exact_ties_and_pairing_across_partitions(self):
        terminal = [{'powered': 10, 'money': 3, 'cities': 12} for _ in range(3)]
        self.assertEqual(exact_credit(terminal, 0, 3), Fraction(1, 3))
        modes = self.modes(); left = paired_root(self.root, modes)
        self.assertEqual(left['margins'], {mode: [1, 2] for mode in MODES})
        for mode in MODES: modes[mode] = [synthetic(self.root, mode, 4, 4), synthetic(self.root, mode, 0, 4)]
        self.assertEqual(paired_root(self.root, modes), left)

    def test_omitted_duplicate_and_cross_mode_worlds_rejected(self):
        for kind in ('missing', 'duplicate', 'different_world', 'different_action_world', 'different_belief'):
            modes = self.modes(); mode = MODES[0]
            if kind == 'missing': modes[mode] = [synthetic(self.root, mode, 0, 7)]
            elif kind == 'duplicate': modes[mode].append(synthetic(self.root, mode, 0, 1))
            elif kind == 'different_world':
                for row in modes[mode][0]['rows'][:2]: row['diagnostic']['sampledWorldSha256'] = 'a'*64
            elif kind == 'different_action_world': modes[mode][0]['rows'][0]['diagnostic']['sampledWorldSha256'] = 'b'*64
            else: modes[mode][0]['rows'][0]['initialBelief']['committed'][0]['action'] = {'name': 'Bid', 'data': 100}
            with self.assertRaises(AssertionError): paired_root(self.root, modes)

    def test_wrong_terminal_credit_and_prior_actor_rejected(self):
        for kind in ('credit', 'terminal', 'actor', 'counter'):
            result = synthetic(self.root, MODES[0])
            if kind == 'credit': result['rows'][0]['value'] = 1
            elif kind == 'terminal': result['rows'][0]['diagnostic']['terminal'][0]['money'] = -1
            elif kind == 'actor': result['rows'][0]['initialBelief']['committed'] = []
            else: result['inference_decisions']['neural'] += 1
            with self.assertRaises(AssertionError): verify_result(self.root, result, MODES[0], 0, 8)

    def test_outer_and_nested_caps_retained_without_margin(self):
        for nested in (False, True):
            modes = self.modes(); mode = 'reference_opponent_v1'; r = modes[mode][0]; row = r['rows'][0]
            r.update(caps=1, usable=False)
            if nested:
                r['nested_caps'] = 1; row['searchStats'] = {'decisions': 1, 'evaluations': 16, 'truncated': 1}
            else:
                r['outer_caps'] = 1; row.update(truncated=True, value=None, steps=2400)
                row['policyDecisions']['neural'] = 2400; r['inference_decisions']['neural'] += 2399
                row['diagnostic']['terminal'] = None
            result = paired_root(self.root, modes)
            self.assertFalse(result['complete']); self.assertEqual(result['caps'], 1); self.assertIsNone(result['margins'])
            self.assertEqual(len(result['mode_credits'][mode]), 8)

    def test_immutable_receipt_checks_even_after_resealing(self):
        mode = 'surrogate_opponent_v1'
        policy = read(ROOT/'ai/runs/surrogate-opponent-integration-v1/untrained-fixture/policy.json')
        model_sha = policy_digest(policy)
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp); result = synthetic(self.root, mode)
            intent = {'root_sha256': object_hash(self.root), 'public_root_sha256': self.root['public_root_sha256'],
                      'mode': mode, 'begin': 0, 'count': 8, 'samples': 8, 'max_steps': 2400,
                      'focal_model_sha256': read(PROTOCOL)['focal_model_sha256'], 'surrogate_policy_sha256': model_sha,
                      'protocol_sha256': digest(PROTOCOL), 'code_hashes': code_hashes(), 'gradients': False,
                      'qualification_eligible': False, 'reserved_final_seeds_used': False}
            write(folder/'intent.json', intent); write(folder/'root.json', self.root); write(folder/'result.json', result)
            write(folder/'policy.json', policy)
            status = {**intent, 'stage': 'complete', 'caps': 0, 'rows': 16, 'result_sha256': digest(folder/'result.json')}
            write(folder/'status.json', status)
            self.assertEqual(verify_chunk(folder, self.root, surrogate_sha256=model_sha), result)
            with self.assertRaises(AssertionError): verify_chunk(folder, self.root, surrogate_sha256='d'*64)
            result['rows'][0]['value'] = .123; write(folder/'result.json', result)
            status['result_sha256'] = digest(folder/'result.json'); write(folder/'status.json', status)
            with self.assertRaises(AssertionError): verify_chunk(folder, self.root, surrogate_sha256=model_sha)

    def test_wrong_loaded_policy_refuses_before_execution_or_output(self):
        policy = read(ROOT/'ai/runs/surrogate-opponent-integration-v1/untrained-fixture/policy.json')
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)/'chunk'
            with self.assertRaisesRegex(AssertionError, 'Loaded opponent policy'):
                run_chunk(self.root, 'surrogate_opponent_v1', 0, 8,
                          SimpleNamespace(sha256=read(PROTOCOL)['focal_model_sha256']),
                          SimpleNamespace(policy=policy), output, surrogate_sha256='f'*64)
            self.assertFalse(output.exists())

    def test_premature_full_study_refuses_before_output(self):
        spec = importlib.util.spec_from_file_location('study_prepare_test', STRONG/'prepare-surrogate-continuation-study-v1.py')
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        self.assertFalse(module.OUT.exists())
        with self.assertRaisesRegex(AssertionError, 'fresh-root'): module.prepare()
        self.assertFalse(module.OUT.exists())


if __name__ == '__main__': unittest.main()
