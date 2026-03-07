import unittest

from skills.simulink_scan.scripts.sl_core import build_parser, parse_request_args


class JsonInputModeTests(unittest.TestCase):
    def setUp(self):
        self.parser = build_parser()

    def test_build_parser_exposes_json_flag(self):
        option_strings = []
        for action in self.parser._actions:
            option_strings.extend(action.option_strings)
        self.assertIn("--json", option_strings)

    def test_parse_request_args_accepts_json_scan_request(self):
        args = parse_request_args(
            self.parser,
            ['--json', '{"action":"scan","model":"demo","recursive":true}'],
        )
        self.assertEqual(args.action, "scan")
        self.assertEqual(args.model, "demo")
        self.assertTrue(args.recursive)

    def test_parse_request_args_rejects_invalid_json_payload(self):
        with self.assertRaises(ValueError) as context:
            parse_request_args(self.parser, ["--json", "{invalid-json"])
        self.assertIn("invalid_json", str(context.exception))

    def test_parse_request_args_requires_action_field(self):
        with self.assertRaises(ValueError) as context:
            parse_request_args(self.parser, ['--json', '{"model":"demo"}'])
        self.assertIn("action", str(context.exception))

    def test_parse_request_args_rejects_mixed_json_and_flags(self):
        with self.assertRaises(ValueError) as context:
            parse_request_args(
                self.parser,
                [
                    "scan",
                    "--model",
                    "demo",
                    "--json",
                    '{"action":"scan","model":"demo"}',
                ],
            )
        self.assertIn("json_conflict", str(context.exception))

    def test_parse_request_args_rejects_unknown_json_field(self):
        with self.assertRaises(ValueError) as context:
            parse_request_args(
                self.parser,
                ['--json', '{"action":"scan","model":"demo","unknown":"x"}'],
            )
        self.assertIn("unknown_parameter", str(context.exception))

    def test_parse_request_args_rejects_wrong_json_value_type(self):
        with self.assertRaises(ValueError) as context:
            parse_request_args(self.parser, ['--json', '{"action":"scan","model":123}'])
        self.assertIn("invalid_json", str(context.exception))


if __name__ == "__main__":
    unittest.main()
