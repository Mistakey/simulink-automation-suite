import unittest

from skills.simulink_edit.scripts.sl_core import build_parser, run_action, validate_args


class EditInputValidationTests(unittest.TestCase):
    def setUp(self):
        self.parser = build_parser()

    def test_missing_target_returns_error(self):
        args = self.parser.parse_args(["set_param", "--target", "", "--param", "P", "--value", "1"])
        result = validate_args(args)
        self.assertIsNotNone(result)
        self.assertEqual(result["error"], "invalid_input")

    def test_missing_param_returns_error(self):
        args = self.parser.parse_args(["set_param", "--target", "m/B", "--param", "", "--value", "1"])
        result = validate_args(args)
        self.assertIsNotNone(result)
        self.assertEqual(result["error"], "invalid_input")

    def test_control_characters_in_target_rejected(self):
        args = self.parser.parse_args(["set_param", "--target", "m/B\x01", "--param", "P", "--value", "1"])
        result = validate_args(args)
        self.assertIsNotNone(result)
        self.assertEqual(result["error"], "invalid_input")

    def test_reserved_characters_in_param_rejected(self):
        args = self.parser.parse_args(["set_param", "--target", "m/B", "--param", "P?", "--value", "1"])
        result = validate_args(args)
        self.assertIsNotNone(result)
        self.assertEqual(result["error"], "invalid_input")

    def test_valid_args_returns_none(self):
        args = self.parser.parse_args(["set_param", "--target", "m/B", "--param", "Gain", "--value", "2.0"])
        result = validate_args(args)
        self.assertIsNone(result)

    def test_schema_returns_none(self):
        args = self.parser.parse_args(["schema"])
        result = validate_args(args)
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
