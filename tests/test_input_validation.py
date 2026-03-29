import unittest

from simulink_cli.validation import (
    validate_matlab_name_field,
    validate_session_field,
    validate_text_field,
    validate_value_field,
)
from simulink_cli.core import run_action
from simulink_cli.actions import connections, inspect_block, scan, set_param


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

    def test_validate_matlab_name_field_allows_newline_for_target(self):
        self.assertIsNone(validate_matlab_name_field("target", "m/Sub\nSystem"))

    def test_validate_matlab_name_field_allows_leading_and_trailing_spaces(self):
        self.assertIsNone(validate_matlab_name_field("target", " m/Sub "))

    def test_validate_matlab_name_field_rejects_nul(self):
        err = validate_matlab_name_field("target", "abc\x00def")
        self.assertEqual(err["error"], "invalid_input")

    def test_validate_session_field_still_rejects_control_characters(self):
        err = validate_session_field("session", "MATLAB_\n1")
        self.assertEqual(err["error"], "invalid_input")

    def test_validate_value_field_allows_percent_and_newline(self):
        self.assertIsNone(validate_value_field("value", "%.3f\nnext"))

    def test_validate_value_field_allows_leading_and_trailing_spaces(self):
        self.assertIsNone(validate_value_field("value", " 1 "))

    def test_validate_value_field_rejects_nul(self):
        err = validate_value_field("value", "abc\x00def")
        self.assertEqual(err["error"], "invalid_input")

    def test_run_action_applies_validation_for_library_callers(self):
        result = run_action("highlight", {"target": "a?b", "session": None})
        self.assertEqual(result["error"], "invalid_input")

    def test_validate_does_not_overrestrict_inspect_param(self):
        args = {
            "action": "inspect",
            "model": None,
            "target": "m/b",
            "param": "Param%Name",
            "active_only": False,
            "strict_active": False,
            "resolve_effective": False,
            "summary": False,
            "session": None,
        }
        result = inspect_block.validate(args)
        self.assertIsNone(result)

    def test_validate_rejects_invalid_connections_direction(self):
        args = {
            "action": "connections",
            "model": None,
            "target": "m/b",
            "session": None,
            "direction": "sideways",
            "depth": 1,
            "detail": "summary",
            "include_handles": False,
        }
        result = connections.validate(args)
        self.assertEqual(result["error"], "invalid_input")

    def test_validate_rejects_non_positive_connections_depth(self):
        args = {
            "action": "connections",
            "model": None,
            "target": "m/b",
            "session": None,
            "direction": "both",
            "depth": 0,
            "detail": "summary",
            "include_handles": False,
            "max_edges": None,
            "fields": None,
        }
        result = connections.validate(args)
        self.assertEqual(result["error"], "invalid_input")

    def test_validate_rejects_non_positive_connections_max_edges(self):
        args = {
            "action": "connections",
            "model": None,
            "target": "m/b",
            "session": None,
            "direction": "both",
            "depth": 1,
            "detail": "ports",
            "include_handles": False,
            "max_edges": 0,
            "fields": None,
        }
        result = connections.validate(args)
        self.assertEqual(result["error"], "invalid_input")

    def test_set_param_missing_target_returns_error(self):
        args = {"target": "", "param": "P", "value": "1", "dry_run": True, "model": None, "session": None}
        result = set_param.validate(args)
        self.assertIsNotNone(result)
        self.assertEqual(result["error"], "invalid_input")

    def test_set_param_missing_param_returns_error(self):
        args = {"target": "m/B", "param": "", "value": "1", "dry_run": True, "model": None, "session": None}
        result = set_param.validate(args)
        self.assertIsNotNone(result)
        self.assertEqual(result["error"], "invalid_input")

    def test_set_param_target_allows_matlab_control_characters(self):
        args = {"target": "m/B\x01", "param": "P", "value": "1", "dry_run": True, "model": None, "session": None}
        result = set_param.validate(args)
        self.assertIsNone(result)

    def test_set_param_param_allows_matlab_reserved_characters(self):
        args = {"target": "m/B", "param": "P?", "value": "1", "dry_run": True, "model": None, "session": None}
        result = set_param.validate(args)
        self.assertIsNone(result)

    def test_set_param_valid_args_returns_none(self):
        args = {"target": "m/B", "param": "Gain", "value": "2.0", "dry_run": True, "model": None, "session": None}
        result = set_param.validate(args)
        self.assertIsNone(result)

    def test_set_param_value_allows_literal_percent(self):
        args = {
            "target": "m/B",
            "param": "Format",
            "value": "%.3f",
            "dry_run": True,
            "model": None,
            "session": None,
        }
        result = set_param.validate(args)
        self.assertIsNone(result)

    def test_set_param_value_allows_trim_mismatch(self):
        args = {
            "target": "m/B",
            "param": "Gain",
            "value": " 1 ",
            "dry_run": True,
            "model": None,
            "session": None,
        }
        result = set_param.validate(args)
        self.assertIsNone(result)

    def test_set_param_value_allows_control_characters(self):
        args = {
            "target": "m/B",
            "param": "Gain",
            "value": "abc\x01",
            "dry_run": True,
            "model": None,
            "session": None,
        }
        result = set_param.validate(args)
        self.assertIsNone(result)

    def test_set_param_value_allows_empty_string(self):
        args = {
            "target": "m/B",
            "param": "Gain",
            "value": "",
            "dry_run": True,
            "model": None,
            "session": None,
        }
        result = set_param.validate(args)
        self.assertIsNone(result)

    def test_set_param_expected_current_value_uses_payload_validation(self):
        args = {
            "target": "m/B",
            "param": "Gain",
            "value": "2.0",
            "expected_current_value": "",
            "dry_run": False,
            "session": None,
        }
        result = set_param.validate(args)
        self.assertIsNone(result)

    def test_schema_action_returns_none_for_validate(self):
        # schema has no validate — run_action handles it directly
        result = run_action("schema", {})
        self.assertIn("version", result)
        self.assertIn("actions", result)

    def test_validate_json_type_port_accepts_integer(self):
        from simulink_cli.validation import validate_json_type
        validate_json_type("line_add", "src_port", 1, {"type": "port"})

    def test_validate_json_type_port_accepts_string(self):
        from simulink_cli.validation import validate_json_type
        validate_json_type("line_add", "src_port", "RConn1", {"type": "port"})

    def test_validate_json_type_port_rejects_bool(self):
        from simulink_cli.validation import validate_json_type
        with self.assertRaises(ValueError):
            validate_json_type("line_add", "src_port", True, {"type": "port"})

    def test_validate_json_type_port_rejects_float(self):
        from simulink_cli.validation import validate_json_type
        with self.assertRaises(ValueError):
            validate_json_type("line_add", "src_port", 1.5, {"type": "port"})

    def test_validate_json_type_object_accepts_dict(self):
        from simulink_cli.validation import validate_json_type
        validate_json_type("set_param", "params", {"k": "v"}, {"type": "object"})

    def test_validate_json_type_object_rejects_string(self):
        from simulink_cli.validation import validate_json_type
        with self.assertRaises(ValueError):
            validate_json_type("set_param", "params", "not_dict", {"type": "object"})

    def test_validate_json_type_object_rejects_list(self):
        from simulink_cli.validation import validate_json_type
        with self.assertRaises(ValueError):
            validate_json_type("set_param", "params", ["a"], {"type": "object"})


if __name__ == "__main__":
    unittest.main()
