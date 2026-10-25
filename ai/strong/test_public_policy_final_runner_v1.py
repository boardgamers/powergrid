"""Admission/lifecycle contracts; no real games or reserved seed consumption."""
import contextlib
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from public_policy_final_audit_v1 import PROTOCOL_SHA, digest, schedule
from public_policy_final_contract_v1 import admit, audit_execution_binding, fingerprint
import public_policy_final_runner_v1 as runner
from test_public_policy_final_audit_v1 import identity


def documents(final=False):
    selected = identity(True)
    candidate = {'status': 'selected' if final else 'engineering',
                 'frozen_at': '2026-10-25T00:00:00+00:00', 'identity': selected,
                 'protocol_sha256': PROTOCOL_SHA, 'selection_evidence':
                 {'repo': 'coyotte508/powergrid-ai-germany-v1', 'revision': '1'*40,
                  'archive_path': 'archives/synthetic-contract-fixture.tgz', 'archive_sha256': '2'*64} if final else None}
    sha = '3'*64
    shard = schedule()[0] if final else {'name': 'wrapper-engineering-2p', 'group': 'economic/2p',
        'players': 2, 'start': 4, 'deals': 1, 'seed': 'wrapper-engineering', 'opponent': 'economic',
        'opponent_sha256': None, 'games': 8}
    contract = {'version': 1, 'purpose': 'final' if final else 'engineering',
                'created_at': '2026-10-25T00:00:01+00:00', 'candidate_sha256': sha,
                'protocol_sha256': PROTOCOL_SHA, 'identity': selected, 'shard': shard,
                'launch_authorization': {'stage': 'launch_intent', 'name': shard['name'],
                    'candidate_sha256': sha, 'run_fingerprint': fingerprint(sha, selected)} if final else None}
    return contract, candidate, sha, selected


class FinalRunnerContracts(unittest.TestCase):
    def test_engineering_admission_retains_nonzero_deal_offset(self):
        contract, candidate, sha, selected = documents()
        admitted = admit(contract, candidate, sha, selected)
        self.assertFalse(admitted['reserved']); self.assertEqual(admitted['shard']['start'], 4)

    def test_engineering_cannot_use_reserved_seed_or_claim_selection(self):
        for field in ('name', 'seed', 'group'):
            contract, candidate, sha, selected = documents()
            contract['shard'][field] = 'strong-multiplayer-final-reserved-v1'
            with self.subTest(field=field), self.assertRaises(ValueError): admit(contract, candidate, sha, selected)
        contract, candidate, sha, selected = documents(); candidate['status'] = 'selected'
        with self.assertRaises(ValueError): admit(contract, candidate, sha, selected)

    def test_final_requires_selection_immutable_evidence_and_exact_intent(self):
        contract, candidate, sha, selected = documents(True)
        self.assertTrue(admit(contract, candidate, sha, selected)['reserved'])
        for change in [{'status': 'engineering'}, {'selection_evidence': None},
                       {'frozen_at': '2026-10-25T00:01:00+00:00'}]:
            with self.subTest(change=change), self.assertRaises(ValueError):
                admit(contract, {**candidate, **change}, sha, selected)
        for authorization in [None, {}, {**contract['launch_authorization'], 'name': 'different'},
                              {**contract['launch_authorization'], 'run_fingerprint': '4'*64}]:
            with self.subTest(authorization=authorization), self.assertRaises(ValueError):
                admit({**contract, 'launch_authorization': authorization}, candidate, sha, selected)

    def test_changed_policy_candidate_protocol_and_shard_are_rejected(self):
        contract, candidate, sha, selected = documents(True)
        for change in [{'identity': identity()}, {'candidate_sha256': '5'*64},
                       {'protocol_sha256': '6'*64}, {'shard': {**contract['shard'], 'start': 4}},
                       {'version': True}]:
            with self.subTest(change=change), self.assertRaises(ValueError):
                admit({**contract, **change}, candidate, sha, selected)

    def test_unpinned_selection_and_incomplete_engineering_deal_are_rejected(self):
        contract, candidate, sha, selected = documents(True)
        candidate['selection_evidence']['revision'] = 'main'
        with self.assertRaises(ValueError): admit(contract, candidate, sha, selected)
        contract, candidate, sha, selected = documents(); contract['shard']['games'] = 7
        with self.assertRaises(ValueError): admit(contract, candidate, sha, selected)

    def test_saved_binding_rechecks_exact_candidate_and_contract_bytes(self):
        contract, candidate, _, selected = documents()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'candidate.json').write_text(json.dumps(candidate))
            sha = digest(root/'candidate.json'); contract['candidate_sha256'] = sha
            (root/'contract.json').write_text(json.dumps(contract))
            binding = {**admit(contract, candidate, sha, selected),
                       'contract_sha256': digest(root/'contract.json'), 'runner_sha256': '7'*64, 'purpose': 'engineering'}
            (root/'evaluation.json').write_text(json.dumps({'execution_binding': binding, 'reserved_final_seeds_used': False}))
            self.assertEqual(audit_execution_binding(root, selected, '7'*64), binding)
            (root/'candidate.json').write_text(json.dumps(candidate)+'\n')
            with self.assertRaises(ValueError): audit_execution_binding(root, selected, '7'*64)

    def test_existing_output_cannot_restart_original_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileExistsError), patch.object(runner.arena, 'play') as play:
                runner.execute({'output': tmp}, {})
            play.assert_not_called()

    def test_default_is_validation_only(self):
        args = ['runner', '--artifact', '/synthetic', '--candidate', '/synthetic-candidate',
                '--contract', '/synthetic-contract', '--output', '/never-created']
        with patch.object(sys, 'argv', args), patch.object(runner, 'configuration', return_value=({}, {})), \
             patch.object(runner, 'execute') as execute, contextlib.redirect_stdout(io.StringIO()):
            runner.main()
        execute.assert_not_called()


if __name__ == '__main__':
    unittest.main()
