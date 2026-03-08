import argparse
import unittest

from skills.simulink_scan.scripts.sl_core import (
    run_action,
    validate_args,
    validate_text_field,
)


class InputValidationTests(unittest.TestCase):
    def test_rejects_control_chars(self):
        result = validate_text_field("target", "abc\x01")
        self.assertEqual(result["error"], "invalid_input")

    def test_rejects_reserved_chars(self):
        for value in ("a?b", "a#b", "a%b"):
            result = validate_text_field("model", value)
            self.assertEqual(result["error"], "invalid_input")

    def test_rejects_trim_mismatch(self):
        result = validate_text_field("session", " MATLAB_1 ")
        self.assertEqual(result["error"], "invalid_input")

    def test_rejects_overlength(self):
        result = validate_text_field("subsystem", "a" * 257)
        self.assertEqual(result["error"], "invalid_input")

    def test_accepts_normal_text(self):
        result = validate_text_field("model", "my_model")
        self.assertIsNone(result)

    def test_run_action_applies_validation_for_library_callers(self):
        args = argparse.Namespace(action="highlight", target="a?b", session=None)
        result = run_action(args)
        self.assertEqual(result["error"], "invalid_input")

    def test_validate_args_does_not_overrestrict_inspect_param(self):
        args = argparse.Namespace(
            action="inspect",
            model=None,
            target="m/b",
            param="Param%Name",
            active_only=False,
            strict_active=False,
            resolve_effective=False,
            summary=False,
            session=None,
        )
        result = validate_args(args)
        self.assertIsNone(result)

    def test_validate_args_rejects_invalid_connections_direction(self):
        args = argparse.Namespace(
            action="connections",
            model=None,
            target="m/b",
            session=None,
            direction="sideways",
            depth=1,
            detail="summary",
            include_handles=False,
        )
        result = validate_args(args)
        self.assertEqual(result["error"], "invalid_input")

    def test_validate_args_rejects_non_positive_connections_depth(self):
        args = argparse.Namespace(
            action="connections",
            model=None,
            target="m/b",
            session=None,
            direction="both",
            depth=0,
            detail="summary",
            include_handles=False,
        )
        result = validate_args(args)
        self.assertEqual(result["error"], "invalid_input")


if __name__ == "__main__":
    unittest.main()
