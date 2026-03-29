"""line_delete action — remove a signal line between two block ports."""

from simulink_cli import matlab_transport
from simulink_cli.errors import make_error
from simulink_cli.validation import validate_matlab_name_field, validate_text_field
from simulink_cli.session import safe_connect_to_session

DESCRIPTION = "Delete a signal line between two block ports."

FIELDS = {
    "model": {
        "type": "string",
        "required": True,
        "default": None,
        "description": "Target model or subsystem path.",
    },
    "src_block": {
        "type": "string",
        "required": True,
        "default": None,
        "description": "Source block name (local to model, must not contain '/').",
    },
    "src_port": {
        "type": "port",
        "required": True,
        "default": None,
        "description": "Source port — integer (signal) or string name (physical, e.g. 'RConn1').",
    },
    "dst_block": {
        "type": "string",
        "required": True,
        "default": None,
        "description": "Destination block name (local to model, must not contain '/').",
    },
    "dst_port": {
        "type": "port",
        "required": True,
        "default": None,
        "description": "Destination port — integer (signal) or string name (physical, e.g. 'LConn1').",
    },
    "session": {
        "type": "string",
        "required": False,
        "default": None,
        "description": "MATLAB session name override.",
    },
}

ERRORS = [
    "engine_unavailable",
    "no_session",
    "session_not_found",
    "session_required",
    "model_not_found",
    "block_not_found",
    "line_not_found",
    "runtime_error",
]


def validate(args):
    """Validate line_delete arguments. Returns error dict or None."""
    err = validate_matlab_name_field("model", args.get("model"))
    if err is not None:
        return err

    model = args.get("model")
    if model is None or (isinstance(model, str) and not model):
        return make_error(
            "invalid_input",
            "Field 'model' is required.",
            details={"field": "model"},
        )

    for field in ("src_block", "dst_block"):
        value = args.get(field)
        err = validate_matlab_name_field(field, value)
        if err is not None:
            return err
        if value is None or (isinstance(value, str) and not value):
            return make_error(
                "invalid_input",
                f"Field '{field}' is required.",
                details={"field": field},
            )
        if isinstance(value, str) and "/" in value:
            return make_error(
                "invalid_input",
                f"Field '{field}' must not contain '/' (use local block name, not path).",
                details={"field": field},
            )

    for field in ("src_port", "dst_port"):
        value = args.get(field)
        if value is None:
            return make_error(
                "invalid_input",
                f"Field '{field}' is required.",
                details={"field": field},
            )
        if isinstance(value, bool):
            return make_error(
                "invalid_input",
                f"Field '{field}' must be a positive integer or port name string.",
                details={"field": field},
            )
        if isinstance(value, int):
            if value < 1:
                return make_error(
                    "invalid_input",
                    f"Field '{field}' must be a positive integer or port name string.",
                    details={"field": field},
                )
        elif isinstance(value, str):
            if not value:
                return make_error(
                    "invalid_input",
                    f"Field '{field}' must not be empty.",
                    details={"field": field},
                )
        else:
            return make_error(
                "invalid_input",
                f"Field '{field}' must be a positive integer or port name string.",
                details={"field": field},
            )

    err = validate_text_field("session", args.get("session"))
    if err is not None:
        return err
    return None


def execute(args):
    """Execute line_delete: remove a signal line between two block ports."""
    eng, err = safe_connect_to_session(args.get("session"))
    if err is not None:
        return err

    model = args["model"]
    src_block = args["src_block"]
    src_port = args["src_port"]
    dst_block = args["dst_block"]
    dst_port = args["dst_port"]

    # Precondition 1: model is loaded
    try:
        matlab_transport.get_param(eng, model, "Handle")
    except Exception:
        return make_error(
            "model_not_found",
            f"Model '{model}' is not loaded.",
            details={"model": model},
            suggested_fix=f"Open the model first: {{\"action\":\"model_open\",\"path\":\"{model}.slx\"}}",
        )

    # Precondition 2: source block exists
    try:
        matlab_transport.get_param(eng, f"{model}/{src_block}", "Handle")
    except Exception:
        return make_error(
            "block_not_found",
            f"Source block '{src_block}' not found in '{model}'.",
            details={"block": src_block, "role": "source"},
            suggested_fix="Check spelling. Use find to list blocks in the model.",
        )

    # Precondition 3: destination block exists
    try:
        matlab_transport.get_param(eng, f"{model}/{dst_block}", "Handle")
    except Exception:
        return make_error(
            "block_not_found",
            f"Destination block '{dst_block}' not found in '{model}'.",
            details={"block": dst_block, "role": "destination"},
            suggested_fix="Check spelling. Use find to list blocks in the model.",
        )

    # Execute
    src_str = f"{src_block}/{src_port}"
    dst_str = f"{dst_block}/{dst_port}"
    try:
        matlab_transport.delete_line(eng, model, src_str, dst_str)
    except Exception as exc:
        msg = str(exc)
        if "not found" in msg.lower() or "no line found" in msg.lower():
            return make_error(
                "line_not_found",
                f"No line found from '{src_str}' to '{dst_str}' in '{model}'.",
                details={"src": src_str, "dst": dst_str},
                suggested_fix="Use connections to inspect existing lines in the model.",
            )
        return make_error(
            "runtime_error",
            f"Failed to delete line from '{src_str}' to '{dst_str}'.",
            details={"src": src_str, "dst": dst_str, "cause": msg},
        )

    # No verification step — no exception means success
    rollback = {
        "action": "line_add",
        "model": model,
        "src_block": src_block,
        "src_port": src_port,
        "dst_block": dst_block,
        "dst_port": dst_port,
        "available": True,
    }
    if args.get("session") is not None:
        rollback["session"] = args["session"]

    return {
        "action": "line_delete",
        "model": model,
        "src_block": src_block,
        "src_port": src_port,
        "dst_block": dst_block,
        "dst_port": dst_port,
        "rollback": rollback,
    }
