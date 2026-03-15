import json

from skills._shared.json_io import JsonArgumentParser, emit_json
from skills._shared.errors import make_error
from skills._shared.validation import validate_text_field, _invalid_input, validate_json_type
from skills._shared.session import connect_to_session


_JSON_FIELD_TYPES = {
    "schema": {},
    "set_param": {
        "target": {
            "type": "string",
            "required": True,
            "default": None,
            "description": "Full block path to modify.",
        },
        "param": {
            "type": "string",
            "required": True,
            "default": None,
            "description": "Parameter name.",
        },
        "value": {
            "type": "string",
            "required": True,
            "default": None,
            "description": "New parameter value (always string — MATLAB handles conversion).",
        },
        "dry_run": {
            "type": "boolean",
            "required": False,
            "default": True,
            "description": "Preview mode — show diff without writing. Defaults to true.",
        },
        "model": {
            "type": "string",
            "required": False,
            "default": None,
            "description": "Model disambiguation.",
        },
        "session": {
            "type": "string",
            "required": False,
            "default": None,
            "description": "MATLAB session name override.",
        },
    },
}

_ACTION_DESCRIPTIONS = {
    "schema": "Return machine-readable command contract and error-code catalog.",
    "set_param": "Set a block parameter with dry-run preview and rollback support.",
}

_ERROR_CODES = [
    "invalid_input",
    "invalid_json",
    "unknown_parameter",
    "json_conflict",
    "engine_unavailable",
    "no_session",
    "session_required",
    "session_not_found",
    "model_not_found",
    "block_not_found",
    "param_not_found",
    "set_param_failed",
    "runtime_error",
]


def build_schema_payload():
    actions = {}
    for action_name, field_defs in _JSON_FIELD_TYPES.items():
        actions[action_name] = {
            "description": _ACTION_DESCRIPTIONS.get(action_name, ""),
            "fields": field_defs,
        }
    return {
        "version": "1.0",
        "actions": actions,
        "error_codes": list(_ERROR_CODES),
    }


def build_parser():
    parser = JsonArgumentParser(description="Simulink Edit — Parameter Modification")
    parser.add_argument(
        "--json",
        dest="json_payload",
        help="JSON request payload. Use as a standalone entrypoint and do not mix with flags.",
    )
    subparsers = parser.add_subparsers(dest="action", required=True)
    subparsers.add_parser("schema", help="Return machine-readable command contract")

    set_param_parser = subparsers.add_parser(
        "set_param", help="Set a block parameter"
    )
    set_param_parser.add_argument(
        "--target", required=True, help="Full block path to modify"
    )
    set_param_parser.add_argument(
        "--param", required=True, help="Parameter name"
    )
    set_param_parser.add_argument(
        "--value", required=True, help="New parameter value (string)"
    )
    set_param_parser.add_argument(
        "--dry-run",
        type=lambda v: v.lower() in ("true", "1", "yes"),
        default=True,
        help="Preview mode (default: true)",
    )
    set_param_parser.add_argument("--model", help="Model disambiguation")
    set_param_parser.add_argument("--session", help="MATLAB session name override")
    return parser


def _parse_json_request(parser, raw_json):
    try:
        payload = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid_json: {exc}") from exc

    if not isinstance(payload, dict):
        raise ValueError("invalid_json: payload must be a JSON object")

    action = payload.pop("action", None)
    if not action:
        raise ValueError("invalid_json: 'action' field is required")

    if action not in _JSON_FIELD_TYPES:
        raise ValueError(f"invalid_json: unknown action '{action}'")

    field_defs = _JSON_FIELD_TYPES.get(action, {})
    for key in payload:
        if key not in field_defs:
            raise ValueError(
                f"unknown_parameter: field '{key}' is not valid for action '{action}'"
            )

    for key, value in payload.items():
        meta = field_defs[key]
        validate_json_type(action, key, value, meta)

    return _json_request_to_argv(action, payload, field_defs)


def _json_request_to_argv(action, payload, field_defs):
    argv = [action]
    for key, value in payload.items():
        meta = field_defs[key]
        flag = f"--{key.replace('_', '-')}"
        if meta["type"] == "boolean":
            argv.extend([flag, str(value).lower()])
        else:
            argv.extend([flag, str(value)])
    return argv


def parse_request_args(parser, argv=None):
    import sys

    args_list = argv if argv is not None else sys.argv[1:]

    json_payload = None
    for i, arg in enumerate(args_list):
        if arg == "--json" and i + 1 < len(args_list):
            json_payload = args_list[i + 1]
            break

    if json_payload is not None:
        positional = [a for a in args_list if a != "--json" and a != json_payload]
        if positional:
            raise ValueError("json_conflict: --json must not be mixed with positional/flag arguments")
        synthetic_argv = _parse_json_request(parser, json_payload)
        return parser.parse_args(synthetic_argv)

    return parser.parse_args(args_list)


def validate_args(args):
    if args.action == "schema":
        return None

    if args.action == "set_param":
        for field in ["target", "param", "value", "model", "session"]:
            val = getattr(args, field, None)
            if val is not None:
                err = validate_text_field(field, val)
                if err:
                    return err

        target = getattr(args, "target", None)
        if not target:
            return _invalid_input("target", "is required")
        param = getattr(args, "param", None)
        if not param:
            return _invalid_input("param", "is required")
        value = getattr(args, "value", None)
        if value is None:
            return _invalid_input("value", "is required")

    return None


def map_runtime_error(exc):
    message = str(exc).strip()
    mapping = {
        "engine_unavailable": (
            "engine_unavailable",
            "MATLAB Engine for Python is not available.",
            "Install MATLAB Engine for Python, then retry.",
        ),
        "no_session": (
            "no_session",
            "No shared MATLAB session found.",
            "Run matlab.engine.shareEngine in MATLAB, then retry.",
        ),
        "session_required": (
            "session_required",
            "Multiple MATLAB sessions found. Specify which session to use.",
            "Run `schema` or `--json '{\"action\":\"schema\"}'` to discover fields, then pass --session.",
        ),
        "session_not_found": (
            "session_not_found",
            "Specified session not found.",
            "Check session name and retry.",
        ),
    }
    if message in mapping:
        code, msg, fix = mapping[message]
        return make_error(code, msg, suggested_fix=fix)
    return make_error(
        "runtime_error",
        "Unexpected runtime error.",
        details={"cause": message},
    )


def map_value_error(exc):
    message = str(exc).strip()
    if message.startswith("invalid_json:"):
        return make_error("invalid_json", message)
    if message.startswith("json_conflict:"):
        return make_error("json_conflict", message)
    if message.startswith("unknown_parameter:"):
        return make_error("unknown_parameter", message)
    return make_error("invalid_input", message)


def run_action(args):
    if args.action == "schema":
        return build_schema_payload()

    validation_error = validate_args(args)
    if validation_error:
        return validation_error

    eng = connect_to_session(getattr(args, "session", None))

    if args.action == "set_param":
        from .sl_set_param import set_param

        return set_param(
            eng,
            target=args.target,
            param=args.param,
            value=args.value,
            dry_run=getattr(args, "dry_run", True),
            model=getattr(args, "model", None),
        )

    return make_error(
        "invalid_input",
        f"Unknown action '{args.action}'.",
        details={"action": args.action},
    )


def main(argv=None):
    try:
        parser = build_parser()
        parsed = parse_request_args(parser, argv=argv)
        result = run_action(parsed)
        emit_json(result)
        if isinstance(result, dict) and "error" in result:
            return 1
    except ValueError as exc:
        emit_json(map_value_error(exc))
        return 1
    except RuntimeError as exc:
        emit_json(map_runtime_error(exc))
        return 1
    except Exception as exc:
        emit_json(
            make_error(
                "runtime_error",
                "Unexpected error.",
                details={"cause": str(exc)},
            )
        )
        return 1
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
