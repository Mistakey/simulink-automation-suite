import unittest
from unittest.mock import patch

from simulink_cli.actions import set_param
from tests.fakes import FakeSetParamEngine


def _set_param_args(target="my_model/Gain1", param="Gain", value="2.0",
                    dry_run=True, model=None, session=None):
    return {
        "target": target, "param": param, "value": value,
        "dry_run": dry_run, "model": model, "session": session,
    }


class SetParamBehaviorTests(unittest.TestCase):
    def _make_engine(self, target="my_model/Gain1", param="Gain", value="1.5"):
        return FakeSetParamEngine(
            params={f"{target}::{param}": value},
            valid_handles={target},
        )

    def test_dry_run_returns_preview(self):
        eng = self._make_engine()
        with patch.object(set_param, 'safe_connect_to_session', return_value=(eng, None)):
            result = set_param.execute(_set_param_args(dry_run=True))
        self.assertNotIn("error", result)
        self.assertTrue(result["dry_run"])
        self.assertEqual(result["current_value"], "1.5")
        self.assertEqual(result["proposed_value"], "2.0")

    def test_execute_writes_and_verifies(self):
        eng = self._make_engine()
        with patch.object(set_param, 'safe_connect_to_session', return_value=(eng, None)):
            result = set_param.execute(_set_param_args(dry_run=False))
        self.assertNotIn("error", result)
        self.assertFalse(result["dry_run"])
        self.assertEqual(result["previous_value"], "1.5")
        self.assertEqual(result["new_value"], "2.0")
        self.assertTrue(result["verified"])

    def test_execute_includes_rollback(self):
        eng = self._make_engine()
        with patch.object(set_param, 'safe_connect_to_session', return_value=(eng, None)):
            result = set_param.execute(_set_param_args(dry_run=False))
        rollback = result["rollback"]
        self.assertEqual(rollback["action"], "set_param")
        self.assertEqual(rollback["target"], "my_model/Gain1")
        self.assertEqual(rollback["param"], "Gain")
        self.assertEqual(rollback["value"], "1.5")
        self.assertFalse(rollback["dry_run"])

    def test_block_not_found_error(self):
        eng = FakeSetParamEngine(params={}, valid_handles=set())
        with patch.object(set_param, 'safe_connect_to_session', return_value=(eng, None)):
            result = set_param.execute(_set_param_args(target="my_model/Missing", dry_run=True))
        self.assertEqual(result["error"], "block_not_found")

    def test_param_not_found_error(self):
        eng = FakeSetParamEngine(
            params={},
            valid_handles={"my_model/Gain1"},
        )
        with patch.object(set_param, 'safe_connect_to_session', return_value=(eng, None)):
            result = set_param.execute(_set_param_args(param="NonExistent", dry_run=True))
        self.assertEqual(result["error"], "param_not_found")

    def test_set_param_failed_error(self):
        eng = self._make_engine()
        # Override set_param to simulate failure
        def failing_set_param(path, param, value):
            raise RuntimeError("MATLAB error: invalid value")

        eng.set_param = failing_set_param
        with patch.object(set_param, 'safe_connect_to_session', return_value=(eng, None)):
            result = set_param.execute(_set_param_args(value="invalid", dry_run=False))
        self.assertEqual(result["error"], "set_param_failed")

    def test_result_includes_target_and_param(self):
        eng = self._make_engine()
        with patch.object(set_param, 'safe_connect_to_session', return_value=(eng, None)):
            result = set_param.execute(_set_param_args(dry_run=True))
        self.assertEqual(result["target"], "my_model/Gain1")
        self.assertEqual(result["param"], "Gain")

    def test_result_includes_action_field(self):
        eng = self._make_engine()
        with patch.object(set_param, 'safe_connect_to_session', return_value=(eng, None)):
            result = set_param.execute(_set_param_args(dry_run=True))
        self.assertEqual(result["action"], "set_param")


if __name__ == "__main__":
    unittest.main()
