import unittest
from unittest.mock import patch

from simulink_cli.actions import set_param
from tests.fakes import FakeSetParamEngine, WriteThenFailEngine, VerificationMismatchEngine


def _set_param_args(target="my_model/Gain1", param="Gain", value="2.0",
                    dry_run=True, model=None, session=None,
                    expected_current_value=None):
    return {
        "target": target, "param": param, "value": value,
        "dry_run": dry_run, "model": model, "session": session,
        "expected_current_value": expected_current_value,
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

    def test_rollback_includes_resolved_session(self):
        eng = self._make_engine()
        with patch.object(set_param, 'safe_connect_to_session', return_value=(eng, None)):
            result = set_param.execute(
                _set_param_args(dry_run=False, session="MATLAB_12345")
            )
        self.assertEqual(result["rollback"]["session"], "MATLAB_12345")

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

    def test_execute_rejects_stale_preview_without_writing(self):
        eng = self._make_engine()
        with patch.object(set_param, "safe_connect_to_session", return_value=(eng, None)):
            preview = set_param.execute(_set_param_args(dry_run=True))
        eng.force_param_value("my_model/Gain1", "Gain", "9.0")

        with patch.object(set_param, "safe_connect_to_session", return_value=(eng, None)):
            result = set_param.execute(preview["apply_payload"])

        self.assertEqual(result["error"], "precondition_failed")
        self.assertEqual(result["details"]["expected_current_value"], "1.5")
        self.assertEqual(result["details"]["observed_current_value"], "9.0")
        self.assertTrue(result["details"]["safe_to_retry"])
        self.assertEqual(eng.get_param("my_model/Gain1", "Gain"), "9.0")

    def test_execute_failure_after_attempt_includes_rollback_and_write_state(self):
        eng = WriteThenFailEngine()
        with patch.object(set_param, "safe_connect_to_session", return_value=(eng, None)):
            result = set_param.execute(_set_param_args(target="m/Gain", param="Gain", value="2.0", dry_run=False))
        self.assertEqual(result["error"], "set_param_failed")
        self.assertEqual(result["details"]["write_state"], "attempted")
        self.assertIn("rollback", result["details"])
        self.assertEqual(result["details"]["rollback"]["target"], "m/Gain")

    def test_execute_failure_after_attempt_includes_recovery_metadata(self):
        eng = WriteThenFailEngine()
        with patch.object(set_param, "safe_connect_to_session", return_value=(eng, None)):
            result = set_param.execute(
                _set_param_args(target="m/Gain", param="Gain", value="2.0", dry_run=False)
            )

        self.assertEqual(result["details"]["write_state"], "attempted")
        self.assertFalse(result["details"]["safe_to_retry"])
        self.assertEqual(result["details"]["recommended_recovery"], "rollback")

    def test_execute_verification_failure_returns_error_not_verified_false(self):
        eng = VerificationMismatchEngine()
        with patch.object(set_param, "safe_connect_to_session", return_value=(eng, None)):
            result = set_param.execute(_set_param_args(target="m/Gain", param="Gain", value="2.0", dry_run=False))
        self.assertEqual(result["error"], "verification_failed")
        self.assertEqual(result["details"]["write_state"], "verification_failed")

    def test_verification_failure_includes_recovery_metadata(self):
        eng = VerificationMismatchEngine()
        with patch.object(set_param, "safe_connect_to_session", return_value=(eng, None)):
            result = set_param.execute(
                _set_param_args(target="m/Gain", param="Gain", value="2.0", dry_run=False)
            )

        self.assertEqual(result["details"]["write_state"], "verification_failed")
        self.assertFalse(result["details"]["safe_to_retry"])
        self.assertEqual(result["details"]["recommended_recovery"], "rollback")

    def test_execute_rollback_with_empty_previous_value_is_replayable(self):
        eng = self._make_engine(param="Description", value="")
        with patch.object(set_param, "safe_connect_to_session", return_value=(eng, None)):
            result = set_param.execute(
                _set_param_args(param="Description", value="Line 1\nLine 2", dry_run=False)
            )
        self.assertNotIn("error", result)
        self.assertEqual(result["rollback"]["value"], "")

        rollback = result["rollback"]
        with patch.object(set_param, "safe_connect_to_session", return_value=(eng, None)):
            rollback_result = set_param.execute(
                _set_param_args(
                    target=rollback["target"],
                    param=rollback["param"],
                    value=rollback["value"],
                    dry_run=rollback["dry_run"],
                )
            )
        self.assertNotIn("error", rollback_result)
        self.assertEqual(rollback_result["new_value"], "")

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

    def test_multi_param_fake_engine_sets_both_params(self):
        eng = FakeSetParamEngine(
            params={"m/B::rep_seq_t": "[0 1]", "m/B::rep_seq_y": "[0 1]"},
            valid_handles={"m/B"},
        )
        eng.set_param("m/B", "rep_seq_t", "[0 5e-5 1e-4]", "rep_seq_y", "[-1 1 -1]")
        self.assertEqual(eng.get_param("m/B", "rep_seq_t"), "[0 5e-5 1e-4]")
        self.assertEqual(eng.get_param("m/B", "rep_seq_y"), "[-1 1 -1]")


class SetParamMultiValidationTests(unittest.TestCase):
    def test_params_and_param_mutually_exclusive(self):
        result = set_param.validate({
            "target": "m/B", "param": "Gain", "value": "2.0",
            "params": {"Gain": "2.0"}, "dry_run": True,
            "session": None, "expected_current_value": None,
            "expected_current_values": None,
        })
        self.assertIsNotNone(result)
        self.assertEqual(result["error"], "invalid_input")

    def test_neither_param_nor_params_returns_error(self):
        result = set_param.validate({
            "target": "m/B", "param": None, "value": None,
            "params": None, "dry_run": True,
            "session": None, "expected_current_value": None,
            "expected_current_values": None,
        })
        self.assertIsNotNone(result)
        self.assertEqual(result["error"], "invalid_input")

    def test_params_valid(self):
        result = set_param.validate({
            "target": "m/B", "param": None, "value": None,
            "params": {"rep_seq_t": "[0 1]", "rep_seq_y": "[0 1]"},
            "dry_run": True, "session": None,
            "expected_current_value": None,
            "expected_current_values": None,
        })
        self.assertIsNone(result)

    def test_params_empty_returns_error(self):
        result = set_param.validate({
            "target": "m/B", "param": None, "value": None,
            "params": {}, "dry_run": True, "session": None,
            "expected_current_value": None,
            "expected_current_values": None,
        })
        self.assertIsNotNone(result)
        self.assertEqual(result["error"], "invalid_input")

    def test_params_non_string_value_returns_error(self):
        result = set_param.validate({
            "target": "m/B", "param": None, "value": None,
            "params": {"Gain": 123}, "dry_run": True, "session": None,
            "expected_current_value": None,
            "expected_current_values": None,
        })
        self.assertIsNotNone(result)
        self.assertEqual(result["error"], "invalid_input")

    def test_single_param_mode_still_works(self):
        result = set_param.validate({
            "target": "m/B", "param": "Gain", "value": "2.0",
            "params": None, "dry_run": True, "session": None,
            "expected_current_value": None,
            "expected_current_values": None,
        })
        self.assertIsNone(result)


class SetParamMultiExecuteTests(unittest.TestCase):
    def _make_engine(self):
        return FakeSetParamEngine(
            params={
                "m/B::rep_seq_t": "[0 1]",
                "m/B::rep_seq_y": "[0 1]",
            },
            valid_handles={"m/B"},
        )

    def _multi_args(self, **overrides):
        args = {
            "target": "m/B",
            "param": None, "value": None,
            "params": {"rep_seq_t": "[0 5e-5 1e-4]", "rep_seq_y": "[-1 1 -1]"},
            "dry_run": True, "session": None,
            "expected_current_value": None,
            "expected_current_values": None,
        }
        args.update(overrides)
        return args

    def test_dry_run_returns_changes(self):
        eng = self._make_engine()
        with patch.object(set_param, "safe_connect_to_session", return_value=(eng, None)):
            result = set_param.execute(self._multi_args(dry_run=True))
        self.assertNotIn("error", result)
        self.assertTrue(result["dry_run"])
        self.assertEqual(result["write_state"], "not_attempted")
        self.assertEqual(len(result["changes"]), 2)
        self.assertIn("apply_payload", result)
        self.assertIn("rollback", result)

    def test_dry_run_apply_payload_has_expected_current_values(self):
        eng = self._make_engine()
        with patch.object(set_param, "safe_connect_to_session", return_value=(eng, None)):
            result = set_param.execute(self._multi_args(dry_run=True))
        apply = result["apply_payload"]
        self.assertIn("expected_current_values", apply)
        self.assertEqual(apply["expected_current_values"]["rep_seq_t"], "[0 1]")

    def test_execute_writes_and_verifies(self):
        eng = self._make_engine()
        with patch.object(set_param, "safe_connect_to_session", return_value=(eng, None)):
            result = set_param.execute(self._multi_args(dry_run=False))
        self.assertNotIn("error", result)
        self.assertFalse(result["dry_run"])
        self.assertEqual(result["write_state"], "verified")
        self.assertTrue(result["verified"])
        self.assertEqual(len(result["changes"]), 2)

    def test_execute_updates_all_params(self):
        eng = self._make_engine()
        with patch.object(set_param, "safe_connect_to_session", return_value=(eng, None)):
            set_param.execute(self._multi_args(dry_run=False))
        self.assertEqual(eng.get_param("m/B", "rep_seq_t"), "[0 5e-5 1e-4]")
        self.assertEqual(eng.get_param("m/B", "rep_seq_y"), "[-1 1 -1]")

    def test_rollback_captures_original_values(self):
        eng = self._make_engine()
        with patch.object(set_param, "safe_connect_to_session", return_value=(eng, None)):
            result = set_param.execute(self._multi_args(dry_run=False))
        rollback = result["rollback"]
        self.assertEqual(rollback["params"]["rep_seq_t"], "[0 1]")
        self.assertEqual(rollback["params"]["rep_seq_y"], "[0 1]")

    def test_block_not_found(self):
        eng = FakeSetParamEngine(params={}, valid_handles=set())
        with patch.object(set_param, "safe_connect_to_session", return_value=(eng, None)):
            result = set_param.execute(self._multi_args(target="m/Missing"))
        self.assertEqual(result["error"], "block_not_found")

    def test_param_not_found(self):
        eng = FakeSetParamEngine(
            params={"m/B::rep_seq_t": "[0 1]"},
            valid_handles={"m/B"},
        )
        with patch.object(set_param, "safe_connect_to_session", return_value=(eng, None)):
            result = set_param.execute(self._multi_args())
        self.assertEqual(result["error"], "param_not_found")

    def test_precondition_check_rejects_stale_values(self):
        eng = self._make_engine()
        with patch.object(set_param, "safe_connect_to_session", return_value=(eng, None)):
            preview = set_param.execute(self._multi_args(dry_run=True))
        eng.force_param_value("m/B", "rep_seq_t", "[changed]")
        with patch.object(set_param, "safe_connect_to_session", return_value=(eng, None)):
            result = set_param.execute(preview["apply_payload"])
        self.assertEqual(result["error"], "precondition_failed")
        self.assertEqual(result["details"]["write_state"], "not_attempted")

    def test_session_in_rollback(self):
        eng = self._make_engine()
        with patch.object(set_param, "safe_connect_to_session", return_value=(eng, None)):
            result = set_param.execute(self._multi_args(dry_run=False, session="S1"))
        self.assertEqual(result["rollback"]["session"], "S1")


if __name__ == "__main__":
    unittest.main()
