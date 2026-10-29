from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import selected_public_policy_final_source_v1 as source


class FinalSourceTests(unittest.TestCase):
    def setUp(self):
        self.identity = {'policySha256': '1'*64, 'runtimeManifestSha256': '2'*64,
            'modelSha256': '3'*64, 'featureRevision': '4.3-strategic-correction',
            'backend': 'opponent-auction-v1', 'opponentPolicySha256': '4'*64,
            'settings': {'arm': 'auction', 'samples': 8, 'workers': 4, 'threads': 1,
                'max_steps': 2400, 'population_modes': ['neural_population'], 'minimum_advantage': '1/8'}}
        self.candidate = {'status': 'selected', 'frozen_at': '2026-10-29T01:00:00+00:00',
            'identity': self.identity, 'protocol_sha256': source.PROTOCOL_SHA,
            'selection_evidence': {'repo': 'coyotte508/powergrid-ai-germany-v1',
                'revision': '5'*40, 'archive_path': 'archives/synthetic-test-only.tgz', 'archive_sha256': '6'*64}}
        self.workers = {s['name']: 4 for s in source.schedule()}
        self.now = '2026-10-29T02:00:00+00:00'

    def controls(self, candidate=None, workers=None, identity=None, created_at=None, descriptor='policies/conservative_population.json'):
        return source.controls(json.dumps(candidate or self.candidate).encode(), identity or self.identity,
            descriptor, self.workers if workers is None else workers, created_at or self.now)

    def test_all_reserved_deals_rules_seats_and_opponents_preserved(self):
        files, rows = self.controls()
        self.assertEqual([r['shard'] for r in rows], source.schedule())
        self.assertEqual(len(rows), 320)
        self.assertEqual(sum(r['shard']['games'] for r in rows), 20160)
        self.assertEqual(len(files), 640)
        self.assertEqual({r['shard']['players'] for r in rows}, set(range(2, 7)))
        for row in rows:
            job, contract = files[row['job']], files[row['contract']]
            self.assertEqual(contract['identity'], self.identity)
            self.assertEqual(contract['launch_authorization']['name'], row['name'])
            self.assertEqual(job['opponent_model'], 'artifact/final-opponent-a260.onnx' if row['shard']['opponent'] == 'a260' else None)

    def test_exact_candidate_bytes_and_full_search_identity(self):
        data = json.dumps(self.candidate, indent=3).encode()+b'\n'
        files, rows = source.controls(data, self.identity, 'policies/conservative_population.json', self.workers, self.now)
        expected = hashlib.sha256(data).hexdigest()
        self.assertTrue(all(files[r['contract']]['candidate_sha256'] == expected for r in rows))
        altered = deepcopy(self.identity); altered['settings']['workers'] = 8
        with self.assertRaisesRegex(ValueError, 'Complete policy identity'):
            self.controls(identity=altered)

    def test_no_selection_or_freeze_bypass(self):
        for update in ({'status': 'engineering'}, {'selection_evidence': None},
                       {'protocol_sha256': '0'*64}, {'frozen_at': '2026-10-30T00:00:00+00:00'}):
            with self.subTest(update=update), self.assertRaises((ValueError, TypeError)):
                self.controls(candidate={**self.candidate, **update})

    def test_complete_worker_allocation_and_integer_bounds(self):
        name = next(iter(self.workers))
        variants = [{}, {**self.workers, 'unexpected': 4},
                    *({**self.workers, name: value} for value in (0, 33, True, 1.5))]
        for workers in variants:
            with self.subTest(workers_count=len(workers)), self.assertRaises(ValueError):
                self.controls(workers=workers)

    def test_descriptor_cannot_escape_bundle(self):
        for descriptor in ('/tmp/x', '../policy.json', 'a//b', './policy.json', ''):
            with self.subTest(descriptor=descriptor), self.assertRaises(ValueError):
                self.controls(descriptor=descriptor)

    def test_source_symlinks_are_rejected_without_following(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root/'real').write_text('data'); (root/'link').symlink_to(root/'real')
            with self.assertRaisesRegex(ValueError, 'symlink'):
                source.source_files(root)

    def test_existing_partial_or_overlapping_output_is_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); artifact = root/'artifact'; artifact.mkdir(); candidate = root/'candidate.json'
            candidate.write_text(json.dumps(self.candidate)); output = root/'partial'; output.mkdir()
            (output/'intent.json').write_text('original attempt')
            for destination in (output, artifact/'nested', root):
                with self.subTest(destination=str(destination)), self.assertRaises(ValueError):
                    source.build(artifact, 'policy.json', candidate, self.workers, destination)
            self.assertEqual((output/'intent.json').read_text(), 'original attempt')


if __name__ == '__main__':
    unittest.main()
