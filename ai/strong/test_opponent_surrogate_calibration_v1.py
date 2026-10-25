"""A partial calibration cannot create an archive or permit full collection."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('surrogate_calibration',Path(__file__).with_name('collect-opponent-surrogate-calibration-v1.py'))
collector=importlib.util.module_from_spec(spec);spec.loader.exec_module(collector)


class CalibrationAdmissionTest(unittest.TestCase):
    def test_missing_endpoint_refuses_before_upload_or_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            with patch.object(collector.endpoint,'COLLECTED',root), patch.object(collector,'upload_evidence') as upload:
                for archive in (False,True):
                    with self.assertRaisesRegex(AssertionError,'Both original HF endpoints'):
                        collector.main(archive)
                upload.assert_not_called()
                self.assertEqual(list(root.iterdir()),[])


if __name__=='__main__':unittest.main()
