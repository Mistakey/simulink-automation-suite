import unittest

from skills.simulink_edit.scripts.sl_core import build_parser, parse_request_args


class EditJsonInputModeTests(unittest.TestCase):
    def setUp(self):
        self.parser = build_parser()

    def test_json_flag_exposed(self):
        option_strings = []
        for action in self.parser._actions:
            option_strings.extend(action.option_strings)
        self.assertIn("--json", option_strings)

    def test_accepts_json_set_param_request(self):
        args = parse_request_args(
            self.parser,
            [
                "--json",
                '{"action":"set_param","target":"m/Gain1","param":"Gain","value":"2.0","dry_run":true}',
            ],
        )
        self.assertEqual(args.action, "set_param")
        self.assertEqual(args.target, "m/Gain1")
        self.assertEqual(args.param, "Gain")
        self.assertEqual(args.value, "2.0")

    def test_accepts_json_schema_request(self):
        args = parse_request_args(
            self.parser,
            ["--json", '{"action":"schema"}'],
        )
        self.assertEqual(args.action, "schema")

    def test_rejects_invalid_json(self):
        with self.assertRaises(ValueError) as ctx:
            parse_request_args(self.parser, ["--json", "{invalid"])
        self.assertIn("invalid_json", str(ctx.exception))

    def test_rejects_missing_action(self):
        with self.assertRaises(ValueError) as ctx:
            parse_request_args(
                self.parser,
                ["--json", '{"target":"m/B","param":"P","value":"1"}'],
            )
        self.assertIn("action", str(ctx.exception))

    def test_rejects_unknown_field(self):
        with self.assertRaises(ValueError) as ctx:
            parse_request_args(
                self.parser,
                [
                    "--json",
                    '{"action":"set_param","target":"m/B","param":"P","value":"1","bogus":"x"}',
                ],
            )
        self.assertIn("unknown_parameter", str(ctx.exception))

    def test_rejects_wrong_type(self):
        with self.assertRaises(ValueError) as ctx:
            parse_request_args(
                self.parser,
                [
                    "--json",
                    '{"action":"set_param","target":"m/B","param":"P","value":123}',
                ],
            )
        self.assertIn("invalid_json", str(ctx.exception))

    def test_rejects_mixed_json_and_flags(self):
        with self.assertRaises(ValueError) as ctx:
            parse_request_args(
                self.parser,
                [
                    "set_param",
                    "--target",
                    "m/B",
                    "--json",
                    '{"action":"set_param","target":"m/B","param":"P","value":"1"}',
                ],
            )
        self.assertIn("json_conflict", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
