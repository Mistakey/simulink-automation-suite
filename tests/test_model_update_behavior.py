import unittest
from unittest.mock import patch

from tests.fakes import FakeModelEngine
from simulink_cli.actions import model_update


class ModelUpdateValidationTests(unittest.TestCase):
    def test_missing_model_returns_error(self):
        result = model_update.validate({"model": None, "session": None})
        self.assertIsNotNone(result)
        self.assertEqual(result["error"], "invalid_input")

    def test_valid_args_returns_none(self):
        result = model_update.validate({"model": "m", "session": None})
        self.assertIsNone(result)


class ModelUpdateExecuteTests(unittest.TestCase):
    def _run(self, args, engine=None):
        if engine is None:
            engine = FakeModelEngine(loaded_models=["m"])
        with patch.object(model_update, "safe_connect_to_session", return_value=(engine, None)):
            return model_update.execute(args)

    def _default_args(self, **overrides):
        args = {"model": "m", "session": None}
        args.update(overrides)
        return args

    def test_updates_model_successfully(self):
        result = self._run(self._default_args())
        self.assertNotIn("error", result)
        self.assertEqual(result["action"], "model_update")
        self.assertEqual(result["model"], "m")
        self.assertIn("warnings", result)
        self.assertIsInstance(result["warnings"], list)

    def test_model_not_found_returns_error(self):
        eng = FakeModelEngine()
        result = self._run(self._default_args(), engine=eng)
        self.assertEqual(result["error"], "model_not_found")

    def test_update_failed_returns_error(self):
        eng = FakeModelEngine(loaded_models=["m"])
        original_set_param = eng.set_param
        def failing_set_param(target, param, value, nargout=0):
            if param == "SimulationCommand":
                raise RuntimeError("Compile error: algebraic loop detected")
            return original_set_param(target, param, value, nargout=nargout)
        eng.set_param = failing_set_param
        result = self._run(self._default_args(), engine=eng)
        self.assertEqual(result["error"], "update_failed")
        self.assertIn("Compile error", result["message"])

    def test_runtime_error_on_unexpected_failure(self):
        eng = FakeModelEngine(loaded_models=["m"])
        original_set_param = eng.set_param
        def failing_set_param(target, param, value, nargout=0):
            if param == "SimulationCommand":
                raise RuntimeError("Connection lost")
            return original_set_param(target, param, value, nargout=nargout)
        eng.set_param = failing_set_param
        result = self._run(self._default_args(), engine=eng)
        self.assertEqual(result["error"], "runtime_error")
        self.assertIn("Connection lost", result["message"])

    def test_connection_error_propagates(self):
        error_response = {"error": "engine_unavailable", "message": "No MATLAB.", "details": {}}
        with patch.object(model_update, "safe_connect_to_session", return_value=(None, error_response)):
            result = model_update.execute(self._default_args())
        self.assertEqual(result["error"], "engine_unavailable")

    def test_success_includes_diagnostics_field(self):
        result = self._run(self._default_args())
        self.assertIn("diagnostics", result)
        self.assertIsInstance(result["diagnostics"], list)

    def test_diagnostics_captures_output(self):
        eng = FakeModelEngine(
            loaded_models=["m"],
            update_output="Warning: Block 'm/Gain1' has unconnected input port 2.\n",
        )
        result = self._run(self._default_args(), engine=eng)
        self.assertEqual(len(result["diagnostics"]), 1)
        self.assertIn("unconnected", result["diagnostics"][0])

    def test_empty_diagnostics_on_clean_update(self):
        result = self._run(self._default_args())
        self.assertEqual(result["diagnostics"], [])


if __name__ == "__main__":
    unittest.main()
