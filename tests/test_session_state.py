import unittest
from unittest import mock

from simulink_cli import session as sl_session


class SessionStateTests(unittest.TestCase):
    def test_get_matlab_engine_import_failure_returns_engine_unavailable(self):
        with mock.patch("importlib.import_module", side_effect=ImportError("missing")):
            with self.assertRaises(RuntimeError) as context:
                sl_session._get_matlab_engine()

        self.assertEqual(str(context.exception), "engine_unavailable")

    def test_discover_sessions_propagates_engine_unavailable(self):
        with mock.patch.object(
            sl_session, "_get_matlab_engine", side_effect=RuntimeError("engine_unavailable")
        ):
            with self.assertRaises(RuntimeError) as context:
                sl_session.discover_sessions()

        self.assertEqual(str(context.exception), "engine_unavailable")

    def test_session_current_does_not_activate_saved_when_multiple_sessions(self):
        with mock.patch.object(
            sl_session, "discover_sessions", return_value=["MATLAB_A", "MATLAB_B"]
        ), mock.patch.object(
            sl_session, "get_saved_session_name", return_value="MATLAB_A"
        ):
            result = sl_session.command_session_current()

        self.assertIsNone(result["active_session"])
        self.assertEqual(result["active_source"], "required")
        self.assertEqual(result["configured_session"], "MATLAB_A")

    def test_resolve_target_session_requires_explicit_when_multiple_sessions(self):
        with mock.patch.object(
            sl_session, "discover_sessions", return_value=["MATLAB_A", "MATLAB_B"]
        ):
            with self.assertRaises(RuntimeError) as context:
                sl_session.resolve_target_session()

        self.assertEqual(str(context.exception), "session_required")

    def test_command_session_use_rejects_non_exact_session_name(self):
        with mock.patch.object(
            sl_session, "discover_sessions", return_value=["MATLAB_12345"]
        ):
            result = sl_session.command_session_use("matlab")

        self.assertEqual(result["error"], "session_not_found")
        self.assertIn("message", result)
        self.assertIn("details", result)
        self.assertEqual(result["details"]["sessions"], ["MATLAB_12345"])

    def test_command_session_use_no_session_returns_stable_error_code(self):
        with mock.patch.object(sl_session, "discover_sessions", return_value=[]):
            result = sl_session.command_session_use("MATLAB_12345")

        self.assertEqual(result["error"], "no_session")
        self.assertIn("message", result)
        self.assertIn("details", result)
        self.assertEqual(result["details"].get("sessions"), [])
        self.assertIn("suggested_fix", result)

    def test_session_use_write_failure_returns_machine_error(self):
        with mock.patch.object(
            sl_session, "discover_sessions", return_value=["MATLAB_12345"]
        ), mock.patch.object(
            sl_session,
            "resolve_session_alias",
            return_value={"status": "exact", "matched": "MATLAB_12345"},
        ), mock.patch.object(
            sl_session,
            "set_saved_session_name",
            side_effect=RuntimeError("write denied"),
        ):
            result = sl_session.command_session_use("MATLAB_12345")

        self.assertEqual(result["error"], "state_write_failed")
        self.assertEqual(result["active_session"], "MATLAB_12345")
        self.assertIn("write denied", result["message"])
        self.assertIn("details", result)

    def test_session_clear_failure_returns_machine_error(self):
        with mock.patch.object(
            sl_session, "clear_state", side_effect=RuntimeError("clear denied")
        ):
            result = sl_session.command_session_clear()

        self.assertEqual(result["error"], "state_clear_failed")
        self.assertIn("clear denied", result["message"])
        self.assertIn("details", result)


if __name__ == "__main__":
    unittest.main()
