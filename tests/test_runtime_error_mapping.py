import unittest

from simulink_cli.core import map_runtime_error


class RuntimeErrorMappingTests(unittest.TestCase):
    def test_known_session_error_codes_map_stably(self):
        for code in (
            "session_required",
            "session_not_found",
            "no_session",
            "engine_unavailable",
        ):
            result = map_runtime_error(RuntimeError(code))
            self.assertEqual(result["error"], code)
            self.assertIn("message", result)
            self.assertIn("details", result)
            self.assertIn("suggested_fix", result)

    def test_unknown_runtime_error_maps_to_runtime_error(self):
        result = map_runtime_error(RuntimeError("engine crashed"))
        self.assertEqual(result["error"], "runtime_error")
        self.assertEqual(result["message"], "engine crashed")
        self.assertEqual(result["details"]["cause"], "engine crashed")

    def test_engine_unavailable(self):
        result = map_runtime_error(RuntimeError("engine_unavailable"))
        self.assertEqual(result["error"], "engine_unavailable")

    def test_no_session(self):
        result = map_runtime_error(RuntimeError("no_session"))
        self.assertEqual(result["error"], "no_session")

    def test_session_required(self):
        result = map_runtime_error(RuntimeError("session_required"))
        self.assertEqual(result["error"], "session_required")

    def test_session_not_found(self):
        result = map_runtime_error(RuntimeError("session_not_found"))
        self.assertEqual(result["error"], "session_not_found")

    def test_unknown_runtime_error_cause_in_details(self):
        result = map_runtime_error(RuntimeError("something else"))
        self.assertEqual(result["error"], "runtime_error")
        self.assertIn("something else", result["details"]["cause"])


if __name__ == "__main__":
    unittest.main()
