"""Complete-index/archive-admission tests using synthetic records only."""
from copy import deepcopy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('comparison_cli', Path(__file__).with_name('compare-current-auction-confirmation-v1.py'))
cli = importlib.util.module_from_spec(spec); spec.loader.exec_module(cli)

class CompletionAdmissionTests(unittest.TestCase):
    def fixture(self):
        # Small synthetic job index for admission arithmetic only; not actual receipts.
        rows = [{'name': f'job{i}', 'shard': {'games': 13440}} for i in range(2)]
        jobs = [{'name': r['name'], 'row': r, 'job_id': format(i+1, '024x'), 'verified': True,
                 'stage': 'COMPLETED', 'review': {'games': 13440, 'audit': {'all_receipts_verified': True,
                 'reserved_final_seeds_used': False, 'counts': {'rollout_caps': 0}}}} for i, r in enumerate(rows)]
        return {'rows': rows}, {'complete': True, 'verified_jobs': 2, 'expected_jobs': 2, 'jobs': jobs,
                              'qualified': False, 'reserved_final_seeds_used': False}

    def test_incomplete_failed_duplicate_or_wrong_source_jobs_rejected(self):
        source, report = self.fixture(); self.assertEqual(len(cli.completion_index(source, report)), 2)
        edits = [lambda r: r.update(complete=False), lambda r: r['jobs'].pop(),
                 lambda r: r['jobs'][0].update(stage='ERROR'), lambda r: r['jobs'][0].update(verified=False),
                 lambda r: r['jobs'][1].update(job_id=r['jobs'][0]['job_id']),
                 lambda r: r['jobs'][1].update(name=r['jobs'][0]['name']),
                 lambda r: r['jobs'][0]['review']['audit']['counts'].update(rollout_caps=1),
                 lambda r: r['jobs'][0]['review'].update(games=13439),
                 lambda r: r['jobs'][0].update(row={'name': 'other'})]
        for edit in edits:
            r = deepcopy(report); edit(r)
            with self.subTest(edit=edit), self.assertRaises(ValueError): cli.completion_index(source, r)

    def test_cli_refuses_live_partial_execution_without_side_effects(self):
        with tempfile.TemporaryDirectory() as tmp:
            owner = Path(tmp)/'owner.json'; owner.write_text(json.dumps({'stage': 'waiting_for_original_pilots'}))
            output = Path(tmp)/'result.json'
            with patch.object(cli, 'OWNER', owner), patch.object(cli, 'manager_module') as manager:
                with self.assertRaisesRegex(ValueError, 'Wait for complete'): cli.compare(output)
                manager.assert_not_called()
            self.assertFalse(output.exists()); self.assertFalse(output.with_suffix('.intent.json').exists())

    def test_existing_intent_requires_inspection_not_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)/'result.json'; output.with_suffix('.intent.json').write_text('{}')
            with patch.object(cli, 'manager_module') as manager:
                with self.assertRaisesRegex(ValueError, 'Inspect existing'): cli.compare(output)
                manager.assert_not_called()

    def test_archive_bytes_and_internal_manifest_must_both_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp)/'case.tgz'; manifest = b'{"game.json": "synthetic-only"}'
            with tarfile.open(archive, 'w:gz') as bundle:
                info = tarfile.TarInfo('manifest.json'); info.size = len(manifest)
                bundle.addfile(info, io.BytesIO(manifest))
            evidence = {'repo': 'coyotte508/powergrid-ai-germany-v1', 'archive_path': 'archives/case.tgz',
                'remote_archive_verified': True, 'revision': 'a'*40,
                'archive_sha256': cli.digest(archive), 'manifest_sha256': hashlib.sha256(manifest).hexdigest()}
            with patch.object(cli, 'hf_hub_download', return_value=str(archive)) as download:
                cli.immutable_archive(evidence, 'case')
                download.assert_called_once_with(evidence['repo'], evidence['archive_path'], revision='a'*40)
                for field in ('archive_sha256', 'manifest_sha256', 'revision', 'archive_path'):
                    broken = {**evidence, field: 'b'*64}
                    with self.subTest(field=field), self.assertRaises(ValueError): cli.immutable_archive(broken, 'case')

    def test_duplicate_archive_manifests_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp)/'case.tgz'
            with tarfile.open(archive, 'w:gz') as bundle:
                for _ in range(2):
                    info = tarfile.TarInfo('manifest.json'); info.size = 2
                    bundle.addfile(info, io.BytesIO(b'{}'))
            evidence = {'repo': 'coyotte508/powergrid-ai-germany-v1', 'archive_path': 'archives/case.tgz',
                'remote_archive_verified': True, 'revision': 'a'*40,
                'archive_sha256': cli.digest(archive), 'manifest_sha256': hashlib.sha256(b'{}').hexdigest()}
            with patch.object(cli, 'hf_hub_download', return_value=str(archive)):
                with self.assertRaisesRegex(ValueError, 'duplicate'): cli.immutable_archive(evidence, 'case')


if __name__ == '__main__': unittest.main()
