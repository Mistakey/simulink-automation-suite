import unittest

from skills.simulink_scan.scripts.sl_scan import get_model_structure


class FakeScanEngine:
    def __init__(self, models, active_root, shallow_blocks, recursive_blocks, block_types):
        self.models = models
        self.active_root = active_root
        self.shallow_blocks = shallow_blocks
        self.recursive_blocks = recursive_blocks
        self.block_types = block_types

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
            return 1
        raise RuntimeError(f"unsupported param {param_name}")


class ScanBehaviorTests(unittest.TestCase):
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
        self.assertIn("error", result)
        self.assertEqual(result["models"], ["m1"])


if __name__ == "__main__":
    unittest.main()
