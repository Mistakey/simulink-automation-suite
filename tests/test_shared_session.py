import unittest
from unittest import mock

from simulink_cli import session as sl_session


class SharedSessionTests(unittest.TestCase):
    def test_discover_sessions_raises_on_engine_unavailable(self):
        with mock.patch.object(
            sl_session, "_get_matlab_engine", side_effect=RuntimeError("engine_unavailable")
        ):
            with self.assertRaises(RuntimeError) as ctx:
                sl_session.discover_sessions()
            self.assertIn("engine_unavailable", str(ctx.exception))

    def test_resolve_session_alias_exact_match(self):
        result = sl_session.resolve_session_alias("MATLAB_A", ["MATLAB_A", "MATLAB_B"])
        self.assertEqual(result["status"], "exact")
        self.assertEqual(result["matched"], "MATLAB_A")

    def test_resolve_session_alias_missing(self):
        result = sl_session.resolve_session_alias("MATLAB_X", ["MATLAB_A"])
        self.assertEqual(result["status"], "missing")

    def test_get_effective_session_single(self):
        with mock.patch.object(sl_session, "get_saved_session_name", return_value=None):
            effective, source, saved = sl_session.get_effective_session(["MATLAB_A"])
            self.assertEqual(effective, "MATLAB_A")
            self.assertEqual(source, "single")

    def test_get_effective_session_multiple_requires_explicit(self):
        with mock.patch.object(sl_session, "get_saved_session_name", return_value=None):
            effective, source, saved = sl_session.get_effective_session(["MATLAB_A", "MATLAB_B"])
            self.assertIsNone(effective)
            self.assertEqual(source, "required")

    def test_get_effective_session_uses_saved_selection_when_available(self):
        with mock.patch.object(sl_session, "get_saved_session_name", return_value="MATLAB_A"):
            effective, source, saved = sl_session.get_effective_session(["MATLAB_A", "MATLAB_B"])
            self.assertEqual(effective, "MATLAB_A")
            self.assertEqual(source, "configured")
            self.assertEqual(saved, "MATLAB_A")

    def test_plugin_root_points_to_repo_root(self):
        self.assertTrue(sl_session.PLUGIN_ROOT.exists())
        self.assertTrue((sl_session.PLUGIN_ROOT / ".claude-plugin" / "plugin.json").exists())


if __name__ == "__main__":
    unittest.main()
