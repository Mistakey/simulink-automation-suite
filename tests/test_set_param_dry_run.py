import unittest
from unittest.mock import patch

from simulink_cli.actions import set_param
from tests.fakes import FakeSetParamEngine


def _set_param_args(target="my_model/PID/Kp", param="Kp", value="3.0",
                    dry_run=True, model=None, session=None):
    return {
        "target": target, "param": param, "value": value,
        "dry_run": dry_run, "model": model, "session": session,
    }


class SetParamDryRunTests(unittest.TestCase):
    def _make_engine(self):
        return FakeSetParamEngine(
            params={"my_model/PID/Kp::Kp": "1.5"},
            valid_handles={"my_model/PID/Kp"},
        )

    def test_dry_run_does_not_write(self):
        eng = self._make_engine()
        with patch.object(set_param, 'safe_connect_to_session', return_value=(eng, None)):
            set_param.execute(_set_param_args(dry_run=True))
        # Verify the original value is unchanged
        self.assertEqual(eng.get_param("my_model/PID/Kp", "Kp"), "1.5")

    def test_dry_run_rollback_payload(self):
        eng = self._make_engine()
        with patch.object(set_param, 'safe_connect_to_session', return_value=(eng, None)):
            result = set_param.execute(_set_param_args(dry_run=True))
        rollback = result["rollback"]
        self.assertEqual(rollback["action"], "set_param")
        self.assertEqual(rollback["target"], "my_model/PID/Kp")
        self.assertEqual(rollback["param"], "Kp")
        self.assertEqual(rollback["value"], "1.5")
        self.assertFalse(rollback["dry_run"])

    def test_dry_run_output_shape(self):
        eng = self._make_engine()
        with patch.object(set_param, 'safe_connect_to_session', return_value=(eng, None)):
            result = set_param.execute(_set_param_args(dry_run=True))
        required_keys = {"action", "dry_run", "target", "param", "current_value", "proposed_value", "rollback"}
        self.assertTrue(required_keys.issubset(result.keys()))

    def test_execute_output_shape(self):
        eng = self._make_engine()
        with patch.object(set_param, 'safe_connect_to_session', return_value=(eng, None)):
            result = set_param.execute(_set_param_args(dry_run=False))
        required_keys = {"action", "dry_run", "target", "param", "previous_value", "new_value", "verified", "rollback"}
        self.assertTrue(required_keys.issubset(result.keys()))

    def test_dry_run_defaults_true_via_parser(self):
        from simulink_cli.core import build_parser

        parser = build_parser()
        args = parser.parse_args(["set_param", "--target", "m/B", "--param", "P", "--value", "1"])
        self.assertTrue(args.dry_run)


if __name__ == "__main__":
    unittest.main()
