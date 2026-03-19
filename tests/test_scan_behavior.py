import unittest
from unittest.mock import patch

from simulink_cli.actions import scan, highlight, list_opened
from simulink_cli import model_helpers
from tests.fakes import FakeScanEngine


def _scan_args(model=None, subsystem=None, recursive=False, hierarchy=False,
               session=None, max_blocks=None, fields=None):
    return {
        "model": model, "subsystem": subsystem, "recursive": recursive,
        "hierarchy": hierarchy, "session": session, "max_blocks": max_blocks,
        "fields": fields,
    }


class WarningBearingScanEngine(FakeScanEngine):
    def __init__(self):
        super().__init__(
            models=["m"],
            active_root="m",
            shallow_blocks={"m": ["m", "m/Gain"]},
            recursive_blocks={"m": ["m", "m/Gain"]},
            block_types={"m": "SubSystem", "m/Gain": "Gain"},
            valid_handles={"m", "m/Gain"},
        )
        self.warning_log = []

    def find_system(self, *args):
        self.warning_log.append("Variant warning")
        return super().find_system(*args)


class ScanBehaviorTests(unittest.TestCase):
    def test_resolve_scan_root_uses_bdroot_when_no_models_are_open(self):
        class BdrootOnlyEngine:
            def __init__(self):
                self.calls = []

            def find_system(self, *args, nargout):
                self.calls.append(("find_system", args, nargout))
                if args == ("Type", "block_diagram") and nargout == 1:
                    return []
                raise RuntimeError("unexpected")

            def bdroot(self, *, nargout):
                self.calls.append(("bdroot", (), nargout))
                return "m1"

        eng = BdrootOnlyEngine()

        result = model_helpers.resolve_scan_root_path(eng)

        self.assertEqual(result, {"model": "m1", "scan_root": "m1"})

    def test_no_open_model_bdroot_failure_returns_model_not_found(self):
        class FailingBdrootEngine:
            def find_system(self, *args):
                if args == ("Type", "block_diagram"):
                    return []
                raise RuntimeError("unexpected")

            def bdroot(self):
                raise RuntimeError("No system selected")

        eng = FailingBdrootEngine()
        with patch.object(scan, 'safe_connect_to_session', return_value=(eng, None)):
            result = scan.execute(_scan_args())
        self.assertEqual(result["error"], "model_not_found")

    def test_list_opened_models_returns_sorted_names(self):
        eng = FakeScanEngine(
            models=["z_model", "a_model", "m_model"],
            active_root="a_model",
            shallow_blocks={},
            recursive_blocks={},
            block_types={},
        )
        with patch.object(list_opened, 'safe_connect_to_session', return_value=(eng, None)):
            result = list_opened.execute({"session": None})
        self.assertEqual(result["models"], ["a_model", "m_model", "z_model"])

    def test_multiple_models_without_model_returns_model_required(self):
        eng = FakeScanEngine(
            models=["m1", "m2"],
            active_root="m1",
            shallow_blocks={},
            recursive_blocks={},
            block_types={},
        )
        with patch.object(scan, 'safe_connect_to_session', return_value=(eng, None)):
            result = scan.execute(_scan_args())
        self.assertEqual(result["error"], "model_required")
        self.assertEqual(result["details"]["models"], ["m1", "m2"])

    def test_single_model_defaults_to_only_open_model(self):
        eng = FakeScanEngine(
            models=["m1"],
            active_root="",
            shallow_blocks={"m1": ["m1", "m1/Gain"]},
            recursive_blocks={"m1": ["m1", "m1/Gain"]},
            block_types={"m1/Gain": "Gain"},
        )
        with patch.object(scan, 'safe_connect_to_session', return_value=(eng, None)):
            result = scan.execute(_scan_args())
        self.assertEqual(result["model"], "m1")
        self.assertEqual(result["scan_root"], "m1")
        self.assertFalse(result["recursive"])
        self.assertEqual(result["blocks"], [{"name": "m1/Gain", "type": "Gain"}])
        self.assertNotIn("connections", result)

    def test_single_model_includes_warnings_from_find_system(self):
        eng = WarningBearingScanEngine()
        with patch.object(scan, 'safe_connect_to_session', return_value=(eng, None)):
            result = scan.execute(_scan_args(model="m"))
        self.assertIn("warnings", result)
        self.assertEqual(result["warnings"], ["Variant warning"])

    def test_unknown_explicit_model_returns_available_models(self):
        eng = FakeScanEngine(
            models=["m1"],
            active_root="m1",
            shallow_blocks={},
            recursive_blocks={},
            block_types={},
        )
        with patch.object(scan, 'safe_connect_to_session', return_value=(eng, None)):
            result = scan.execute(_scan_args(model="m2"))
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
        with patch.object(scan, 'safe_connect_to_session', return_value=(eng, None)):
            result = scan.execute(_scan_args(model="m1", subsystem="bad/sub"))
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
        with patch.object(scan, 'safe_connect_to_session', return_value=(eng, None)):
            result = scan.execute(_scan_args(model="m1", subsystem="Gain"))
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
        with patch.object(highlight, 'safe_connect_to_session', return_value=(eng, None)):
            result = highlight.execute({"target": "m1/Gain", "session": None})
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
        with patch.object(highlight, 'safe_connect_to_session', return_value=(eng, None)):
            result = highlight.execute({"target": "m1/Gain", "session": None})
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
        with patch.object(highlight, 'safe_connect_to_session', return_value=(eng, None)):
            result = highlight.execute({"target": "m1/Gain", "session": None})
        self.assertEqual(result["error"], "runtime_error")
        self.assertEqual(result["details"]["target"], "m1/Gain")


    def test_hierarchy_with_fields_does_not_crash(self):
        eng = FakeScanEngine(
            models=["m1"],
            active_root="m1",
            shallow_blocks={"m1": ["m1/A", "m1/B"]},
            recursive_blocks={"m1": ["m1/A", "m1/B"]},
            block_types={"m1/A": "Gain", "m1/B": "SubSystem"},
            valid_handles=set(),
        )
        with patch.object(scan, 'safe_connect_to_session', return_value=(eng, None)):
            result = scan.execute(_scan_args(
                model="m1", recursive=True, hierarchy=True, fields=["name"],
            ))
        self.assertNotIn("error", result)
        self.assertIn("hierarchy", result)
        # Field projection applies to blocks but hierarchy uses full data
        for blk in result["blocks"]:
            self.assertNotIn("type", blk)
            self.assertIn("name", blk)


class SessionFlagModeTests(unittest.TestCase):
    def test_session_list_positional(self):
        from simulink_cli.core import build_parser

        parser = build_parser()
        args = parser.parse_args(["session", "list"])
        self.assertEqual(args.session_action, "list")

    def test_session_use_positional_name_bare(self):
        from simulink_cli.core import build_parser

        parser = build_parser()
        args = parser.parse_args(["session", "use", "MATLAB_123"])
        self.assertEqual(args.session_action, "use")
        self.assertEqual(args.name, "MATLAB_123")

    def test_session_use_positional_with_name(self):
        from simulink_cli.core import build_parser

        parser = build_parser()
        args = parser.parse_args(["session", "use", "--name", "MATLAB_123"])
        self.assertEqual(args.session_action, "use")
        self.assertEqual(args.name, "MATLAB_123")


if __name__ == "__main__":
    unittest.main()
