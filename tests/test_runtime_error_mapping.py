import unittest

from skills.simulink_scan.scripts.sl_core import map_runtime_error


class RuntimeErrorMappingTests(unittest.TestCase):
    def test_known_session_error_codes_map_stably(self):
        for code in ("session_required", "session_not_found", "no_session"):
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


if __name__ == "__main__":
    unittest.main()
