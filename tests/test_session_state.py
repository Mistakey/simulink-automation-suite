import unittest
from unittest import mock

from skills.simulink_scan.scripts import sl_session


class SessionStateTests(unittest.TestCase):
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

    def test_session_clear_failure_returns_machine_error(self):
        with mock.patch.object(
            sl_session, "clear_state", side_effect=RuntimeError("clear denied")
        ):
            result = sl_session.command_session_clear()

        self.assertEqual(result["error"], "state_clear_failed")
        self.assertIn("clear denied", result["message"])


if __name__ == "__main__":
    unittest.main()
