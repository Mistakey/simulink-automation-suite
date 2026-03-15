import unittest

from skills.simulink_scan.scripts.sl_core import build_parser, parse_request_args, run_action


class SchemaActionTests(unittest.TestCase):
    def setUp(self):
        self.parser = build_parser()

    def test_parser_accepts_schema_action(self):
        args = parse_request_args(self.parser, ["schema"])
        self.assertEqual(args.action, "schema")

    def test_json_mode_accepts_schema_action(self):
        args = parse_request_args(self.parser, ['--json', '{"action":"schema"}'])
        self.assertEqual(args.action, "schema")

    def test_run_action_schema_returns_machine_contract(self):
        args = parse_request_args(self.parser, ["schema"])
        result = run_action(args)
        self.assertIn("version", result)
        self.assertIn("actions", result)
        self.assertIn("connections", result["actions"])
        self.assertIn("scan", result["actions"])
        self.assertIn("inspect", result["actions"])
        self.assertIn("session", result["actions"])
        self.assertIn("error_codes", result)

    def test_schema_connections_field_metadata_shape(self):
        args = parse_request_args(self.parser, ["schema"])
        result = run_action(args)
        connections = result["actions"]["connections"]
        self.assertIn("description", connections)
        self.assertIn("fields", connections)

        direction_meta = connections["fields"]["direction"]
        self.assertEqual(direction_meta["type"], "string")
        self.assertEqual(direction_meta["default"], "both")
        self.assertEqual(
            direction_meta["enum"], ["upstream", "downstream", "both"]
        )
        self.assertFalse(direction_meta["required"])

        depth_meta = connections["fields"]["depth"]
        self.assertEqual(depth_meta["type"], "integer")
        self.assertEqual(depth_meta["default"], 1)
        self.assertFalse(depth_meta["required"])

        target_meta = connections["fields"]["target"]
        self.assertTrue(target_meta["required"])
        self.assertEqual(target_meta["type"], "string")

    def test_schema_action_includes_engine_unavailable_error_code(self):
        args = parse_request_args(self.parser, ["schema"])
        result = run_action(args)
        self.assertIn("engine_unavailable", result["error_codes"])

    def test_find_action_in_schema(self):
        result = run_action(self.parser.parse_args(["schema"]))
        self.assertIn("find", result["actions"])
        find_action = result["actions"]["find"]
        self.assertIn("description", find_action)
        self.assertIn("fields", find_action)
        self.assertIn("name", find_action["fields"])
        self.assertIn("block_type", find_action["fields"])
        self.assertIn("max_results", find_action["fields"])
        name_meta = find_action["fields"]["name"]
        self.assertEqual(name_meta["type"], "string")
        self.assertFalse(name_meta["required"])


if __name__ == "__main__":
    unittest.main()
