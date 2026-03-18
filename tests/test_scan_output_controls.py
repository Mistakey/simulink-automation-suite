import unittest
from unittest.mock import patch

from simulink_cli.actions import scan
from tests.fakes import FakeScanOutputEngine


class ScanOutputControlsTests(unittest.TestCase):
    def _run_scan(self, **kwargs):
        args = {
            "model": "m1",
            "subsystem": None,
            "recursive": False,
            "hierarchy": False,
            "session": None,
            "max_blocks": None,
            "fields": None,
        }
        args.update(kwargs)
        with patch.object(scan, 'safe_connect_to_session',
                          return_value=(FakeScanOutputEngine(), None)):
            return scan.execute(args)

    def test_scan_max_blocks_truncates_and_reports_metadata(self):
        result = self._run_scan(max_blocks=2)
        self.assertEqual(result["total_count"], 3)
        self.assertTrue(result["truncated"])
        self.assertEqual(len(result["blocks"]), 2)

    def test_scan_fields_projects_block_entries(self):
        result = self._run_scan(fields=["name"])
        self.assertTrue(result["blocks"])
        self.assertEqual(sorted(result["blocks"][0].keys()), ["name"])

    def test_validate_rejects_non_positive_scan_max_blocks(self):
        args = {
            "model": "m1",
            "subsystem": None,
            "recursive": False,
            "hierarchy": False,
            "session": None,
            "max_blocks": 0,
            "fields": None,
        }
        result = scan.validate(args)
        self.assertEqual(result["error"], "invalid_input")


if __name__ == "__main__":
    unittest.main()
