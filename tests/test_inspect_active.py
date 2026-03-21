import unittest
from unittest.mock import patch

from simulink_cli.actions import inspect_block
from tests.fakes import FakeInspectEngine, KeywordNargoutInspectEngine


def _inspect_args(target="m/b", model=None, param="All", active_only=False,
                  strict_active=False, resolve_effective=False, summary=False,
                  session=None, max_params=None, fields=None):
    return {
        "target": target, "model": model, "param": param,
        "active_only": active_only, "strict_active": strict_active,
        "resolve_effective": resolve_effective, "summary": summary,
        "session": session, "max_params": max_params, "fields": fields,
    }


class InspectActiveTests(unittest.TestCase):
    def test_missing_block_returns_block_not_found(self):
        eng = FakeInspectEngine(values={"Gain": "5"}, valid_paths={"m/other"})
        with patch.object(inspect_block, 'safe_connect_to_session', return_value=(eng, None)):
            result = inspect_block.execute(_inspect_args(target="m/b"))
        self.assertEqual(result["error"], "block_not_found")
        self.assertEqual(result["details"]["target"], "m/b")

    def test_masked_block_inactive_params_and_warning(self):
        eng = FakeInspectEngine(
            values={"Mechanical": "[J F p Tf]", "PolePairs": "3"},
            mask_names=["Mechanical", "PolePairs"],
            mask_visibilities=["on", "off"],
            mask_enables=["on", "on"],
        )

        with patch.object(inspect_block, 'safe_connect_to_session', return_value=(eng, None)):
            full = inspect_block.execute(_inspect_args())
        self.assertIn("parameter_meta", full)
        self.assertTrue(full["parameter_meta"]["Mechanical"]["active"])
        self.assertFalse(full["parameter_meta"]["PolePairs"]["active"])
        self.assertIn("warnings", full)

        with patch.object(inspect_block, 'safe_connect_to_session', return_value=(eng, None)):
            active = inspect_block.execute(_inspect_args(active_only=True))
        self.assertTrue(active["active_only"])
        self.assertIn("Mechanical", active["values"])
        self.assertNotIn("PolePairs", active["values"])
        self.assertIn("PolePairs", active["dropped_inactive"])

    def test_single_param_inactive_metadata_and_effective_note(self):
        eng = FakeInspectEngine(
            values={"Mechanical": "[0.1 0.2 7 0.4]", "PolePairs": "4"},
            mask_names=["Mechanical", "PolePairs"],
            mask_visibilities=["on", "off"],
            mask_enables=["on", "on"],
        )
        with patch.object(inspect_block, 'safe_connect_to_session', return_value=(eng, None)):
            result = inspect_block.execute(_inspect_args(param="PolePairs"))
        self.assertEqual(result["param"], "PolePairs")
        self.assertFalse(result["meta"]["active"])
        self.assertEqual(result["effective_from"], "Mechanical[3]")
        self.assertIn("warnings", result)

    def test_single_param_strict_active_returns_machine_error(self):
        eng = FakeInspectEngine(
            values={"Mechanical": "[0.1 0.2 7 0.4]", "PolePairs": "4"},
            mask_names=["Mechanical", "PolePairs"],
            mask_visibilities=["on", "off"],
            mask_enables=["on", "on"],
        )
        with patch.object(inspect_block, 'safe_connect_to_session', return_value=(eng, None)):
            result = inspect_block.execute(_inspect_args(param="PolePairs", strict_active=True))
        self.assertEqual(result["error"], "inactive_parameter")
        self.assertIn("details", result)
        self.assertEqual(result["details"]["param"], "PolePairs")
        self.assertEqual(result["details"]["effective_from"], "Mechanical[3]")

    def test_single_param_resolve_effective_returns_resolved_value(self):
        eng = FakeInspectEngine(
            values={"Mechanical": "[1 2 9 4]", "PolePairs": "4"},
            mask_names=["Mechanical", "PolePairs"],
            mask_visibilities=["on", "off"],
            mask_enables=["on", "on"],
        )
        with patch.object(inspect_block, 'safe_connect_to_session', return_value=(eng, None)):
            result = inspect_block.execute(_inspect_args(param="PolePairs", resolve_effective=True))
        self.assertEqual(result["requested_param"], "PolePairs")
        self.assertEqual(result["resolved_param"], "Mechanical")
        self.assertEqual(result["resolved_path"], "Mechanical[3]")
        self.assertEqual(result["resolved_value"], "9")

    def test_single_param_unknown_name_returns_stable_error(self):
        eng = FakeInspectEngine(values={"Gain": "5", "SampleTime": "0.1"})
        with patch.object(inspect_block, 'safe_connect_to_session', return_value=(eng, None)):
            result = inspect_block.execute(_inspect_args(param="NoSuchParam"))
        self.assertEqual(result["error"], "param_not_found")
        self.assertIn("details", result)
        self.assertEqual(result["details"]["param"], "NoSuchParam")
        self.assertIn("target", result["details"])

    def test_single_param_unknown_name_preserves_warning(self):
        class WarningThenMissingParamInspectEngine(FakeInspectEngine):
            def get_param(self, block_path, param_name):
                if param_name == "NoSuchParam":
                    self.warning_log.append("Variant warning")
                    raise RuntimeError("missing")
                return super().get_param(block_path, param_name)

        eng = WarningThenMissingParamInspectEngine(
            values={"Gain": "5", "SampleTime": "0.1"}
        )
        eng.warning_log = []
        with patch.object(inspect_block, 'safe_connect_to_session', return_value=(eng, None)):
            result = inspect_block.execute(_inspect_args(param="NoSuchParam"))
        self.assertEqual(result["error"], "param_not_found")
        self.assertEqual(result["details"]["warnings"], ["Variant warning"])

    def test_dialog_value_fallback_preserves_warning(self):
        class WarningThenUnavailableDialogValueInspectEngine(FakeInspectEngine):
            def get_param(self, block_path, param_name):
                if param_name == "Gain":
                    self.warning_log.append("Variant warning")
                    raise RuntimeError("missing")
                return super().get_param(block_path, param_name)

        eng = WarningThenUnavailableDialogValueInspectEngine(
            values={"Gain": "5", "SampleTime": "0.1"}
        )
        eng.warning_log = []
        with patch.object(inspect_block, 'safe_connect_to_session', return_value=(eng, None)):
            result = inspect_block.execute(_inspect_args())
        self.assertIn("warnings", result)
        self.assertEqual(result["warnings"], ["Variant warning"])
        self.assertTrue(str(result["values"]["Gain"]).startswith("<unavailable:"))

    def test_single_param_resolve_effective_without_mapping_is_safe(self):
        eng = FakeInspectEngine(
            values={"Alpha": "10"},
            mask_names=["Alpha"],
            mask_visibilities=["off"],
            mask_enables=["on"],
        )
        with patch.object(inspect_block, 'safe_connect_to_session', return_value=(eng, None)):
            result = inspect_block.execute(_inspect_args(param="Alpha", resolve_effective=True))
        self.assertFalse(result["meta"]["active"])
        self.assertIn("warnings", result)

    def test_all_summary_groups_active_and_inactive(self):
        eng = FakeInspectEngine(
            values={"Mechanical": "[1 2 6 4]", "PolePairs": "4", "Gain": "1"},
            mask_names=["Mechanical", "PolePairs", "Gain"],
            mask_visibilities=["on", "off", "on"],
            mask_enables=["on", "on", "on"],
        )
        with patch.object(inspect_block, 'safe_connect_to_session', return_value=(eng, None)):
            result = inspect_block.execute(_inspect_args(summary=True))
        self.assertIn("active_params", result)
        self.assertIn("inactive_params", result)
        self.assertIn("effective_overrides", result)
        self.assertIn("PolePairs", result["inactive_params"])
        self.assertTrue(len(result["effective_overrides"]) >= 1)

    def test_available_params_are_sorted_for_stable_output(self):
        eng = FakeInspectEngine(values={"B": "2", "A": "1"})
        with patch.object(inspect_block, 'safe_connect_to_session', return_value=(eng, None)):
            result = inspect_block.execute(_inspect_args())
        self.assertEqual(result["available_params"], ["A", "B"])

    def test_inspect_uses_transport_backed_get_param_reads(self):
        eng = KeywordNargoutInspectEngine(values={"B": "2", "A": "1"})
        with patch.object(inspect_block, 'safe_connect_to_session', return_value=(eng, None)):
            result = inspect_block.execute(_inspect_args())
        self.assertNotIn("error", result)
        self.assertEqual(result["available_params"], ["A", "B"])
        self.assertEqual(result["values"]["A"], "1")

    def test_unmasked_block_graceful_behavior(self):
        eng = FakeInspectEngine(values={"Gain": "5", "SampleTime": "0.1"})
        with patch.object(inspect_block, 'safe_connect_to_session', return_value=(eng, None)):
            full = inspect_block.execute(_inspect_args())
        self.assertIn("parameter_meta", full)
        self.assertTrue(full["parameter_meta"]["Gain"]["active"])

        with patch.object(inspect_block, 'safe_connect_to_session', return_value=(eng, None)):
            active = inspect_block.execute(_inspect_args(active_only=True))
        self.assertEqual(set(active["values"].keys()), {"Gain", "SampleTime"})
        self.assertEqual(active["dropped_inactive"], [])

        with patch.object(inspect_block, 'safe_connect_to_session', return_value=(eng, None)):
            strict = inspect_block.execute(_inspect_args(param="Gain", strict_active=True))
        self.assertEqual(strict["param"], "Gain")
        self.assertTrue(strict["meta"]["active"])

        with patch.object(inspect_block, 'safe_connect_to_session', return_value=(eng, None)):
            resolved = inspect_block.execute(_inspect_args(param="Gain", resolve_effective=True))
        self.assertEqual(resolved["param"], "Gain")

    def test_all_params_active(self):
        eng = FakeInspectEngine(
            values={"A": "1", "B": "2"},
            mask_names=["A", "B"],
            mask_visibilities=["on", "on"],
            mask_enables=["on", "on"],
        )
        with patch.object(inspect_block, 'safe_connect_to_session', return_value=(eng, None)):
            full = inspect_block.execute(_inspect_args())
        self.assertTrue(full["parameter_meta"]["A"]["active"])
        self.assertTrue(full["parameter_meta"]["B"]["active"])

        with patch.object(inspect_block, 'safe_connect_to_session', return_value=(eng, None)):
            active = inspect_block.execute(_inspect_args(active_only=True))
        self.assertEqual(set(active["values"].keys()), {"A", "B"})
        self.assertEqual(active["dropped_inactive"], [])

    def test_mask_array_length_mismatch_is_robust(self):
        eng = FakeInspectEngine(
            values={"A": "1", "B": "2"},
            mask_names=["A", "B"],
            mask_visibilities=["off"],
            mask_enables=[],
        )
        with patch.object(inspect_block, 'safe_connect_to_session', return_value=(eng, None)):
            full = inspect_block.execute(_inspect_args())
        self.assertIn("warnings", full)
        self.assertFalse(full["parameter_meta"]["A"]["active"])
        self.assertTrue(full["parameter_meta"]["B"]["active"])


if __name__ == "__main__":
    unittest.main()
