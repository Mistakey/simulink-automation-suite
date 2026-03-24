import argparse
import json
import sys

from simulink_cli.errors import make_error
from simulink_cli.json_io import JsonArgumentParser, emit_json
from simulink_cli.session import SESSION_ERROR_MAP
from simulink_cli.validation import validate_json_type
from simulink_cli.actions import (
    connections,
    find,
    highlight,
    inspect_block,
    list_opened,
    model_new,
    model_open,
    model_save,
    scan,
    session_cmd,
    set_param,
)

# -- Action registry ----------------------------------------------------------
_ACTIONS = {
    "scan": scan,
    "connections": connections,
    "highlight": highlight,
    "inspect": inspect_block,
    "find": find,
    "list_opened": list_opened,
    "set_param": set_param,
    "session": session_cmd,
    "model_new": model_new,
    "model_open": model_open,
    "model_save": model_save,
}

_FRAMEWORK_ERRORS = {
    "invalid_input",
    "invalid_json",
    "json_conflict",
    "unknown_parameter",
}


# -- Schema generation --------------------------------------------------------
def build_schema_payload():
    actions = {}
    all_errors = set(_FRAMEWORK_ERRORS)
    for name, mod in _ACTIONS.items():
        actions[name] = {
            "description": mod.DESCRIPTION,
            "fields": mod.FIELDS,
        }
        all_errors.update(mod.ERRORS)
    return {
        "version": "2.2",
        "actions": {"schema": {"description": "Return machine-readable command contract and error-code catalog.", "fields": {}}, **actions},
        "error_codes": sorted(all_errors),
    }


# -- JSON direct parsing (no argv round-trip) ---------------------------------
def parse_json_request(raw_payload):
    try:
        request = json.loads(raw_payload)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid_json: {exc.msg}") from exc

    if not isinstance(request, dict):
        raise ValueError("invalid_json: payload must be a JSON object")

    action = request.get("action")
    if not isinstance(action, str) or not action.strip():
        raise ValueError("invalid_json: action is required")
    if action not in _ACTIONS:
        if action == "schema":
            allowed = {"action"}
            for key in request:
                if key not in allowed:
                    raise ValueError(
                        f"unknown_parameter: field '{key}' is not supported for action '{action}'"
                    )
            return "schema", {}
        raise ValueError(f"invalid_json: unsupported action '{action}'")

    mod = _ACTIONS[action]
    allowed = {"action"} | set(mod.FIELDS.keys())
    for key in request:
        if key not in allowed:
            raise ValueError(
                f"unknown_parameter: field '{key}' is not supported for action '{action}'"
            )

    # Validate required fields before filling defaults
    for field_name, field_meta in mod.FIELDS.items():
        if field_meta.get("required") and field_name not in request:
            raise ValueError(
                f"invalid_json: field '{field_name}' is required for action '{action}'"
            )

    args = {}
    for field_name, field_meta in mod.FIELDS.items():
        if field_name in request:
            validate_json_type(action, field_name, request[field_name], field_meta)
            args[field_name] = request[field_name]
        else:
            args[field_name] = field_meta.get("default")

    return action, args


# -- Argparse auto-generation (flag mode) ------------------------------------
def _add_argument_from_field(parser, name, meta):
    field_type = meta.get("type", "string")

    # Positional arguments (e.g., session_action for `session list`)
    if meta.get("positional"):
        kwargs = {"help": meta.get("description", "")}
        if "enum" in meta:
            kwargs["choices"] = meta["enum"]
        parser.add_argument(name, **kwargs)
        return

    # Optional positional arguments that also keep a flag form.
    if meta.get("positional_optional"):
        parser.add_argument(
            name,
            nargs="?",
            help=meta.get("description", ""),
            default=argparse.SUPPRESS,
        )
        parser.add_argument(
            f"--{name.replace('_', '-')}",
            dest=name,
            help=meta.get("description", ""),
            default=argparse.SUPPRESS,
        )
        return

    flag = f"--{name.replace('_', '-')}"
    kwargs = {"help": meta.get("description", ""), "dest": name}
    if field_type == "boolean":
        kwargs["action"] = argparse.BooleanOptionalAction
        kwargs["default"] = meta.get("default", False)
        parser.add_argument(flag, **kwargs)
        return
    if field_type == "integer":
        kwargs["type"] = int
        kwargs["default"] = meta.get("default")
    elif field_type == "array":
        kwargs["default"] = meta.get("default")
        # Accept comma-separated string (flag mode) for array fields
    else:
        kwargs["default"] = meta.get("default", "")
    if meta.get("required"):
        kwargs["required"] = True
    if "enum" in meta:
        kwargs["choices"] = meta["enum"]
    parser.add_argument(flag, **kwargs)


def build_parser():
    parser = JsonArgumentParser(description="Simulink Automation Suite CLI")
    parser.add_argument(
        "--json",
        dest="json_payload",
        help="JSON request payload. Mutually exclusive with flag mode.",
    )
    subparsers = parser.add_subparsers(dest="action", required=True)
    subparsers.add_parser(
        "schema", help="Return machine-readable command contract"
    )
    for name, mod in _ACTIONS.items():
        sub = subparsers.add_parser(name, help=mod.DESCRIPTION)
        for field_name, field_meta in mod.FIELDS.items():
            _add_argument_from_field(sub, field_name, field_meta)
    return parser


# -- Routing -------------------------------------------------------------------
def run_action(action_name, args):
    if action_name == "schema":
        return build_schema_payload()
    mod = _ACTIONS[action_name]
    validation_error = mod.validate(args)
    if validation_error:
        return validation_error
    return mod.execute(args)


# -- Error mapping (unified) --------------------------------------------------
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


def map_runtime_error(exc):
    code = str(exc).strip()
    if code in SESSION_ERROR_MAP:
        msg, fix = SESSION_ERROR_MAP[code]
        return make_error(code, msg, details={"cause": code}, suggested_fix=fix)
    return make_error(
        "runtime_error", str(exc), details={"cause": str(exc)}
    )


# -- Entry point ---------------------------------------------------------------
def _extract_json_payload(argv):
    if argv is None:
        argv = sys.argv[1:]
    argv = list(argv)
    if "--json" not in argv:
        return None, argv

    json_positions = [i for i, t in enumerate(argv) if t == "--json"]
    if len(json_positions) > 1:
        raise ValueError("json_conflict: --json can only be provided once")

    idx = json_positions[0]
    if idx >= len(argv) - 1:
        raise ValueError("invalid_json: --json requires a payload")
    if len(argv) != 2 or idx != 0:
        raise ValueError(
            "json_conflict: --json cannot be mixed with flags arguments"
        )
    return argv[idx + 1], None


def _parse_flag_mode(argv):
    parser = build_parser()
    try:
        parsed = parser.parse_args(argv)
    except ValueError as exc:
        message = str(exc).strip()
        if message.startswith("unrecognized arguments:"):
            raise ValueError(f"unknown_parameter: {message}") from exc
        raise ValueError(f"invalid_input: {message}") from exc
    action_name = parsed.action
    if action_name == "schema":
        return "schema", {}
    args = {k: v for k, v in vars(parsed).items() if k not in ("action", "json_payload")}
    # Parse comma-separated fields string into list (flag mode compat)
    for field_name, field_meta in _ACTIONS[action_name].FIELDS.items():
        if field_meta.get("type") == "array" and isinstance(args.get(field_name), str):
            args[field_name] = [s.strip() for s in args[field_name].split(",") if s.strip()]
    return action_name, args


def main(argv=None):
    try:
        raw_json, remaining = _extract_json_payload(argv)
        if raw_json is not None:
            action_name, args = parse_json_request(raw_json)
        else:
            action_name, args = _parse_flag_mode(remaining)
        result = run_action(action_name, args)
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
