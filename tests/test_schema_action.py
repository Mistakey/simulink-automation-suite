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
        self.assertIn("actions", result)
        self.assertIn("connections", result["actions"])
        self.assertIn("scan", result["actions"])
        self.assertIn("inspect", result["actions"])
        self.assertIn("session", result["actions"])
        self.assertIn("error_codes", result)

    def test_schema_action_includes_engine_unavailable_error_code(self):
        args = parse_request_args(self.parser, ["schema"])
        result = run_action(args)
        self.assertIn("engine_unavailable", result["error_codes"])


if __name__ == "__main__":
    unittest.main()
