import unittest

from skills.simulink_edit.scripts.sl_core import build_parser, run_action


class EditSchemaActionTests(unittest.TestCase):
    def setUp(self):
        self.parser = build_parser()

    def test_schema_returns_actions(self):
        result = run_action(self.parser.parse_args(["schema"]))
        self.assertIn("actions", result)
        self.assertIn("schema", result["actions"])
        self.assertIn("set_param", result["actions"])

    def test_schema_returns_error_codes(self):
        result = run_action(self.parser.parse_args(["schema"]))
        self.assertIn("error_codes", result)
        self.assertIn("param_not_found", result["error_codes"])
        self.assertIn("set_param_failed", result["error_codes"])

    def test_schema_returns_version(self):
        result = run_action(self.parser.parse_args(["schema"]))
        self.assertIn("version", result)

    def test_set_param_action_in_schema(self):
        result = run_action(self.parser.parse_args(["schema"]))
        set_param_action = result["actions"]["set_param"]
        self.assertIn("description", set_param_action)
        self.assertIn("fields", set_param_action)
        self.assertIn("target", set_param_action["fields"])
        self.assertIn("param", set_param_action["fields"])
        self.assertIn("value", set_param_action["fields"])
        self.assertIn("dry_run", set_param_action["fields"])

    def test_set_param_target_is_required(self):
        result = run_action(self.parser.parse_args(["schema"]))
        target_meta = result["actions"]["set_param"]["fields"]["target"]
        self.assertTrue(target_meta["required"])

    def test_set_param_dry_run_defaults_true(self):
        result = run_action(self.parser.parse_args(["schema"]))
        dry_run_meta = result["actions"]["set_param"]["fields"]["dry_run"]
        self.assertTrue(dry_run_meta["default"])
        self.assertEqual(dry_run_meta["type"], "boolean")


if __name__ == "__main__":
    unittest.main()
