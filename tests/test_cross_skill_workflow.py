import unittest

from skills.simulink_edit.scripts.sl_set_param import set_param


class FakeCrossSkillEngine:
    """Simulates a MATLAB engine with get_param and set_param."""

    def __init__(self):
        self._params = {
            "my_model/Gain1::Gain": "1.5",
            "my_model/Gain1::Handle": 1.0,
        }
        self._valid_handles = {"my_model/Gain1"}

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
        self._params[key] = value


class CrossSkillWorkflowTests(unittest.TestCase):
    def test_preview_then_execute_then_rollback(self):
        eng = FakeCrossSkillEngine()

        # Step 1: Preview (dry-run)
        preview = set_param(
            eng, target="my_model/Gain1", param="Gain", value="3.0", dry_run=True
        )
        self.assertNotIn("error", preview)
        self.assertTrue(preview["dry_run"])
        self.assertEqual(preview["current_value"], "1.5")
        self.assertEqual(preview["proposed_value"], "3.0")

        # Step 2: Execute
        execute = set_param(
            eng, target="my_model/Gain1", param="Gain", value="3.0", dry_run=False
        )
        self.assertNotIn("error", execute)
        self.assertFalse(execute["dry_run"])
        self.assertEqual(execute["new_value"], "3.0")
        self.assertTrue(execute["verified"])

        # Step 3: Verify the write happened
        self.assertEqual(eng.get_param("my_model/Gain1", "Gain"), "3.0")

        # Step 4: Rollback using the rollback payload from execute response
        rollback_payload = execute["rollback"]
        rollback_result = set_param(
            eng,
            target=rollback_payload["target"],
            param=rollback_payload["param"],
            value=rollback_payload["value"],
            dry_run=rollback_payload["dry_run"],
        )
        self.assertNotIn("error", rollback_result)
        self.assertEqual(rollback_result["new_value"], "1.5")

        # Step 5: Verify rollback restored the value
        self.assertEqual(eng.get_param("my_model/Gain1", "Gain"), "1.5")

    def test_rollback_payload_is_self_consistent(self):
        eng = FakeCrossSkillEngine()
        result = set_param(
            eng, target="my_model/Gain1", param="Gain", value="5.0", dry_run=True
        )
        rollback = result["rollback"]
        # Rollback should restore the original value, not the proposed one
        self.assertEqual(rollback["value"], "1.5")
        self.assertFalse(rollback["dry_run"])


if __name__ == "__main__":
    unittest.main()
