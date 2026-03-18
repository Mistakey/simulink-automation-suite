import unittest

from simulink_cli.core import build_schema_payload


class SchemaActionTests(unittest.TestCase):
    """Unified schema tests — covers all actions in the merged registry."""

    def setUp(self):
        self.schema = build_schema_payload()

    # -- Top-level shape -------------------------------------------------------

    def test_schema_returns_version(self):
        self.assertIn("version", self.schema)
        self.assertEqual(self.schema["version"], "2.0")

    def test_schema_returns_actions(self):
        self.assertIn("actions", self.schema)

    def test_schema_returns_error_codes(self):
        self.assertIn("error_codes", self.schema)

    def test_error_codes_sorted_alphabetically(self):
        codes = self.schema["error_codes"]
        self.assertEqual(codes, sorted(codes))

    # -- All 9 actions present (8 + schema) ------------------------------------

    def test_schema_action_present(self):
        self.assertIn("schema", self.schema["actions"])

    def test_scan_action_present(self):
        self.assertIn("scan", self.schema["actions"])

    def test_connections_action_present(self):
        self.assertIn("connections", self.schema["actions"])

    def test_inspect_action_present(self):
        self.assertIn("inspect", self.schema["actions"])

    def test_find_action_present(self):
        self.assertIn("find", self.schema["actions"])

    def test_highlight_action_present(self):
        self.assertIn("highlight", self.schema["actions"])

    def test_list_opened_action_present(self):
        self.assertIn("list_opened", self.schema["actions"])

    def test_set_param_action_present(self):
        self.assertIn("set_param", self.schema["actions"])

    def test_session_action_present(self):
        self.assertIn("session", self.schema["actions"])

    # -- Connections field metadata (from old scan schema tests) ----------------

    def test_connections_has_description_and_fields(self):
        connections = self.schema["actions"]["connections"]
        self.assertIn("description", connections)
        self.assertIn("fields", connections)

    def test_connections_direction_metadata(self):
        direction_meta = self.schema["actions"]["connections"]["fields"]["direction"]
        self.assertEqual(direction_meta["type"], "string")
        self.assertEqual(direction_meta["default"], "both")
        self.assertEqual(
            direction_meta["enum"], ["upstream", "downstream", "both"]
        )
        self.assertFalse(direction_meta["required"])

    def test_connections_depth_metadata(self):
        depth_meta = self.schema["actions"]["connections"]["fields"]["depth"]
        self.assertEqual(depth_meta["type"], "integer")
        self.assertEqual(depth_meta["default"], 1)
        self.assertFalse(depth_meta["required"])

    def test_connections_target_required(self):
        target_meta = self.schema["actions"]["connections"]["fields"]["target"]
        self.assertTrue(target_meta["required"])
        self.assertEqual(target_meta["type"], "string")

    # -- Find action metadata (from old scan schema tests) ---------------------

    def test_find_action_has_description_and_fields(self):
        find_action = self.schema["actions"]["find"]
        self.assertIn("description", find_action)
        self.assertIn("fields", find_action)

    def test_find_action_field_keys(self):
        find_fields = self.schema["actions"]["find"]["fields"]
        self.assertIn("name", find_fields)
        self.assertIn("block_type", find_fields)
        self.assertIn("max_results", find_fields)

    def test_find_name_metadata(self):
        name_meta = self.schema["actions"]["find"]["fields"]["name"]
        self.assertEqual(name_meta["type"], "string")
        self.assertFalse(name_meta["required"])

    # -- Error codes from scan/connections side ---------------------------------

    def test_engine_unavailable_error_code_present(self):
        self.assertIn("engine_unavailable", self.schema["error_codes"])

    # -- set_param action metadata (from old edit schema tests) ----------------

    def test_set_param_has_description_and_fields(self):
        set_param = self.schema["actions"]["set_param"]
        self.assertIn("description", set_param)
        self.assertIn("fields", set_param)

    def test_set_param_field_keys(self):
        sp_fields = self.schema["actions"]["set_param"]["fields"]
        self.assertIn("target", sp_fields)
        self.assertIn("param", sp_fields)
        self.assertIn("value", sp_fields)
        self.assertIn("dry_run", sp_fields)

    def test_set_param_target_is_required(self):
        target_meta = self.schema["actions"]["set_param"]["fields"]["target"]
        self.assertTrue(target_meta["required"])

    def test_set_param_dry_run_defaults_true(self):
        dry_run_meta = self.schema["actions"]["set_param"]["fields"]["dry_run"]
        self.assertTrue(dry_run_meta["default"])
        self.assertEqual(dry_run_meta["type"], "boolean")

    # -- Error codes from edit side --------------------------------------------

    def test_param_not_found_error_code_present(self):
        self.assertIn("param_not_found", self.schema["error_codes"])

    def test_set_param_failed_error_code_present(self):
        self.assertIn("set_param_failed", self.schema["error_codes"])


if __name__ == "__main__":
    unittest.main()
