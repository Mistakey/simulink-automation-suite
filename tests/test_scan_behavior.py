import unittest

from skills.simulink_scan.scripts.sl_actions import (
    get_model_structure,
    highlight_block,
    list_opened_models,
)


class FakeScanEngine:
    def __init__(
        self,
        models,
        active_root,
        shallow_blocks,
        recursive_blocks,
        block_types,
        valid_handles=None,
        highlight_fail_targets=None,
    ):
        self.models = models
        self.active_root = active_root
        self.shallow_blocks = shallow_blocks
        self.recursive_blocks = recursive_blocks
        self.block_types = block_types
        self.valid_handles = set(valid_handles or [])
        self.highlight_fail_targets = set(highlight_fail_targets or [])
        self.highlight_calls = []

    def find_system(self, *args):
        if args == ("Type", "block_diagram"):
            return self.models

        scan_root = args[0]
        if "SearchDepth" in args:
            return self.shallow_blocks.get(scan_root, [scan_root])
        return self.recursive_blocks.get(scan_root, [scan_root])

    def bdroot(self):
        return self.active_root

    def get_param(self, block_path, param_name):
        if param_name == "BlockType":
            return self.block_types.get(block_path, "SubSystem")
        if param_name == "Handle":
            if self.valid_handles and block_path not in self.valid_handles:
                raise RuntimeError("not found")
            return 1
        raise RuntimeError(f"unsupported param {param_name}")

    def hilite_system(self, block_path, mode, nargout=0):
        self.highlight_calls.append((block_path, mode, nargout))
        if block_path in self.highlight_fail_targets:
            raise RuntimeError("highlight failed")
        return None


class ScanBehaviorTests(unittest.TestCase):
    def test_list_opened_models_returns_sorted_names(self):
        eng = FakeScanEngine(
            models=["z_model", "a_model", "m_model"],
            active_root="a_model",
            shallow_blocks={},
            recursive_blocks={},
            block_types={},
        )
        result = list_opened_models(eng)
        self.assertEqual(result["models"], ["a_model", "m_model", "z_model"])

    def test_multiple_models_without_model_returns_model_required(self):
        eng = FakeScanEngine(
            models=["m1", "m2"],
            active_root="m1",
            shallow_blocks={},
            recursive_blocks={},
            block_types={},
        )
        result = get_model_structure(eng)
        self.assertEqual(result["error"], "model_required")
        self.assertEqual(result["models"], ["m1", "m2"])

    def test_single_model_defaults_to_only_open_model(self):
        eng = FakeScanEngine(
            models=["m1"],
            active_root="",
            shallow_blocks={"m1": ["m1", "m1/Gain"]},
            recursive_blocks={"m1": ["m1", "m1/Gain"]},
            block_types={"m1/Gain": "Gain"},
        )
        result = get_model_structure(eng)
        self.assertEqual(result["model"], "m1")
        self.assertEqual(result["scan_root"], "m1")
        self.assertFalse(result["recursive"])
        self.assertEqual(result["blocks"], [{"name": "m1/Gain", "type": "Gain"}])
        self.assertNotIn("connections", result)

    def test_unknown_explicit_model_returns_available_models(self):
        eng = FakeScanEngine(
            models=["m1"],
            active_root="m1",
            shallow_blocks={},
            recursive_blocks={},
            block_types={},
        )
        result = get_model_structure(eng, model_name="m2")
        self.assertEqual(result["error"], "model_not_found")
        self.assertEqual(result["details"]["models"], ["m1"])

    def test_invalid_subsystem_returns_subsystem_not_found(self):
        eng = FakeScanEngine(
            models=["m1"],
            active_root="m1",
            shallow_blocks={},
            recursive_blocks={},
            block_types={},
            valid_handles={"m1"},
        )
        result = get_model_structure(eng, model_name="m1", subsystem_path="bad/sub")
        self.assertEqual(result["error"], "subsystem_not_found")
        self.assertEqual(result["details"]["model"], "m1")

    def test_non_subsystem_path_returns_invalid_subsystem_type(self):
        eng = FakeScanEngine(
            models=["m1"],
            active_root="m1",
            shallow_blocks={"m1/Gain": ["m1/Gain"]},
            recursive_blocks={"m1/Gain": ["m1/Gain"]},
            block_types={"m1/Gain": "Gain"},
            valid_handles={"m1", "m1/Gain"},
        )
        result = get_model_structure(eng, model_name="m1", subsystem_path="Gain")
        self.assertEqual(result["error"], "invalid_subsystem_type")
        self.assertEqual(result["details"]["path"], "m1/Gain")

    def test_highlight_block_success_returns_highlighted_target(self):
        eng = FakeScanEngine(
            models=[],
            active_root="",
            shallow_blocks={},
            recursive_blocks={},
            block_types={},
            valid_handles={"m1/Gain"},
        )
        result = highlight_block(eng, "m1/Gain")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["highlighted"], "m1/Gain")
        self.assertEqual(eng.highlight_calls, [("m1/Gain", "find", 0)])

    def test_highlight_block_missing_target_returns_block_not_found(self):
        eng = FakeScanEngine(
            models=[],
            active_root="",
            shallow_blocks={},
            recursive_blocks={},
            block_types={},
            valid_handles={"m1/Other"},
        )
        result = highlight_block(eng, "m1/Gain")
        self.assertEqual(result["error"], "block_not_found")
        self.assertEqual(result["details"]["target"], "m1/Gain")

    def test_highlight_block_runtime_failure_returns_runtime_error(self):
        eng = FakeScanEngine(
            models=[],
            active_root="",
            shallow_blocks={},
            recursive_blocks={},
            block_types={},
            valid_handles={"m1/Gain"},
            highlight_fail_targets={"m1/Gain"},
        )
        result = highlight_block(eng, "m1/Gain")
        self.assertEqual(result["error"], "runtime_error")
        self.assertEqual(result["details"]["target"], "m1/Gain")


if __name__ == "__main__":
    unittest.main()
