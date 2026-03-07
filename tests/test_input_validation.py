import unittest

from skills.simulink_scan.scripts.sl_core import validate_text_field


class InputValidationTests(unittest.TestCase):
    def test_rejects_control_chars(self):
        result = validate_text_field("target", "abc\x01")
        self.assertEqual(result["error"], "invalid_input")

    def test_rejects_reserved_chars(self):
        for value in ("a?b", "a#b", "a%b"):
            result = validate_text_field("model", value)
            self.assertEqual(result["error"], "invalid_input")

    def test_rejects_trim_mismatch(self):
        result = validate_text_field("session", " MATLAB_1 ")
        self.assertEqual(result["error"], "invalid_input")

    def test_rejects_overlength(self):
        result = validate_text_field("subsystem", "a" * 257)
        self.assertEqual(result["error"], "invalid_input")

    def test_accepts_normal_text(self):
        result = validate_text_field("model", "my_model")
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
