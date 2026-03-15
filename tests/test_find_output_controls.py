import unittest

from skills.simulink_scan.scripts.sl_find import find_blocks


class FakeFindEngine:
    def __init__(self, models, find_results=None, valid_handles=None):
        self.models = models
        self.find_results = find_results or {}
        self.valid_handles = valid_handles or set()

    def find_system(self, *args, **kwargs):
        # Handle get_opened_models() call: find_system("Type", "block_diagram")
        if args == ("Type", "block_diagram"):
            return list(self.models)
        scope = args[0] if args else ""
        return self.find_results.get(scope, [])

    def get_param(self, path, param):
        if param == "Handle":
            if path not in self.valid_handles:
                raise RuntimeError(f"not found: {path}")
            return 1.0
        if param == "BlockType":
            if "SubSystem" in path or "Controller" in path:
                return "SubSystem"
            return "Gain"
        if param == "Type":
            return "block_diagram"
        raise RuntimeError(f"unknown param: {param}")

    def bdroot(self):
        return self.models[0] if self.models else ""


class FindOutputControlsTests(unittest.TestCase):
    def _make_engine(self):
        blocks = [f"my_model/Block{i}" for i in range(5)]
        return FakeFindEngine(
            models=["my_model"],
            find_results={"my_model": blocks},
            valid_handles={"my_model"} | set(blocks),
        )

    def test_max_results_clips_output(self):
        eng = self._make_engine()
        result = find_blocks(eng, model_name="my_model", name="Block", max_results=3)
        self.assertEqual(result["total_results"], 5)
        self.assertTrue(result["truncated"])
        self.assertEqual(len(result["results"]), 3)

    def test_fields_projection(self):
        eng = self._make_engine()
        result = find_blocks(
            eng, model_name="my_model", name="Block", fields=["path", "type"]
        )
        for item in result["results"]:
            self.assertIn("path", item)
            self.assertIn("type", item)
            self.assertNotIn("name", item)
            self.assertNotIn("parent", item)

    def test_max_results_and_fields_combined(self):
        eng = self._make_engine()
        result = find_blocks(
            eng,
            model_name="my_model",
            name="Block",
            max_results=2,
            fields=["path"],
        )
        self.assertEqual(result["total_results"], 5)
        self.assertTrue(result["truncated"])
        self.assertEqual(len(result["results"]), 2)
        self.assertEqual(sorted(result["results"][0].keys()), ["path"])


if __name__ == "__main__":
    unittest.main()
