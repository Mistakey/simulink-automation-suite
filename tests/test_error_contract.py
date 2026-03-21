import unittest

from simulink_cli.errors import make_error
from simulink_cli.core import build_schema_payload, map_runtime_error, map_value_error


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

    def test_action_error_codes_present_in_schema(self):
        error_codes = build_schema_payload()["error_codes"]
        for code in [
            "engine_unavailable",
            "no_session",
            "session_required",
            "session_not_found",
            "block_not_found",
            "runtime_error",
            "param_not_found",
            "set_param_failed",
            "precondition_failed",
            "verification_failed",
        ]:
            self.assertIn(code, error_codes, f"Missing error code: {code}")

    def test_framework_error_codes_produced_by_map_value_error(self):
        for code in ("invalid_input", "invalid_json", "json_conflict", "unknown_parameter"):
            result = map_value_error(ValueError(f"{code}: test"))
            self.assertEqual(result["error"], code, f"Framework code '{code}' not mapped correctly")

    def test_known_runtime_errors_map_to_stable_codes(self):
        for code in ("session_required", "session_not_found", "no_session", "engine_unavailable"):
            result = map_runtime_error(RuntimeError(code))
            self.assertEqual(result["error"], code)
            self.assertIn("message", result)
            self.assertIn("suggested_fix", result)

    def test_unknown_runtime_error_maps_to_runtime_error(self):
        result = map_runtime_error(RuntimeError("engine crashed"))
        self.assertEqual(result["error"], "runtime_error")
        self.assertEqual(result["message"], "engine crashed")
        self.assertEqual(result["details"]["cause"], "engine crashed")


if __name__ == "__main__":
    unittest.main()
