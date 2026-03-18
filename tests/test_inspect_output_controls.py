import unittest
from unittest.mock import patch

from simulink_cli.actions import inspect_block
from tests.fakes import FakeInspectOutputEngine


class InspectOutputControlsTests(unittest.TestCase):
    def _run_inspect(self, **kwargs):
        args = {
            "model": None,
            "target": "m/b",
            "param": "All",
            "active_only": False,
            "strict_active": False,
            "resolve_effective": False,
            "summary": False,
            "session": None,
            "max_params": None,
            "fields": None,
        }
        args.update(kwargs)
        with patch.object(inspect_block, 'safe_connect_to_session',
                          return_value=(FakeInspectOutputEngine(), None)):
            return inspect_block.execute(args)

    def test_inspect_max_params_truncates_and_reports_metadata(self):
        result = self._run_inspect(max_params=1)
        self.assertEqual(result["total_params"], 2)
        self.assertTrue(result["truncated"])
        self.assertEqual(len(result["available_params"]), 1)
        self.assertEqual(len(result["values"]), 1)
        self.assertEqual(len(result["parameter_meta"]), 1)

    def test_inspect_fields_projects_top_level_keys(self):
        result = self._run_inspect(fields=["target", "values"])
        self.assertIn("target", result)
        self.assertIn("values", result)
        self.assertNotIn("available_params", result)
        self.assertNotIn("parameter_meta", result)

    def test_validate_rejects_non_positive_inspect_max_params(self):
        args = {
            "model": None,
            "target": "m/b",
            "param": "All",
            "active_only": False,
            "strict_active": False,
            "resolve_effective": False,
            "summary": False,
            "session": None,
            "max_params": 0,
            "fields": None,
        }
        result = inspect_block.validate(args)
        self.assertEqual(result["error"], "invalid_input")


if __name__ == "__main__":
    unittest.main()
