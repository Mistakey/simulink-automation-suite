import unittest

from simulink_cli.core import build_schema_payload


class SchemaActionTests(unittest.TestCase):
    """Schema contract tests — validates the agent-facing API surface."""

    def setUp(self):
        self.schema = build_schema_payload()

    def test_schema_returns_version(self):
        self.assertEqual(self.schema["version"], "2.8")

    def test_all_actions_present_with_description_and_fields(self):
        expected = {
            "schema", "scan", "connections", "inspect", "find",
            "highlight", "list_opened", "matlab_eval", "set_param", "session",
            "model_new", "model_open", "model_save", "model_close", "model_update",
            "block_add", "block_delete", "line_add", "line_delete", "simulate",
        }
        self.assertEqual(set(self.schema["actions"].keys()), expected)
        for name, action in self.schema["actions"].items():
            if name != "schema":
                self.assertIn("description", action, f"{name} missing description")
                self.assertIn("fields", action, f"{name} missing fields")

    def test_error_codes_sorted_alphabetically(self):
        codes = self.schema["error_codes"]
        self.assertEqual(codes, sorted(codes))

    def test_framework_error_codes_present(self):
        for code in (
            "invalid_input",
            "invalid_json",
            "json_conflict",
            "unknown_parameter",
        ):
            self.assertIn(code, self.schema["error_codes"])

    def test_set_param_dry_run_defaults_true(self):
        meta = self.schema["actions"]["set_param"]["fields"]["dry_run"]
        self.assertTrue(meta["default"])
        self.assertEqual(meta["type"], "boolean")

    def test_set_param_critical_fields_present(self):
        fields = self.schema["actions"]["set_param"]["fields"]
        for name in ("target", "param", "value", "dry_run", "expected_current_value"):
            self.assertIn(name, fields, f"set_param missing field: {name}")


if __name__ == "__main__":
    unittest.main()
