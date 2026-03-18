import unittest

from simulink_cli.validation import validate_text_field


class SharedValidationTests(unittest.TestCase):
    def test_valid_text_returns_none(self):
        self.assertIsNone(validate_text_field("field", "valid_text"))

    def test_none_value_returns_none(self):
        self.assertIsNone(validate_text_field("field", None))

    def test_empty_string_returns_error(self):
        result = validate_text_field("field", "")
        self.assertEqual(result["error"], "invalid_input")

    def test_control_characters_rejected(self):
        result = validate_text_field("field", "abc\x01def")
        self.assertEqual(result["error"], "invalid_input")

    def test_reserved_characters_rejected(self):
        for char in ("?", "#", "%"):
            result = validate_text_field("field", f"abc{char}def")
            self.assertEqual(result["error"], "invalid_input")

    def test_leading_whitespace_rejected(self):
        result = validate_text_field("field", " leading")
        self.assertEqual(result["error"], "invalid_input")

    def test_trailing_whitespace_rejected(self):
        result = validate_text_field("field", "trailing ")
        self.assertEqual(result["error"], "invalid_input")

    def test_exceeds_max_length_rejected(self):
        result = validate_text_field("field", "x" * 257)
        self.assertEqual(result["error"], "invalid_input")

    def test_custom_max_length(self):
        result = validate_text_field("field", "x" * 11, max_len=10)
        self.assertEqual(result["error"], "invalid_input")


if __name__ == "__main__":
    unittest.main()
