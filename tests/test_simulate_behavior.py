"""Tests for simulate action."""

import unittest
from unittest.mock import patch

from tests.fakes import FakeModelEngine
from simulink_cli.actions import simulate_cmd


class SimulateValidationTests(unittest.TestCase):
    def test_missing_model_returns_error(self):
        result = simulate_cmd.validate({"model": None, "session": None})
        self.assertIsNotNone(result)
        self.assertEqual(result["error"], "invalid_input")

    def test_empty_model_returns_error(self):
        result = simulate_cmd.validate({"model": "", "session": None})
        self.assertIsNotNone(result)
        self.assertEqual(result["error"], "invalid_input")

    def test_valid_args_returns_none(self):
        result = simulate_cmd.validate({"model": "m", "session": None})
        self.assertIsNone(result)

    def test_valid_stop_time_returns_none(self):
        result = simulate_cmd.validate({"model": "m", "stop_time": 0.5})
        self.assertIsNone(result)

    def test_invalid_stop_time_returns_error(self):
        result = simulate_cmd.validate({"model": "m", "stop_time": -1})
        self.assertIsNotNone(result)
        self.assertEqual(result["error"], "invalid_input")

    def test_invalid_max_step_string_returns_error(self):
        result = simulate_cmd.validate({"model": "m", "max_step": "auto"})
        self.assertIsNotNone(result)
        self.assertEqual(result["error"], "invalid_input")


class SimulateExecuteTests(unittest.TestCase):
    def _run(self, args, engine=None):
        if engine is None:
            engine = FakeModelEngine(loaded_models=["m"])
        with patch.object(simulate_cmd, "safe_connect_to_session", return_value=(engine, None)):
            return simulate_cmd.execute(args)

    def _default_args(self, **overrides):
        args = {"model": "m", "session": None}
        args.update(overrides)
        return args

    def test_simulate_succeeds(self):
        result = self._run(self._default_args())
        self.assertNotIn("error", result)
        self.assertEqual(result["action"], "simulate")
        self.assertEqual(result["model"], "m")
        self.assertIn("warnings", result)
        self.assertIsInstance(result["warnings"], list)

    def test_model_not_found_returns_error(self):
        eng = FakeModelEngine()  # no loaded models
        result = self._run(self._default_args(), engine=eng)
        self.assertEqual(result["error"], "model_not_found")

    def test_simulation_failed_returns_error(self):
        eng = FakeModelEngine(loaded_models=["m"])
        original_sim = eng.sim
        def failing_sim(model, nargout=1):
            raise RuntimeError("Simulation error: algebraic loop detected")
        eng.sim = failing_sim
        result = self._run(self._default_args(), engine=eng)
        self.assertEqual(result["error"], "simulation_failed")

    def test_runtime_error_on_engine_failure(self):
        eng = FakeModelEngine(loaded_models=["m"])
        def failing_sim(model, nargout=1):
            raise RuntimeError("MATLAB engine crashed")
        eng.sim = failing_sim
        result = self._run(self._default_args(), engine=eng)
        self.assertEqual(result["error"], "runtime_error")

    def test_stop_time_override_in_response(self):
        result = self._run(self._default_args(stop_time=0.1))
        self.assertNotIn("error", result)
        self.assertIn("overrides", result)
        self.assertEqual(result["overrides"]["StopTime"], 0.1)

    def test_max_step_override_in_response(self):
        result = self._run(self._default_args(max_step=1e-4))
        self.assertNotIn("error", result)
        self.assertIn("overrides", result)
        self.assertEqual(result["overrides"]["MaxStep"], 1e-4)

    def test_both_overrides_in_response(self):
        result = self._run(self._default_args(stop_time=0.5, max_step=1e-3))
        self.assertNotIn("error", result)
        self.assertEqual(result["overrides"]["StopTime"], 0.5)
        self.assertEqual(result["overrides"]["MaxStep"], 1e-3)

    def test_no_overrides_key_when_not_provided(self):
        result = self._run(self._default_args())
        self.assertNotIn("overrides", result)

    def test_connection_error_propagates(self):
        error_response = {"error": "engine_unavailable", "message": "No MATLAB.", "details": {}}
        with patch.object(simulate_cmd, "safe_connect_to_session", return_value=(None, error_response)):
            result = simulate_cmd.execute(self._default_args())
        self.assertEqual(result["error"], "engine_unavailable")


if __name__ == "__main__":
    unittest.main()
