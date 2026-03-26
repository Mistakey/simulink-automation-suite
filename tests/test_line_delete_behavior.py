"""Tests for line_delete action."""

import unittest
from unittest.mock import patch
from tests.fakes import FakeLineEngine
from simulink_cli.actions import line_delete


class LineDeleteValidationTests(unittest.TestCase):
    def _default_args(self, **overrides):
        args = {
            "model": "m", "src_block": "A", "src_port": 1,
            "dst_block": "B", "dst_port": 1, "session": None,
        }
        args.update(overrides)
        return args

    def test_missing_model_returns_error(self):
        result = line_delete.validate(self._default_args(model=None))
        self.assertIsNotNone(result)
        self.assertEqual(result["error"], "invalid_input")

    def test_missing_src_block_returns_error(self):
        result = line_delete.validate(self._default_args(src_block=None))
        self.assertIsNotNone(result)
        self.assertEqual(result["error"], "invalid_input")

    def test_missing_dst_block_returns_error(self):
        result = line_delete.validate(self._default_args(dst_block=None))
        self.assertIsNotNone(result)
        self.assertEqual(result["error"], "invalid_input")

    def test_src_block_with_slash_returns_error(self):
        result = line_delete.validate(self._default_args(src_block="A/B"))
        self.assertIsNotNone(result)
        self.assertEqual(result["error"], "invalid_input")

    def test_dst_block_with_slash_returns_error(self):
        result = line_delete.validate(self._default_args(dst_block="A/B"))
        self.assertIsNotNone(result)
        self.assertEqual(result["error"], "invalid_input")

    def test_missing_src_port_returns_error(self):
        result = line_delete.validate(self._default_args(src_port=None))
        self.assertIsNotNone(result)
        self.assertEqual(result["error"], "invalid_input")

    def test_missing_dst_port_returns_error(self):
        result = line_delete.validate(self._default_args(dst_port=None))
        self.assertIsNotNone(result)
        self.assertEqual(result["error"], "invalid_input")

    def test_non_positive_src_port_returns_error(self):
        result = line_delete.validate(self._default_args(src_port=0))
        self.assertIsNotNone(result)
        self.assertEqual(result["error"], "invalid_input")

    def test_non_positive_dst_port_returns_error(self):
        result = line_delete.validate(self._default_args(dst_port=-1))
        self.assertIsNotNone(result)
        self.assertEqual(result["error"], "invalid_input")

    def test_valid_args_returns_none(self):
        result = line_delete.validate(self._default_args())
        self.assertIsNone(result)


class LineDeleteExecuteTests(unittest.TestCase):
    def _make_engine(self, **kwargs):
        defaults = {
            "loaded_models": ["m"],
            "blocks": ["m/A", "m/B"],
            "library_sources": ["simulink/Gain"],
        }
        defaults.update(kwargs)
        eng = FakeLineEngine(**defaults)
        # pre-create the line so delete tests have something to delete
        if "m" in defaults["loaded_models"] and "m/A" in defaults["blocks"] and "m/B" in defaults["blocks"]:
            eng.add_line("m", "A/1", "B/1", nargout=1)
        return eng

    def _run(self, args, engine=None):
        if engine is None:
            engine = self._make_engine()
        with patch.object(line_delete, "safe_connect_to_session", return_value=(engine, None)):
            return line_delete.execute(args)

    def _default_args(self, **overrides):
        args = {
            "model": "m", "src_block": "A", "src_port": 1,
            "dst_block": "B", "dst_port": 1, "session": None,
        }
        args.update(overrides)
        return args

    def test_deletes_line_successfully(self):
        result = self._run(self._default_args())
        self.assertNotIn("error", result)
        self.assertEqual(result["action"], "line_delete")
        self.assertEqual(result["model"], "m")
        self.assertIn("src_block", result)
        self.assertIn("dst_block", result)

    def test_model_not_found_returns_error(self):
        eng = FakeLineEngine()  # empty engine — no loaded models
        result = self._run(self._default_args(), engine=eng)
        self.assertEqual(result["error"], "model_not_found")

    def test_src_block_not_found_returns_error(self):
        eng = FakeLineEngine(loaded_models=["m"], blocks=["m/B"])
        result = self._run(self._default_args(), engine=eng)
        self.assertEqual(result["error"], "block_not_found")
        self.assertEqual(result["details"]["role"], "source")

    def test_dst_block_not_found_returns_error(self):
        eng = FakeLineEngine(loaded_models=["m"], blocks=["m/A"])
        result = self._run(self._default_args(), engine=eng)
        self.assertEqual(result["error"], "block_not_found")
        self.assertEqual(result["details"]["role"], "destination")

    def test_line_not_found_returns_error(self):
        # blocks exist but no line between them
        eng = FakeLineEngine(loaded_models=["m"], blocks=["m/A", "m/B"])
        result = self._run(self._default_args(), engine=eng)
        self.assertEqual(result["error"], "line_not_found")

    def test_runtime_error_on_delete_failure(self):
        eng = self._make_engine()
        from simulink_cli import matlab_transport
        with patch.object(
            matlab_transport, "delete_line",
            side_effect=RuntimeError("MATLAB internal error"),
        ):
            result = self._run(self._default_args(), engine=eng)
        self.assertEqual(result["error"], "runtime_error")
        self.assertIn("MATLAB internal error", result["details"]["cause"])

    def test_rollback_payload_structure(self):
        result = self._run(self._default_args())
        rollback = result["rollback"]
        self.assertEqual(rollback["action"], "line_add")
        self.assertEqual(rollback["model"], "m")
        self.assertIn("src_block", rollback)
        self.assertIn("src_port", rollback)
        self.assertIn("dst_block", rollback)
        self.assertIn("dst_port", rollback)
        self.assertTrue(rollback["available"])

    def test_session_passes_to_rollback(self):
        result = self._run(self._default_args(session="my_session"))
        self.assertEqual(result["rollback"]["session"], "my_session")

    def test_session_absent_from_rollback_when_none(self):
        result = self._run(self._default_args(session=None))
        self.assertNotIn("session", result["rollback"])

    def test_connection_error_propagates(self):
        error_response = {"error": "engine_unavailable", "message": "No MATLAB.", "details": {}}
        with patch.object(line_delete, "safe_connect_to_session", return_value=(None, error_response)):
            result = line_delete.execute(self._default_args())
        self.assertEqual(result["error"], "engine_unavailable")


if __name__ == "__main__":
    unittest.main()
