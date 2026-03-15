import unittest

from skills.simulink_edit.scripts.sl_core import map_runtime_error


class EditRuntimeErrorMappingTests(unittest.TestCase):
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

    def test_unknown_runtime_error(self):
        result = map_runtime_error(RuntimeError("something else"))
        self.assertEqual(result["error"], "runtime_error")
        self.assertIn("something else", result["details"]["cause"])


if __name__ == "__main__":
    unittest.main()
