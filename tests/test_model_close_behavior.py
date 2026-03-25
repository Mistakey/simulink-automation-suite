import unittest
from unittest.mock import patch
from tests.fakes import FakeModelEngine
from simulink_cli.actions import model_close


class FakeModelEngineCloseTests(unittest.TestCase):
    def test_close_removes_from_loaded(self):
        eng = FakeModelEngine(loaded_models=["m"])
        eng.close_system("m", 0, nargout=0)
        self.assertNotIn("m", eng.loaded_models)

    def test_dirty_state_default_off(self):
        eng = FakeModelEngine(loaded_models=["m"])
        self.assertEqual(eng.get_param("m", "Dirty", nargout=1), "off")

    def test_dirty_state_on(self):
        eng = FakeModelEngine(loaded_models=["m"], dirty_models=["m"])
        self.assertEqual(eng.get_param("m", "Dirty", nargout=1), "on")

    def test_set_param_simulation_command_update(self):
        eng = FakeModelEngine(loaded_models=["m"])
        eng.set_param("m", "SimulationCommand", "update", nargout=0)

    def test_set_param_update_not_loaded_raises(self):
        eng = FakeModelEngine()
        with self.assertRaises(RuntimeError):
            eng.set_param("missing", "SimulationCommand", "update", nargout=0)


class ModelCloseValidationTests(unittest.TestCase):
    def test_missing_model_returns_error(self):
        result = model_close.validate({"model": None, "force": False, "session": None})
        self.assertIsNotNone(result)
        self.assertEqual(result["error"], "invalid_input")

    def test_non_boolean_force_returns_error(self):
        result = model_close.validate({"model": "m", "force": 1, "session": None})
        self.assertIsNotNone(result)
        self.assertEqual(result["error"], "invalid_input")
        self.assertIn("force", result["details"]["field"])

    def test_valid_args_returns_none(self):
        result = model_close.validate({"model": "m", "force": False, "session": None})
        self.assertIsNone(result)


class ModelCloseExecuteTests(unittest.TestCase):
    def _run(self, args, engine=None):
        if engine is None:
            engine = FakeModelEngine(loaded_models=["m"])
        with patch.object(model_close, "safe_connect_to_session", return_value=(engine, None)):
            return model_close.execute(args)

    def _default_args(self, **overrides):
        args = {"model": "m", "force": False, "session": None}
        args.update(overrides)
        return args

    def test_closes_model_successfully(self):
        eng = FakeModelEngine(loaded_models=["m"])
        result = self._run(self._default_args(), engine=eng)
        self.assertNotIn("error", result)
        self.assertEqual(result["action"], "model_close")
        self.assertEqual(result["model"], "m")
        self.assertFalse(result["force"])
        self.assertNotIn("m", eng.loaded_models)

    def test_model_not_found_returns_error(self):
        eng = FakeModelEngine()
        result = self._run(self._default_args(), engine=eng)
        self.assertEqual(result["error"], "model_not_found")

    def test_dirty_model_without_force_returns_error(self):
        eng = FakeModelEngine(loaded_models=["m"], dirty_models=["m"])
        result = self._run(self._default_args(), engine=eng)
        self.assertEqual(result["error"], "model_dirty")
        self.assertIn("suggested_fix", result)

    def test_dirty_model_with_force_closes(self):
        eng = FakeModelEngine(loaded_models=["m"], dirty_models=["m"])
        result = self._run(self._default_args(force=True), engine=eng)
        self.assertNotIn("error", result)
        self.assertTrue(result["force"])
        self.assertNotIn("m", eng.loaded_models)

    def test_runtime_error_on_close_failure(self):
        eng = FakeModelEngine(loaded_models=["m"])
        original_close = eng.close_system
        def failing_close(model, save_flag=0, nargout=0):
            raise RuntimeError("MATLAB crashed during close")
        eng.close_system = failing_close
        result = self._run(self._default_args(), engine=eng)
        self.assertEqual(result["error"], "runtime_error")
        self.assertIn("MATLAB crashed", result["details"]["cause"])

    def test_connection_error_propagates(self):
        error_response = {"error": "engine_unavailable", "message": "No MATLAB.", "details": {}}
        with patch.object(model_close, "safe_connect_to_session", return_value=(None, error_response)):
            result = model_close.execute(self._default_args())
        self.assertEqual(result["error"], "engine_unavailable")


if __name__ == "__main__":
    unittest.main()
