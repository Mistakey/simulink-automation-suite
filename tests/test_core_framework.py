import json
import unittest

from simulink_cli.core import (
    _ACTIONS,
    build_schema_payload,
    main,
    map_runtime_error,
    map_value_error,
    parse_json_request,
)


class _FakeAction:
    FIELDS = {
        "name": {"type": "string", "required": True, "default": None, "description": "A name"},
        "count": {"type": "integer", "required": False, "default": 10, "description": "A count"},
    }
    ERRORS = ["fake_error"]
    DESCRIPTION = "A fake action for testing"

    @staticmethod
    def validate(args):
        if not args.get("name"):
            from simulink_cli.errors import make_error
            return make_error("invalid_input", "name is required")
        return None

    @staticmethod
    def execute(args):
        return {"action": "fake", "name": args["name"], "count": args.get("count", 10)}


class CoreSchemaTests(unittest.TestCase):
    def setUp(self):
        _ACTIONS["fake"] = _FakeAction
        self.addCleanup(lambda: _ACTIONS.pop("fake", None))

    def test_schema_includes_registered_action(self):
        schema = build_schema_payload()
        self.assertIn("fake", schema["actions"])
        self.assertEqual(schema["actions"]["fake"]["description"], "A fake action for testing")

    def test_schema_includes_schema_action(self):
        schema = build_schema_payload()
        self.assertIn("schema", schema["actions"])

    def test_schema_aggregates_error_codes(self):
        schema = build_schema_payload()
        self.assertIn("fake_error", schema["error_codes"])

    def test_schema_version(self):
        schema = build_schema_payload()
        self.assertEqual(schema["version"], "2.0")


class CoreJsonParsingTests(unittest.TestCase):
    def setUp(self):
        _ACTIONS["fake"] = _FakeAction
        self.addCleanup(lambda: _ACTIONS.pop("fake", None))

    def test_parse_valid_json(self):
        action, args = parse_json_request('{"action":"fake","name":"test"}')
        self.assertEqual(action, "fake")
        self.assertEqual(args["name"], "test")
        self.assertEqual(args["count"], 10)  # default

    def test_parse_schema_action(self):
        action, args = parse_json_request('{"action":"schema"}')
        self.assertEqual(action, "schema")
        self.assertEqual(args, {})

    def test_reject_unknown_action(self):
        with self.assertRaises(ValueError) as ctx:
            parse_json_request('{"action":"nonexistent"}')
        self.assertIn("unsupported action", str(ctx.exception))

    def test_reject_unknown_field(self):
        with self.assertRaises(ValueError) as ctx:
            parse_json_request('{"action":"fake","name":"x","bogus":1}')
        self.assertIn("unknown_parameter", str(ctx.exception))

    def test_reject_type_mismatch(self):
        with self.assertRaises(ValueError) as ctx:
            parse_json_request('{"action":"fake","name":"x","count":"notint"}')
        self.assertIn("invalid_json", str(ctx.exception))

    def test_reject_invalid_json(self):
        with self.assertRaises(ValueError) as ctx:
            parse_json_request("not json")
        self.assertIn("invalid_json", str(ctx.exception))

    def test_reject_non_object(self):
        with self.assertRaises(ValueError) as ctx:
            parse_json_request("[1,2,3]")
        self.assertIn("invalid_json", str(ctx.exception))

    def test_reject_missing_action(self):
        with self.assertRaises(ValueError) as ctx:
            parse_json_request('{"name":"x"}')
        self.assertIn("action is required", str(ctx.exception))


class CoreErrorMappingTests(unittest.TestCase):
    def test_map_value_error_invalid_json(self):
        result = map_value_error(ValueError("invalid_json: bad stuff"))
        self.assertEqual(result["error"], "invalid_json")

    def test_map_value_error_unknown_parameter(self):
        result = map_value_error(ValueError("unknown_parameter: field 'x'"))
        self.assertEqual(result["error"], "unknown_parameter")

    def test_map_value_error_fallback(self):
        result = map_value_error(ValueError("something random"))
        self.assertEqual(result["error"], "invalid_input")

    def test_map_runtime_error_known(self):
        result = map_runtime_error(RuntimeError("no_session"))
        self.assertEqual(result["error"], "no_session")
        self.assertIn("suggested_fix", result)

    def test_map_runtime_error_unknown(self):
        result = map_runtime_error(RuntimeError("weird failure"))
        self.assertEqual(result["error"], "runtime_error")


class CoreMainTests(unittest.TestCase):
    def setUp(self):
        _ACTIONS["fake"] = _FakeAction
        self.addCleanup(lambda: _ACTIONS.pop("fake", None))

    def test_main_json_mode_success(self):
        code = main(["--json", '{"action":"fake","name":"hello"}'])
        self.assertEqual(code, 0)

    def test_main_json_mode_schema(self):
        code = main(["--json", '{"action":"schema"}'])
        self.assertEqual(code, 0)

    def test_main_json_mode_validation_error(self):
        code = main(["--json", '{"action":"fake"}'])
        self.assertEqual(code, 1)

    def test_main_invalid_json(self):
        code = main(["--json", "not json"])
        self.assertEqual(code, 1)

    def test_main_json_conflict_extra_args(self):
        code = main(["--json", '{"action":"schema"}', "extra"])
        self.assertEqual(code, 1)

    def test_main_json_conflict_json_not_first(self):
        code = main(["fake", "--json", '{"action":"schema"}'])
        self.assertEqual(code, 1)

    def test_main_json_missing_required_field(self):
        """Required field missing in JSON -> invalid_json error, not invalid_input."""
        code = main(["--json", '{"action":"fake"}'])
        self.assertEqual(code, 1)
