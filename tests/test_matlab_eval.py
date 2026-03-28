"""Tests for matlab_eval action."""

import unittest
from unittest.mock import MagicMock

from simulink_cli import matlab_transport
from simulink_cli.actions import matlab_eval


class EvalCodeTransportTests(unittest.TestCase):
    def test_eval_code_returns_output_and_warnings(self):
        engine = MagicMock(spec=["evalc", "lastwarn"])
        engine.evalc = MagicMock(return_value="ans =\n    3.1416\n")
        engine.lastwarn = MagicMock(side_effect=TypeError)

        result = matlab_transport.eval_code(engine, "pi")

        engine.evalc.assert_called_once_with("pi", nargout=1)
        self.assertEqual(result["value"], "ans =\n    3.1416\n")
        self.assertIsInstance(result["warnings"], list)

    def test_eval_code_timeout_raises(self):
        engine = MagicMock()
        future = MagicMock()
        future.result = MagicMock(side_effect=TimeoutError("timed out"))
        engine.evalc_async = MagicMock(return_value=future)
        engine.lastwarn = MagicMock(side_effect=TypeError)

        with self.assertRaises(TimeoutError):
            matlab_transport.eval_code(engine, "while true; end", timeout=1)

        engine.evalc_async.assert_called_once_with("while true; end", nargout=1)
        future.result.assert_called_once_with(timeout=1)


class MatlabEvalValidationTests(unittest.TestCase):
    def test_valid_args_returns_none(self):
        result = matlab_eval.validate({"code": "pi", "session": None})
        self.assertIsNone(result)

    def test_missing_code_returns_error(self):
        result = matlab_eval.validate({"code": None, "session": None})
        self.assertIsNotNone(result)
        self.assertEqual(result["error"], "invalid_input")

    def test_empty_code_returns_error(self):
        result = matlab_eval.validate({"code": "", "session": None})
        self.assertIsNotNone(result)
        self.assertEqual(result["error"], "invalid_input")

    def test_timeout_negative_returns_error(self):
        result = matlab_eval.validate({"code": "pi", "timeout": -1})
        self.assertIsNotNone(result)
        self.assertEqual(result["error"], "invalid_input")

    def test_timeout_zero_returns_error(self):
        result = matlab_eval.validate({"code": "pi", "timeout": 0})
        self.assertIsNotNone(result)
        self.assertEqual(result["error"], "invalid_input")

    def test_valid_timeout_returns_none(self):
        result = matlab_eval.validate({"code": "pi", "timeout": 10})
        self.assertIsNone(result)

    def test_code_with_newlines_returns_none(self):
        result = matlab_eval.validate({"code": "x = 1;\ndisp(x)", "session": None})
        self.assertIsNone(result)


from unittest.mock import patch
from tests.fakes import FakeModelEngine


class FakeEvalEngine:
    """Minimal engine fake that supports evalc."""
    def __init__(self, output=""):
        self._output = output
        self.warning_log = []

    def evalc(self, code, nargout=1):
        return self._output

    def lastwarn(self, *args, **kwargs):
        raise TypeError


class MatlabEvalExecuteTests(unittest.TestCase):
    def _run(self, args, engine=None):
        if engine is None:
            engine = FakeEvalEngine(output="ans =\n    3.1416\n")
        with patch.object(matlab_eval, "safe_connect_to_session", return_value=(engine, None)):
            return matlab_eval.execute(args)

    def _default_args(self, **overrides):
        args = {"code": "pi", "session": None}
        args.update(overrides)
        return args

    def test_execute_success(self):
        result = self._run(self._default_args())
        self.assertNotIn("error", result)
        self.assertEqual(result["action"], "matlab_eval")
        self.assertEqual(result["output"], "ans =\n    3.1416\n")
        self.assertFalse(result["truncated"])
        self.assertIsInstance(result["warnings"], list)

    def test_eval_failed_on_matlab_error(self):
        engine = FakeEvalEngine()
        engine.evalc = lambda code, nargout=1: (_ for _ in ()).throw(
            RuntimeError("Undefined function 'foo'")
        )
        result = self._run(self._default_args(code="foo"), engine=engine)
        self.assertEqual(result["error"], "eval_failed")
        self.assertIn("foo", result["message"])

    def test_eval_timeout(self):
        engine = MagicMock(spec=["evalc_async", "lastwarn"])
        future = MagicMock()
        future.result = MagicMock(side_effect=TimeoutError("timed out"))
        engine.evalc_async = MagicMock(return_value=future)
        engine.lastwarn = MagicMock(side_effect=TypeError)
        result = self._run(self._default_args(timeout=1), engine=engine)
        self.assertEqual(result["error"], "eval_timeout")

    def test_output_truncation(self):
        long_output = "x" * 60_000
        engine = FakeEvalEngine(output=long_output)
        result = self._run(self._default_args(), engine=engine)
        self.assertNotIn("error", result)
        self.assertTrue(result["truncated"])
        self.assertEqual(result["total_length"], 60_000)
        self.assertEqual(len(result["output"]), 50_000)

    def test_connection_error_propagates(self):
        error_response = {"error": "engine_unavailable", "message": "No MATLAB.", "details": {}}
        with patch.object(matlab_eval, "safe_connect_to_session", return_value=(None, error_response)):
            result = matlab_eval.execute(self._default_args())
        self.assertEqual(result["error"], "engine_unavailable")

    def test_empty_output(self):
        engine = FakeEvalEngine(output="")
        result = self._run(self._default_args(code="x = 1;"), engine=engine)
        self.assertNotIn("error", result)
        self.assertEqual(result["output"], "")
        self.assertFalse(result["truncated"])


if __name__ == "__main__":
    unittest.main()
