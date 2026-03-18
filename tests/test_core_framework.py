import unittest

from simulink_cli.core import (
    _ACTIONS,
    build_schema_payload,
    main,
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


class CoreRegistryTests(unittest.TestCase):
    """Tests unique to the registry/dispatch mechanism using _FakeAction."""

    def setUp(self):
        _ACTIONS["fake"] = _FakeAction
        self.addCleanup(lambda: _ACTIONS.pop("fake", None))

    def test_schema_includes_registered_action(self):
        schema = build_schema_payload()
        self.assertIn("fake", schema["actions"])
        self.assertEqual(schema["actions"]["fake"]["description"], "A fake action for testing")

    def test_schema_aggregates_error_codes(self):
        schema = build_schema_payload()
        self.assertIn("fake_error", schema["error_codes"])

    def test_parse_valid_json_with_defaults(self):
        action, args = parse_json_request('{"action":"fake","name":"test"}')
        self.assertEqual(action, "fake")
        self.assertEqual(args["name"], "test")
        self.assertEqual(args["count"], 10)  # default injected

    def test_reject_unknown_action(self):
        with self.assertRaises(ValueError) as ctx:
            parse_json_request('{"action":"nonexistent"}')
        self.assertIn("unsupported action", str(ctx.exception))

    def test_reject_non_object(self):
        with self.assertRaises(ValueError) as ctx:
            parse_json_request("[1,2,3]")
        self.assertIn("invalid_json", str(ctx.exception))

    def test_map_value_error_fallback(self):
        result = map_value_error(ValueError("something random"))
        self.assertEqual(result["error"], "invalid_input")

    def test_main_json_mode_success(self):
        code = main(["--json", '{"action":"fake","name":"hello"}'])
        self.assertEqual(code, 0)

    def test_main_json_conflict_extra_args(self):
        code = main(["--json", '{"action":"schema"}', "extra"])
        self.assertEqual(code, 1)

    def test_main_json_missing_required_field(self):
        """Required field missing in JSON -> invalid_json error, not invalid_input."""
        code = main(["--json", '{"action":"fake"}'])
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
