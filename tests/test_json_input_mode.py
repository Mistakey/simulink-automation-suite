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

    def test_parse_request_args_accepts_json_connections_request(self):
        args = parse_request_args(
            self.parser,
            [
                "--json",
                '{"action":"connections","target":"m1/Gain","direction":"both","depth":1,"detail":"summary","max_edges":20,"fields":["target","edges"]}',
            ],
        )
        self.assertEqual(args.action, "connections")
        self.assertEqual(args.target, "m1/Gain")
        self.assertEqual(args.direction, "both")
        self.assertEqual(args.depth, 1)
        self.assertEqual(args.detail, "summary")
        self.assertEqual(args.max_edges, 20)
        self.assertEqual(args.fields, "target,edges")

    def test_parse_request_args_rejects_wrong_connections_include_handles_type(self):
        with self.assertRaises(ValueError) as context:
            parse_request_args(
                self.parser,
                [
                    "--json",
                    '{"action":"connections","target":"m1/Gain","include_handles":"yes"}',
                ],
            )
        self.assertIn("invalid_json", str(context.exception))

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

    def test_parse_request_args_accepts_json_find_request(self):
        args = parse_request_args(
            self.parser,
            [
                "--json",
                '{"action":"find","model":"my_model","name":"PID","block_type":"SubSystem","max_results":50,"fields":["path","type"]}',
            ],
        )
        self.assertEqual(args.action, "find")
        self.assertEqual(args.model, "my_model")
        self.assertEqual(args.name, "PID")
        self.assertEqual(args.block_type, "SubSystem")
        self.assertEqual(args.max_results, 50)
        self.assertEqual(args.fields, "path,type")


if __name__ == "__main__":
    unittest.main()
