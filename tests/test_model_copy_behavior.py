"""Tests for model_copy action."""

import unittest
from unittest.mock import patch

from tests.fakes import FakeModelEngine
from simulink_cli.actions import model_copy


class ModelCopyValidationTests(unittest.TestCase):
    def test_missing_source_returns_error(self):
        result = model_copy.validate({"source": None, "dest": "out", "session": None})
        self.assertIsNotNone(result)
        self.assertEqual(result["error"], "invalid_input")

    def test_empty_source_returns_error(self):
        result = model_copy.validate({"source": "", "dest": "out", "session": None})
        self.assertIsNotNone(result)
        self.assertEqual(result["error"], "invalid_input")

    def test_missing_dest_returns_error(self):
        result = model_copy.validate({"source": "m", "dest": None, "session": None})
        self.assertIsNotNone(result)
        self.assertEqual(result["error"], "invalid_input")

    def test_empty_dest_returns_error(self):
        result = model_copy.validate({"source": "m", "dest": "", "session": None})
        self.assertIsNotNone(result)
        self.assertEqual(result["error"], "invalid_input")

    def test_valid_args_returns_none(self):
        result = model_copy.validate({"source": "m", "dest": "m_copy", "session": None})
        self.assertIsNone(result)


class ModelCopyExecuteTests(unittest.TestCase):
    def _run(self, args, engine=None):
        if engine is None:
            engine = FakeModelEngine(loaded_models=["m"])
        with patch.object(model_copy, "safe_connect_to_session", return_value=(engine, None)):
            return model_copy.execute(args)

    def _default_args(self, **overrides):
        args = {"source": "m", "dest": "m_copy", "session": None}
        args.update(overrides)
        return args

    def test_copy_succeeds(self):
        result = self._run(self._default_args())
        self.assertNotIn("error", result)
        self.assertEqual(result["action"], "model_copy")
        self.assertEqual(result["source"], "m")
        self.assertEqual(result["dest"], "m_copy")

    def test_source_not_loaded_returns_error(self):
        eng = FakeModelEngine()  # no loaded models
        result = self._run(self._default_args(), engine=eng)
        self.assertEqual(result["error"], "model_not_found")

    def test_copy_failure_returns_error(self):
        eng = FakeModelEngine(loaded_models=["m"])
        def failing_evalc(code, nargout=1, background=False):
            if background:
                raise TypeError("no background")
            raise RuntimeError("Permission denied")
        eng.evalc = failing_evalc
        result = self._run(self._default_args(), engine=eng)
        self.assertEqual(result["error"], "model_copy_failed")
        self.assertIn("Permission denied", result["details"]["cause"])

    def test_connection_error_propagates(self):
        error_response = {"error": "engine_unavailable", "message": "No MATLAB.", "details": {}}
        with patch.object(model_copy, "safe_connect_to_session", return_value=(None, error_response)):
            result = model_copy.execute(self._default_args())
        self.assertEqual(result["error"], "engine_unavailable")


if __name__ == "__main__":
    unittest.main()
