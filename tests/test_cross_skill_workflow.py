import unittest
from unittest.mock import patch

from simulink_cli.actions import inspect_block, set_param
from tests.fakes import FakeCrossSkillEngine


def _set_param_args(target, param, value, dry_run=True, model=None, session=None):
    return {
        "target": target, "param": param, "value": value,
        "dry_run": dry_run, "model": model, "session": session,
    }


def _inspect_args():
    return {
        "model": None,
        "target": "my_model/Gain1",
        "param": "Gain",
        "active_only": False,
        "strict_active": False,
        "resolve_effective": False,
        "summary": False,
        "session": None,
        "max_params": None,
        "fields": None,
    }


class CrossSkillWorkflowTests(unittest.TestCase):
    def test_inspect_preview_apply_and_rollback_loop(self):
        eng = FakeCrossSkillEngine()
        inspect_args = _inspect_args()

        with patch.object(set_param, 'safe_connect_to_session', return_value=(eng, None)):
            with patch.object(inspect_block, "safe_connect_to_session", return_value=(eng, None)):
                before = inspect_block.execute(inspect_args)
                preview = set_param.execute(_set_param_args(
                    target="my_model/Gain1", param="Gain", value="3.0", dry_run=True
                ))
                execute = set_param.execute(preview["apply_payload"])
                after = inspect_block.execute(inspect_args)
                rollback_result = set_param.execute(execute["rollback"])
                restored = inspect_block.execute(inspect_args)

        self.assertEqual(before["value"], "1.5")
        self.assertEqual(preview["current_value"], "1.5")
        self.assertTrue(execute["verified"])
        self.assertEqual(after["value"], "3.0")
        self.assertEqual(rollback_result["new_value"], "1.5")
        self.assertEqual(restored["value"], "1.5")

    def test_stale_preview_requires_new_dry_run(self):
        eng = FakeCrossSkillEngine()
        with patch.object(set_param, "safe_connect_to_session", return_value=(eng, None)):
            preview = set_param.execute(
                _set_param_args(
                    target="my_model/Gain1",
                    param="Gain",
                    value="3.0",
                    dry_run=True,
                )
            )
        eng.force_param_value("my_model/Gain1", "Gain", "9.0")

        with patch.object(set_param, "safe_connect_to_session", return_value=(eng, None)):
            result = set_param.execute(preview["apply_payload"])

        self.assertEqual(result["error"], "precondition_failed")
        self.assertEqual(result["details"]["recommended_recovery"], "rerun_dry_run")

    def test_rollback_payload_is_self_consistent(self):
        eng = FakeCrossSkillEngine()
        with patch.object(set_param, 'safe_connect_to_session', return_value=(eng, None)):
            result = set_param.execute(_set_param_args(
                target="my_model/Gain1", param="Gain", value="5.0", dry_run=True
            ))
        rollback = result["rollback"]
        # Rollback should restore the original value, not the proposed one
        self.assertEqual(rollback["value"], "1.5")
        self.assertFalse(rollback["dry_run"])


if __name__ == "__main__":
    unittest.main()
