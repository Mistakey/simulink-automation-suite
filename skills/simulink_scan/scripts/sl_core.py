import json

from .sl_common import JsonArgumentParser, emit_json
from .sl_errors import make_error
from .sl_scan import (
    get_block_connections,
    get_model_structure,
    highlight_block,
    inspect_block,
    list_opened_models,
)
from .sl_session import (
    command_session_clear,
    command_session_current,
    command_session_list,
    command_session_use,
    connect_to_session,
)

_JSON_FIELD_TYPES = {
    "schema": {},
    "scan": {
        "model": str,
        "subsystem": str,
        "recursive": bool,
        "hierarchy": bool,
        "session": str,
        "max_blocks": int,
        "fields": list,
    },
    "connections": {
        "model": str,
        "target": str,
        "direction": str,
        "depth": int,
        "detail": str,
        "include_handles": bool,
        "session": str,
    },
    "highlight": {"target": str, "session": str},
    "inspect": {
        "model": str,
        "target": str,
        "param": str,
        "active_only": bool,
        "strict_active": bool,
        "resolve_effective": bool,
        "summary": bool,
        "session": str,
        "max_params": int,
        "fields": list,
    },
    "list_opened": {"session": str},
}

_SESSION_ACTIONS = {"list", "use", "current", "clear"}
_ERROR_CODES = [
    "invalid_input",
    "invalid_json",
    "unknown_parameter",
    "json_conflict",
    "engine_unavailable",
    "no_session",
    "session_required",
    "session_not_found",
    "state_write_failed",
    "state_clear_failed",
    "model_required",
    "model_not_found",
    "subsystem_not_found",
    "invalid_subsystem_type",
    "block_not_found",
    "inactive_parameter",
    "runtime_error",
]


def _invalid_input(field_name, message):
    return make_error(
        "invalid_input",
        f"Field '{field_name}' {message}.",
        details={"field": field_name},
    )


def validate_text_field(field_name, value, max_len=256):
    if value is None:
        return None

    text = str(value)
    if not text:
        return _invalid_input(field_name, "must not be empty")
    if text != text.strip():
        return _invalid_input(field_name, "has leading/trailing whitespace")
    if len(text) > max_len:
        return _invalid_input(field_name, f"exceeds max length {max_len}")
    if any(ord(char) < 32 for char in text):
        return _invalid_input(field_name, "contains control characters")
    if any(char in text for char in ("?", "#", "%")):
        return _invalid_input(field_name, "contains reserved characters")
    return None


def validate_args(args):
    fields = []

    if args.action == "scan":
        fields = ["model", "subsystem", "session"]
    elif args.action == "connections":
        fields = ["model", "target", "session"]
    elif args.action == "highlight":
        fields = ["target", "session"]
    elif args.action == "inspect":
        # Parameter names are API-level identifiers and may contain symbols.
        # Keep strict hardening on path/session-like fields only.
        fields = ["model", "target", "session"]
    elif args.action == "list_opened":
        fields = ["session"]
    elif args.action == "session" and getattr(args, "session_action", None) == "use":
        fields = ["name"]

    for field_name in fields:
        result = validate_text_field(field_name, getattr(args, field_name, None))
        if result:
            return result

    if args.action == "scan":
        max_blocks = getattr(args, "max_blocks", None)
        if max_blocks is not None and max_blocks <= 0:
            return _invalid_input("max_blocks", "must be greater than zero")
    if args.action == "connections":
        depth = getattr(args, "depth", None)
        if depth is not None and depth <= 0:
            return _invalid_input("depth", "must be greater than zero")
        direction = getattr(args, "direction", "both")
        if direction not in {"upstream", "downstream", "both"}:
            return _invalid_input(
                "direction", "must be one of upstream,downstream,both"
            )
        detail = getattr(args, "detail", "summary")
        if detail not in {"summary", "ports", "lines"}:
            return _invalid_input("detail", "must be one of summary,ports,lines")
    if args.action == "inspect":
        max_params = getattr(args, "max_params", None)
        if max_params is not None and max_params <= 0:
            return _invalid_input("max_params", "must be greater than zero")
    return None


def map_runtime_error(exc):
    code = str(exc).strip()
    messages = {
        "engine_unavailable": "MATLAB Engine for Python is not available in the current Python environment.",
        "session_required": "Multiple MATLAB sessions found. Pass --session with an exact session name.",
        "session_not_found": "Session not found. Pass an exact session name from `session list` output.",
        "no_session": "No shared MATLAB session found. Ask user to run matlab.engine.shareEngine in MATLAB.",
    }
    suggested_fixes = {
        "engine_unavailable": "Install/configure MATLAB Engine for Python for the active interpreter, then retry.",
        "session_required": "Run `session list` and pass --session with an exact name.",
        "session_not_found": "Run `session list` and retry with an exact session name.",
        "no_session": "Run matlab.engine.shareEngine in MATLAB, then retry.",
    }
    if code in messages:
        return make_error(
            code,
            messages[code],
            details={"cause": code},
            suggested_fix=suggested_fixes[code],
        )
    return make_error(
        "runtime_error",
        str(exc),
        details={"cause": str(exc)},
    )


def map_value_error(exc):
    text = str(exc).strip()
    if ":" in text:
        code, message = text.split(":", 1)
        code = code.strip()
        message = message.strip()
        if code in {
            "invalid_json",
            "json_conflict",
            "unknown_parameter",
            "invalid_input",
        }:
            return make_error(code, message, details={"cause": text})
    return make_error("invalid_input", text, details={"cause": text})


def _parse_with_parser(parser, argv):
    try:
        return parser.parse_args(argv)
    except ValueError as exc:
        message = str(exc).strip()
        if message.startswith("unrecognized arguments:"):
            raise ValueError(f"unknown_parameter: {message}") from exc
        raise ValueError(f"invalid_input: {message}") from exc


def _validate_json_type(action, field_name, value, expected_type):
    if value is None:
        return
    if expected_type is bool and not isinstance(value, bool):
        raise ValueError(
            f"invalid_json: field '{field_name}' for action '{action}' must be boolean"
        )
    if expected_type is str and not isinstance(value, str):
        raise ValueError(
            f"invalid_json: field '{field_name}' for action '{action}' must be string"
        )
    if expected_type is int and not isinstance(value, int):
        raise ValueError(
            f"invalid_json: field '{field_name}' for action '{action}' must be integer"
        )
    if expected_type is list:
        if not isinstance(value, list):
            raise ValueError(
                f"invalid_json: field '{field_name}' for action '{action}' must be an array"
            )
        if not all(isinstance(item, str) for item in value):
            raise ValueError(
                f"invalid_json: field '{field_name}' for action '{action}' must be an array of strings"
            )


def _parse_json_request(raw_payload):
    try:
        request = json.loads(raw_payload)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid_json: {exc.msg}") from exc

    if not isinstance(request, dict):
        raise ValueError("invalid_json: payload must be a JSON object")

    action = request.get("action")
    if not isinstance(action, str) or not action.strip():
        raise ValueError("invalid_json: action is required")
    if action not in _JSON_FIELD_TYPES and action != "session":
        raise ValueError(f"invalid_json: unsupported action '{action}'")

    allowed_fields = {"action"}
    if action == "session":
        allowed_fields.update({"session_action", "name"})
    else:
        allowed_fields.update(_JSON_FIELD_TYPES[action].keys())

    for key in request.keys():
        if key not in allowed_fields:
            raise ValueError(
                f"unknown_parameter: field '{key}' is not supported for action '{action}'"
            )

    if action == "session":
        session_action = request.get("session_action")
        if not isinstance(session_action, str) or not session_action.strip():
            raise ValueError("invalid_json: session_action is required for action=session")
        if session_action not in _SESSION_ACTIONS:
            raise ValueError(
                f"invalid_json: unsupported session_action '{session_action}'"
            )
        if session_action == "use":
            name = request.get("name")
            if not isinstance(name, str) or not name:
                raise ValueError("invalid_json: name is required for action=session/use")
        elif "name" in request:
            raise ValueError(
                "unknown_parameter: field 'name' is only supported for action=session/use"
            )
        return request

    for field_name, expected_type in _JSON_FIELD_TYPES[action].items():
        if field_name in request:
            _validate_json_type(action, field_name, request[field_name], expected_type)

    return request


def _json_request_to_argv(request):
    action = request["action"]
    argv = [action]

    if action == "session":
        session_action = request.get("session_action")
        if not isinstance(session_action, str) or not session_action.strip():
            raise ValueError("invalid_json: session_action is required for action=session")
        argv.append(session_action)
        if session_action == "use":
            name = request.get("name")
            if not isinstance(name, str) or not name:
                raise ValueError("invalid_json: name is required for action=session/use")
            argv.append(name)
        return argv

    for key, value in request.items():
        if key == "action" or value is None:
            continue
        flag = f"--{key.replace('_', '-')}"
        if isinstance(value, bool):
            if value:
                argv.append(flag)
            continue
        if isinstance(value, list):
            argv.extend([flag, ",".join(str(item) for item in value)])
            continue
        argv.extend([flag, str(value)])

    return argv


def parse_request_args(parser, argv=None):
    if argv is None:
        import sys

        argv = sys.argv[1:]

    argv = list(argv)
    if "--json" not in argv:
        return _parse_with_parser(parser, argv)

    json_positions = [index for index, token in enumerate(argv) if token == "--json"]
    if len(json_positions) > 1:
        raise ValueError("json_conflict: --json can only be provided once")

    json_index = json_positions[0]
    if json_index >= len(argv) - 1:
        raise ValueError("invalid_json: --json requires a payload")
    if len(argv) != 2 or json_index != 0:
        raise ValueError("json_conflict: --json cannot be mixed with flags arguments")

    request = _parse_json_request(argv[json_index + 1])
    return _parse_with_parser(parser, _json_request_to_argv(request))


def build_schema_payload():
    return {
        "actions": {
            "schema": {"fields": {}},
            "scan": {"fields": _JSON_FIELD_TYPES["scan"]},
            "connections": {"fields": _JSON_FIELD_TYPES["connections"]},
            "highlight": {"fields": _JSON_FIELD_TYPES["highlight"]},
            "inspect": {"fields": _JSON_FIELD_TYPES["inspect"]},
            "list_opened": {"fields": _JSON_FIELD_TYPES["list_opened"]},
            "session": {"fields": {"session_action": str, "name": str}},
        },
        "error_codes": list(_ERROR_CODES),
    }


def build_parser():
    parser = JsonArgumentParser(description="Simulink AI Bridge Core")
    parser.add_argument(
        "--json",
        dest="json_payload",
        help="JSON request payload. Use as a standalone entrypoint and do not mix with flags.",
    )
    subparsers = parser.add_subparsers(dest="action", required=True)
    subparsers.add_parser("schema", help="Return machine-readable command contract")

    scan_parser = subparsers.add_parser("scan", help="Read active model topology")
    scan_parser.add_argument(
        "--model", help="Optional specific model name from list_opened output"
    )
    scan_parser.add_argument(
        "--subsystem",
        help="Optional subsystem path under the model to scan",
    )
    scan_parser.add_argument(
        "--recursive",
        action="store_true",
        help="Recursively scan all nested blocks under the scan root",
    )
    scan_parser.add_argument(
        "--hierarchy",
        action="store_true",
        help="Include hierarchy tree in scan output (implies recursive)",
    )
    scan_parser.add_argument("--session", help="Session override for this command")
    scan_parser.add_argument(
        "--max-blocks",
        type=int,
        help="Limit number of block entries returned for scan action",
    )
    scan_parser.add_argument(
        "--fields",
        help="Comma-separated block fields to return (for example: name,type)",
    )

    connections_parser = subparsers.add_parser(
        "connections", help="Read upstream/downstream block connections"
    )
    connections_parser.add_argument(
        "--model", help="Optional specific model name from list_opened output"
    )
    connections_parser.add_argument(
        "--target", required=True, help="Block path to analyze"
    )
    connections_parser.add_argument("--session", help="Session override for this command")
    connections_parser.add_argument(
        "--direction",
        default="both",
        choices=["upstream", "downstream", "both"],
        help="Traversal direction from target block",
    )
    connections_parser.add_argument(
        "--depth",
        type=int,
        default=1,
        help="Traversal depth in hops (must be greater than zero)",
    )
    connections_parser.add_argument(
        "--detail",
        default="summary",
        choices=["summary", "ports", "lines"],
        help="Output detail level",
    )
    connections_parser.add_argument(
        "--include-handles",
        action="store_true",
        help="Include line handles in lines detail output",
    )

    highlight_parser = subparsers.add_parser("highlight", help="Highlight a block")
    highlight_parser.add_argument(
        "--target", required=True, help="Block path to highlight"
    )
    highlight_parser.add_argument("--session", help="Session override for this command")

    inspect_parser = subparsers.add_parser("inspect", help="Inspect block parameters")
    inspect_parser.add_argument(
        "--model", help="Optional specific model name from list_opened output"
    )
    inspect_parser.add_argument("--target", required=True, help="Block path to inspect")
    inspect_parser.add_argument(
        "--param",
        default="All",
        help="Parameter name to read, or 'All' to read available dialog parameters",
    )
    inspect_parser.add_argument(
        "--active-only",
        action="store_true",
        help="When used with --param All, return only currently active/effective parameters",
    )
    inspect_parser.add_argument(
        "--strict-active",
        action="store_true",
        help="Fail with inactive_parameter error when requested parameter is inactive",
    )
    inspect_parser.add_argument(
        "--resolve-effective",
        action="store_true",
        help="When requested parameter is inactive, return known effective source/value mapping",
    )
    inspect_parser.add_argument(
        "--summary",
        action="store_true",
        help="When used with --param All, include compact active/inactive/effective summary lists",
    )
    inspect_parser.add_argument("--session", help="Session override for this command")
    inspect_parser.add_argument(
        "--max-params",
        type=int,
        help="Limit number of parameter entries returned when --param All is used",
    )
    inspect_parser.add_argument(
        "--fields",
        help="Comma-separated top-level response fields to return",
    )

    list_opened_parser = subparsers.add_parser("list_opened", help="List loaded models")
    list_opened_parser.add_argument(
        "--session", help="Session override for this command"
    )

    session_parser = subparsers.add_parser(
        "session", help="Manage active MATLAB session"
    )
    session_subparsers = session_parser.add_subparsers(
        dest="session_action", required=True
    )

    session_subparsers.add_parser("list", help="List available MATLAB shared sessions")

    session_use_parser = session_subparsers.add_parser(
        "use", help="Set active session for future commands"
    )
    session_use_parser.add_argument("name", help="Session name, e.g. MATLAB_12345")

    session_subparsers.add_parser(
        "current", help="Show currently configured active session"
    )
    session_subparsers.add_parser("clear", help="Clear active session configuration")
    return parser


def run_action(args):
    if args.action == "schema":
        return build_schema_payload()

    validation_error = validate_args(args)
    if validation_error:
        return validation_error

    if args.action == "session":
        if args.session_action == "list":
            return command_session_list()
        if args.session_action == "use":
            return command_session_use(args.name)
        if args.session_action == "current":
            return command_session_current()
        if args.session_action == "clear":
            return command_session_clear()
        return make_error(
            "invalid_input",
            f"Unsupported session action '{args.session_action}'.",
            details={"session_action": args.session_action},
        )

    eng = connect_to_session(getattr(args, "session", None))

    if args.action == "scan":
        fields = getattr(args, "fields", None)
        parsed_fields = None
        if fields:
            parsed_fields = [item.strip() for item in str(fields).split(",") if item.strip()]
        return get_model_structure(
            eng,
            model_name=getattr(args, "model", None),
            recursive=getattr(args, "recursive", False),
            subsystem_path=getattr(args, "subsystem", None),
            hierarchy=getattr(args, "hierarchy", False),
            max_blocks=getattr(args, "max_blocks", None),
            fields=parsed_fields,
        )
    if args.action == "connections":
        return get_block_connections(
            eng,
            block_path=args.target,
            model_name=getattr(args, "model", None),
            direction=getattr(args, "direction", "both"),
            depth=getattr(args, "depth", 1),
            detail=getattr(args, "detail", "summary"),
            include_handles=getattr(args, "include_handles", False),
        )
    if args.action == "highlight":
        return highlight_block(eng, args.target)
    if args.action == "inspect":
        fields = getattr(args, "fields", None)
        parsed_fields = None
        if fields:
            parsed_fields = [item.strip() for item in str(fields).split(",") if item.strip()]
        return inspect_block(
            eng,
            args.target,
            args.param,
            getattr(args, "model", None),
            active_only=getattr(args, "active_only", False),
            strict_active=getattr(args, "strict_active", False),
            resolve_effective=getattr(args, "resolve_effective", False),
            summary=getattr(args, "summary", False),
            max_params=getattr(args, "max_params", None),
            fields=parsed_fields,
        )
    if args.action == "list_opened":
        return list_opened_models(eng)

    return make_error(
        "invalid_input",
        f"Unsupported action '{args.action}'.",
        details={"action": args.action},
    )


def main(argv=None):
    import sys
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
