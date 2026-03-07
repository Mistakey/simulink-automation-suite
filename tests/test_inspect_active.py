import unittest

from skills.simulink_scan.scripts.sl_scan import inspect_block


class FakeEngine:
    def __init__(
        self,
        values,
        mask_names=None,
        mask_visibilities=None,
        mask_enables=None,
        valid_paths=None,
    ):
        self.values = values
        self.mask_names = mask_names
        self.mask_visibilities = mask_visibilities
        self.mask_enables = mask_enables
        self.valid_paths = set(valid_paths or ["m/b"])

    def get_param(self, block_path, param_name):
        if param_name == "Handle":
            if block_path not in self.valid_paths:
                raise RuntimeError("not found")
            return 1
        if param_name == "DialogParameters":
            return {key: {} for key in self.values.keys()}
        if param_name == "MaskNames":
            if self.mask_names is None:
                raise RuntimeError("not a masked block")
            return self.mask_names
        if param_name == "MaskVisibilities":
            if self.mask_visibilities is None:
                raise RuntimeError("not a masked block")
            return self.mask_visibilities
        if param_name == "MaskEnables":
            if self.mask_enables is None:
                raise RuntimeError("not a masked block")
            return self.mask_enables
        if param_name in self.values:
            return self.values[param_name]
        raise RuntimeError(f"unknown param {param_name}")

    def fieldnames(self, dialog_params):
        return list(dialog_params.keys())


class InspectActiveTests(unittest.TestCase):
    def test_missing_block_returns_block_not_found(self):
        eng = FakeEngine(values={"Gain": "5"}, valid_paths={"m/other"})
        result = inspect_block(eng, "m/b", "All")
        self.assertEqual(result["error"], "block_not_found")
        self.assertEqual(result["details"]["target"], "m/b")

    def test_masked_block_inactive_params_and_warning(self):
        eng = FakeEngine(
            values={"Mechanical": "[J F p Tf]", "PolePairs": "3"},
            mask_names=["Mechanical", "PolePairs"],
            mask_visibilities=["on", "off"],
            mask_enables=["on", "on"],
        )

        full = inspect_block(eng, "m/b", "All")
        self.assertIn("parameter_meta", full)
        self.assertTrue(full["parameter_meta"]["Mechanical"]["active"])
        self.assertFalse(full["parameter_meta"]["PolePairs"]["active"])
        self.assertIn("warnings", full)

        active = inspect_block(eng, "m/b", "All", active_only=True)
        self.assertTrue(active["active_only"])
        self.assertIn("Mechanical", active["values"])
        self.assertNotIn("PolePairs", active["values"])
        self.assertIn("PolePairs", active["dropped_inactive"])

    def test_single_param_inactive_metadata_and_effective_note(self):
        eng = FakeEngine(
            values={"Mechanical": "[0.1 0.2 7 0.4]", "PolePairs": "4"},
            mask_names=["Mechanical", "PolePairs"],
            mask_visibilities=["on", "off"],
            mask_enables=["on", "on"],
        )
        result = inspect_block(eng, "m/b", "PolePairs")
        self.assertEqual(result["param"], "PolePairs")
        self.assertFalse(result["meta"]["active"])
        self.assertEqual(result["effective_from"], "Mechanical[3]")
        self.assertIn("warnings", result)

    def test_single_param_strict_active_returns_machine_error(self):
        eng = FakeEngine(
            values={"Mechanical": "[0.1 0.2 7 0.4]", "PolePairs": "4"},
            mask_names=["Mechanical", "PolePairs"],
            mask_visibilities=["on", "off"],
            mask_enables=["on", "on"],
        )
        result = inspect_block(eng, "m/b", "PolePairs", strict_active=True)
        self.assertEqual(result["error"], "inactive_parameter")
        self.assertEqual(result["param"], "PolePairs")
        self.assertEqual(result["effective_from"], "Mechanical[3]")

    def test_single_param_resolve_effective_returns_resolved_value(self):
        eng = FakeEngine(
            values={"Mechanical": "[1 2 9 4]", "PolePairs": "4"},
            mask_names=["Mechanical", "PolePairs"],
            mask_visibilities=["on", "off"],
            mask_enables=["on", "on"],
        )
        result = inspect_block(eng, "m/b", "PolePairs", resolve_effective=True)
        self.assertEqual(result["requested_param"], "PolePairs")
        self.assertEqual(result["resolved_param"], "Mechanical")
        self.assertEqual(result["resolved_path"], "Mechanical[3]")
        self.assertEqual(result["resolved_value"], "9")

    def test_single_param_unknown_name_returns_stable_error(self):
        eng = FakeEngine(values={"Gain": "5", "SampleTime": "0.1"})
        result = inspect_block(eng, "m/b", "NoSuchParam")
        self.assertEqual(result["error"], "unknown_parameter")
        self.assertEqual(result["param"], "NoSuchParam")

    def test_single_param_resolve_effective_without_mapping_is_safe(self):
        eng = FakeEngine(
            values={"Alpha": "10"},
            mask_names=["Alpha"],
            mask_visibilities=["off"],
            mask_enables=["on"],
        )
        result = inspect_block(eng, "m/b", "Alpha", resolve_effective=True)
        self.assertFalse(result["meta"]["active"])
        self.assertIn("warnings", result)

    def test_all_summary_groups_active_and_inactive(self):
        eng = FakeEngine(
            values={"Mechanical": "[1 2 6 4]", "PolePairs": "4", "Gain": "1"},
            mask_names=["Mechanical", "PolePairs", "Gain"],
            mask_visibilities=["on", "off", "on"],
            mask_enables=["on", "on", "on"],
        )
        result = inspect_block(eng, "m/b", "All", summary=True)
        self.assertIn("active_params", result)
        self.assertIn("inactive_params", result)
        self.assertIn("effective_overrides", result)
        self.assertIn("PolePairs", result["inactive_params"])
        self.assertTrue(len(result["effective_overrides"]) >= 1)

    def test_unmasked_block_graceful_behavior(self):
        eng = FakeEngine(values={"Gain": "5", "SampleTime": "0.1"})
        full = inspect_block(eng, "m/b", "All")
        self.assertIn("parameter_meta", full)
        self.assertTrue(full["parameter_meta"]["Gain"]["active"])

        active = inspect_block(eng, "m/b", "All", active_only=True)
        self.assertEqual(set(active["values"].keys()), {"Gain", "SampleTime"})
        self.assertEqual(active["dropped_inactive"], [])

        strict = inspect_block(eng, "m/b", "Gain", strict_active=True)
        self.assertEqual(strict["param"], "Gain")
        self.assertTrue(strict["meta"]["active"])

        resolved = inspect_block(eng, "m/b", "Gain", resolve_effective=True)
        self.assertEqual(resolved["param"], "Gain")

    def test_all_params_active(self):
        eng = FakeEngine(
            values={"A": "1", "B": "2"},
            mask_names=["A", "B"],
            mask_visibilities=["on", "on"],
            mask_enables=["on", "on"],
        )
        full = inspect_block(eng, "m/b", "All")
        self.assertTrue(full["parameter_meta"]["A"]["active"])
        self.assertTrue(full["parameter_meta"]["B"]["active"])

        active = inspect_block(eng, "m/b", "All", active_only=True)
        self.assertEqual(set(active["values"].keys()), {"A", "B"})
        self.assertEqual(active["dropped_inactive"], [])

    def test_mask_array_length_mismatch_is_robust(self):
        eng = FakeEngine(
            values={"A": "1", "B": "2"},
            mask_names=["A", "B"],
            mask_visibilities=["off"],
            mask_enables=[],
        )
        full = inspect_block(eng, "m/b", "All")
        self.assertIn("warnings", full)
        self.assertFalse(full["parameter_meta"]["A"]["active"])
        self.assertTrue(full["parameter_meta"]["B"]["active"])


if __name__ == "__main__":
    unittest.main()
