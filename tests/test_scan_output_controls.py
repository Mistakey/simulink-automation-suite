import unittest
from unittest import mock

from simulink_cli.actions import scan


class FakeEngine:
    def find_system(self, *args):
        if args == ("Type", "block_diagram"):
            return ["m1"]
        scan_root = args[0]
        return [scan_root, f"{scan_root}/C", f"{scan_root}/A", f"{scan_root}/B"]

    def bdroot(self):
        return "m1"

    def get_param(self, block_path, param_name):
        if param_name == "Handle":
            return 1
        if param_name == "BlockType":
            return "Gain"
        raise RuntimeError("unsupported")


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
        with mock.patch(
            "simulink_cli.actions.scan.safe_connect_to_session",
            return_value=(FakeEngine(), None),
        ):
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
