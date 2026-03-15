import argparse
import unittest

from skills.simulink_scan.scripts.sl_core import validate_args
from skills.simulink_scan.scripts.sl_actions import get_model_structure


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
    def test_scan_max_blocks_truncates_and_reports_metadata(self):
        result = get_model_structure(FakeEngine(), model_name="m1", max_blocks=2)
        self.assertEqual(result["total_count"], 3)
        self.assertTrue(result["truncated"])
        self.assertEqual(len(result["blocks"]), 2)

    def test_scan_fields_projects_block_entries(self):
        result = get_model_structure(FakeEngine(), model_name="m1", fields=["name"])
        self.assertTrue(result["blocks"])
        self.assertEqual(sorted(result["blocks"][0].keys()), ["name"])

    def test_validate_args_rejects_non_positive_scan_max_blocks(self):
        args = argparse.Namespace(
            action="scan",
            model="m1",
            subsystem=None,
            recursive=False,
            hierarchy=False,
            session=None,
            max_blocks=0,
            fields=None,
        )
        result = validate_args(args)
        self.assertEqual(result["error"], "invalid_input")


if __name__ == "__main__":
    unittest.main()
