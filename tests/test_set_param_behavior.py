import unittest

from skills.simulink_edit.scripts.sl_set_param import set_param


class FakeSetParamEngine:
    def __init__(self, params=None, valid_handles=None):
        self._params = params or {}
        self._valid_handles = valid_handles or set()

    def get_param(self, path, param):
        if param == "Handle":
            if path not in self._valid_handles:
                raise RuntimeError(f"Invalid block path: {path}")
            return 1.0
        key = f"{path}::{param}"
        if key not in self._params:
            raise RuntimeError(f"Parameter '{param}' not found on '{path}'")
        return self._params[key]

    def set_param(self, path, param, value):
        key = f"{path}::{param}"
        if key not in self._params:
            raise RuntimeError(f"Parameter '{param}' not found on '{path}'")
        self._params[key] = value


class SetParamBehaviorTests(unittest.TestCase):
    def _make_engine(self, target="my_model/Gain1", param="Gain", value="1.5"):
        return FakeSetParamEngine(
            params={f"{target}::{param}": value},
            valid_handles={target},
        )

    def test_dry_run_returns_preview(self):
        eng = self._make_engine()
        result = set_param(
            eng,
            target="my_model/Gain1",
            param="Gain",
            value="2.0",
            dry_run=True,
        )
        self.assertNotIn("error", result)
        self.assertTrue(result["dry_run"])
        self.assertEqual(result["current_value"], "1.5")
        self.assertEqual(result["proposed_value"], "2.0")

    def test_execute_writes_and_verifies(self):
        eng = self._make_engine()
        result = set_param(
            eng,
            target="my_model/Gain1",
            param="Gain",
            value="2.0",
            dry_run=False,
        )
        self.assertNotIn("error", result)
        self.assertFalse(result["dry_run"])
        self.assertEqual(result["previous_value"], "1.5")
        self.assertEqual(result["new_value"], "2.0")
        self.assertTrue(result["verified"])

    def test_execute_includes_rollback(self):
        eng = self._make_engine()
        result = set_param(
            eng,
            target="my_model/Gain1",
            param="Gain",
            value="2.0",
            dry_run=False,
        )
        rollback = result["rollback"]
        self.assertEqual(rollback["action"], "set_param")
        self.assertEqual(rollback["target"], "my_model/Gain1")
        self.assertEqual(rollback["param"], "Gain")
        self.assertEqual(rollback["value"], "1.5")
        self.assertFalse(rollback["dry_run"])

    def test_block_not_found_error(self):
        eng = FakeSetParamEngine(params={}, valid_handles=set())
        result = set_param(
            eng,
            target="my_model/Missing",
            param="Gain",
            value="2.0",
            dry_run=True,
        )
        self.assertEqual(result["error"], "block_not_found")

    def test_param_not_found_error(self):
        eng = FakeSetParamEngine(
            params={},
            valid_handles={"my_model/Gain1"},
        )
        result = set_param(
            eng,
            target="my_model/Gain1",
            param="NonExistent",
            value="2.0",
            dry_run=True,
        )
        self.assertEqual(result["error"], "param_not_found")

    def test_set_param_failed_error(self):
        eng = self._make_engine()
        # Override set_param to simulate failure
        def failing_set_param(path, param, value):
            raise RuntimeError("MATLAB error: invalid value")

        eng.set_param = failing_set_param
        result = set_param(
            eng,
            target="my_model/Gain1",
            param="Gain",
            value="invalid",
            dry_run=False,
        )
        self.assertEqual(result["error"], "set_param_failed")

    def test_result_includes_target_and_param(self):
        eng = self._make_engine()
        result = set_param(
            eng,
            target="my_model/Gain1",
            param="Gain",
            value="2.0",
            dry_run=True,
        )
        self.assertEqual(result["target"], "my_model/Gain1")
        self.assertEqual(result["param"], "Gain")

    def test_result_includes_action_field(self):
        eng = self._make_engine()
        result = set_param(
            eng,
            target="my_model/Gain1",
            param="Gain",
            value="2.0",
            dry_run=True,
        )
        self.assertEqual(result["action"], "set_param")


if __name__ == "__main__":
    unittest.main()
