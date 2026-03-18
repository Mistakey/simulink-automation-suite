import unittest

from simulink_cli.errors import make_error
from simulink_cli.core import build_schema_payload, map_value_error


class ErrorContractTests(unittest.TestCase):
    def test_make_error_has_stable_shape(self):
        payload = make_error("model_not_found", "Model not opened")
        self.assertEqual(payload["error"], "model_not_found")
        self.assertEqual(payload["message"], "Model not opened")
        self.assertIn("details", payload)
        self.assertEqual(payload["details"], {})

    def test_make_error_accepts_details_and_suggested_fix(self):
        payload = make_error(
            "session_required",
            "Multiple sessions found",
            details={"sessions": ["MATLAB_A", "MATLAB_B"]},
            suggested_fix="Run session list and pass --session.",
        )
        self.assertEqual(payload["error"], "session_required")
        self.assertEqual(payload["details"]["sessions"], ["MATLAB_A", "MATLAB_B"])
        self.assertEqual(
            payload["suggested_fix"],
            "Run session list and pass --session.",
        )

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
        error_codes = build_schema_payload()["error_codes"]
        self.assertIn("param_not_found", error_codes)

    def test_set_param_failed_in_error_codes(self):
        error_codes = build_schema_payload()["error_codes"]
        self.assertIn("set_param_failed", error_codes)

    def test_action_error_codes_present_in_schema(self):
        # Action-level error codes are aggregated by build_schema_payload.
        error_codes = build_schema_payload()["error_codes"]
        for code in [
            "engine_unavailable",
            "no_session",
            "session_required",
            "session_not_found",
            "block_not_found",
            "runtime_error",
        ]:
            self.assertIn(code, error_codes, f"Missing reused error code: {code}")

    def test_framework_error_codes_produced_by_map_value_error(self):
        # Framework codes (invalid_input, invalid_json, etc.) come from map_value_error,
        # not from the schema error_codes list which only aggregates action ERRORS.
        for code in ("invalid_input", "invalid_json", "json_conflict", "unknown_parameter"):
            result = map_value_error(ValueError(f"{code}: test"))
            self.assertEqual(result["error"], code, f"Framework code '{code}' not mapped correctly")


if __name__ == "__main__":
    unittest.main()
