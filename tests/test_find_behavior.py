import unittest
from unittest.mock import patch

from simulink_cli.actions import find
from tests.fakes import FakeFindEngine, OutputSensitiveEngine


def _find_args(model=None, subsystem=None, name=None, block_type=None,
               session=None, max_results=200, fields=None):
    return {
        "model": model, "subsystem": subsystem, "name": name,
        "block_type": block_type, "session": session,
        "max_results": max_results, "fields": fields,
    }


class FindBehaviorTests(unittest.TestCase):
    class _UnstringablePath:
        def __str__(self):
            raise RuntimeError("boom")

    def test_no_open_model_bdroot_failure_returns_model_not_found(self):
        class FailingBdrootEngine:
            def find_system(self, *args, **kwargs):
                if args == ("Type", "block_diagram"):
                    return []
                raise RuntimeError("unexpected")

            def bdroot(self):
                raise RuntimeError("No system selected")

        eng = FailingBdrootEngine()
        with patch.object(find, 'safe_connect_to_session', return_value=(eng, None)):
            result = find.execute(_find_args(name="Gain"))
        self.assertEqual(result["error"], "model_not_found")
        self.assertIn("details", result)

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

    def test_find_includes_warnings_from_find_system(self):
        eng = OutputSensitiveEngine()
        with patch.object(find, 'safe_connect_to_session', return_value=(eng, None)):
            result = find.execute(_find_args(model="m", name="Gain"))
        self.assertIn("warnings", result)
        self.assertEqual(result["warnings"], ["Variant warning"])

    def test_find_block_type_fallback_preserves_warning(self):
        class WarningThenMissingBlockTypeEngine(FakeFindEngine):
            def __init__(self):
                super().__init__(
                    models=["m"],
                    find_results={"m": ["m/Gain"]},
                    valid_handles={"m", "m/Gain"},
                )
                self.warning_log = []

            def get_param(self, path, param):
                if param == "BlockType":
                    self.warning_log.append("Variant warning")
                    raise RuntimeError("boom")
                return super().get_param(path, param)

        eng = WarningThenMissingBlockTypeEngine()
        with patch.object(find, 'safe_connect_to_session', return_value=(eng, None)):
            result = find.execute(_find_args(model="m", name="Gain"))
        self.assertEqual(result["warnings"], ["Variant warning"])
        self.assertEqual(result["results"][0]["type"], "")

    def test_find_failure_after_warning_preserves_details_warnings(self):
        class WarningThenResultEncodingFailureEngine(FakeFindEngine):
            def __init__(self):
                super().__init__(models=["m"], valid_handles={"m"})
                self.warning_log = []

            def find_system(self, *args, **kwargs):
                if args == ("Type", "block_diagram"):
                    return ["m"]
                self.warning_log.append("Variant warning")
                return [FindBehaviorTests._UnstringablePath()]

        eng = WarningThenResultEncodingFailureEngine()
        with patch.object(find, 'safe_connect_to_session', return_value=(eng, None)):
            result = find.execute(_find_args(model="m", name="Gain"))
        self.assertEqual(result["error"], "runtime_error")
        self.assertEqual(result["details"]["warnings"], ["Variant warning"])

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

    def test_find_uses_scan_visibility_options(self):
        class RecordingFindEngine(FakeFindEngine):
            def __init__(self):
                super().__init__(
                    models=["m1"],
                    find_results={"m1": ["m1/Gain1"]},
                    valid_handles={"m1", "m1/Gain1"},
                )
                self.calls = []

            def find_system(self, *args, **kwargs):
                self.calls.append(args)
                return super().find_system(*args, **kwargs)

        eng = RecordingFindEngine()
        with patch.object(find, 'safe_connect_to_session', return_value=(eng, None)):
            result = find.execute(_find_args(model="m1", name="Gain"))
        self.assertNotIn("error", result)
        self.assertGreaterEqual(len(eng.calls), 2)
        self.assertEqual(
            eng.calls[1][:5],
            ("m1", "FollowLinks", "on", "LookUnderMasks", "all"),
        )


if __name__ == "__main__":
    unittest.main()
