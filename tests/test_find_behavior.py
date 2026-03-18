import unittest
from unittest.mock import patch

from simulink_cli.actions import find


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


def _find_args(model=None, subsystem=None, name=None, block_type=None,
               session=None, max_results=200, fields=None):
    return {
        "model": model, "subsystem": subsystem, "name": name,
        "block_type": block_type, "session": session,
        "max_results": max_results, "fields": fields,
    }


class FindBehaviorTests(unittest.TestCase):
    def test_find_by_name_returns_matching_blocks(self):
        eng = FakeFindEngine(
            models=["my_model"],
            find_results={
                "my_model": [
                    "my_model/Controller/PID_speed",
                    "my_model/Controller/PID_current",
                ]
            },
            valid_handles={"my_model", "my_model/Controller/PID_speed", "my_model/Controller/PID_current"},
        )
        with patch.object(find, 'safe_connect_to_session', return_value=(eng, None)):
            result = find.execute(_find_args(model="my_model", name="PID"))
        self.assertNotIn("error", result)
        self.assertEqual(result["total_results"], 2)
        self.assertFalse(result["truncated"])
        self.assertEqual(len(result["results"]), 2)

    def test_find_by_block_type_returns_matching_blocks(self):
        eng = FakeFindEngine(
            models=["my_model"],
            find_results={"my_model": ["my_model/Gain1", "my_model/Gain2"]},
            valid_handles={"my_model", "my_model/Gain1", "my_model/Gain2"},
        )
        with patch.object(find, 'safe_connect_to_session', return_value=(eng, None)):
            result = find.execute(_find_args(model="my_model", block_type="Gain"))
        self.assertNotIn("error", result)
        self.assertEqual(result["total_results"], 2)

    def test_find_requires_name_or_block_type(self):
        result = find.validate(_find_args(model="my_model"))
        self.assertIsNotNone(result)
        self.assertEqual(result["error"], "invalid_input")

    def test_find_empty_results_is_not_error(self):
        eng = FakeFindEngine(
            models=["my_model"],
            find_results={"my_model": []},
            valid_handles={"my_model"},
        )
        with patch.object(find, 'safe_connect_to_session', return_value=(eng, None)):
            result = find.execute(_find_args(model="my_model", name="nonexistent"))
        self.assertNotIn("error", result)
        self.assertEqual(result["total_results"], 0)
        self.assertEqual(result["results"], [])

    def test_find_result_includes_model_and_scan_root(self):
        eng = FakeFindEngine(
            models=["my_model"],
            find_results={"my_model": ["my_model/Gain1"]},
            valid_handles={"my_model", "my_model/Gain1"},
        )
        with patch.object(find, 'safe_connect_to_session', return_value=(eng, None)):
            result = find.execute(_find_args(model="my_model", name="Gain"))
        self.assertEqual(result["model"], "my_model")
        self.assertEqual(result["scan_root"], "my_model")

    def test_find_with_subsystem_narrows_scope(self):
        eng = FakeFindEngine(
            models=["my_model"],
            find_results={"my_model/Controller": ["my_model/Controller/PID1"]},
            valid_handles={"my_model", "my_model/Controller", "my_model/Controller/PID1"},
        )
        with patch.object(find, 'safe_connect_to_session', return_value=(eng, None)):
            result = find.execute(_find_args(model="my_model", subsystem="Controller", name="PID"))
        self.assertNotIn("error", result)
        self.assertEqual(result["scan_root"], "my_model/Controller")

    def test_find_regex_metacharacters_in_name_are_escaped(self):
        eng = FakeFindEngine(
            models=["my_model"],
            find_results={"my_model": []},
            valid_handles={"my_model"},
        )
        # Name with regex metacharacters should not cause MATLAB error
        with patch.object(find, 'safe_connect_to_session', return_value=(eng, None)):
            result = find.execute(_find_args(model="my_model", name="block[1].out"))
        self.assertNotIn("error", result)
        self.assertEqual(result["total_results"], 0)

    def test_find_model_not_found_error(self):
        eng = FakeFindEngine(models=["other_model"], valid_handles={"other_model"})
        with patch.object(find, 'safe_connect_to_session', return_value=(eng, None)):
            result = find.execute(_find_args(model="missing_model", name="x"))
        self.assertEqual(result["error"], "model_not_found")


if __name__ == "__main__":
    unittest.main()
