import unittest

from skills._shared.errors import make_error
from skills.simulink_edit.scripts.sl_core import _ERROR_CODES


class EditErrorContractTests(unittest.TestCase):
    def test_error_envelope_has_required_keys(self):
        result = make_error("test_code", "Test message")
        self.assertIn("error", result)
        self.assertIn("message", result)
        self.assertIn("details", result)

    def test_error_envelope_with_suggested_fix(self):
        result = make_error("test_code", "Test message", suggested_fix="Do this")
        self.assertIn("suggested_fix", result)
        self.assertEqual(result["suggested_fix"], "Do this")

    def test_param_not_found_in_error_codes(self):
        self.assertIn("param_not_found", _ERROR_CODES)

    def test_set_param_failed_in_error_codes(self):
        self.assertIn("set_param_failed", _ERROR_CODES)

    def test_reused_error_codes_present(self):
        for code in [
            "invalid_input",
            "invalid_json",
            "unknown_parameter",
            "json_conflict",
            "engine_unavailable",
            "no_session",
            "session_required",
            "session_not_found",
            "block_not_found",
            "runtime_error",
        ]:
            self.assertIn(code, _ERROR_CODES, f"Missing reused error code: {code}")


if __name__ == "__main__":
    unittest.main()
