"""line_add action — connect two block ports with a signal line."""

from simulink_cli import matlab_transport
from simulink_cli.errors import make_error
from simulink_cli.validation import validate_matlab_name_field, validate_text_field
from simulink_cli.session import safe_connect_to_session

DESCRIPTION = "Connect two block ports with a signal line."

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
        "type": "integer",
        "required": True,
        "default": None,
        "description": "Source output port number.",
    },
    "dst_block": {
        "type": "string",
        "required": True,
        "default": None,
        "description": "Destination block name (local to model, must not contain '/').",
    },
    "dst_port": {
        "type": "integer",
        "required": True,
        "default": None,
        "description": "Destination input port number.",
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
    "port_not_found",
    "line_already_exists",
    "verification_failed",
    "runtime_error",
]


def validate(args):
    """Validate line_add arguments. Returns error dict or None."""
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
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            return make_error(
                "invalid_input",
                f"Field '{field}' must be a positive integer.",
                details={"field": field},
            )

    err = validate_text_field("session", args.get("session"))
    if err is not None:
        return err
    return None


def execute(args):
    """Execute line_add: connect two block ports with a signal line."""
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
            suggested_fix="Add the block first or check spelling. Use find to list blocks in the model.",
        )

    # Precondition 3: destination block exists
    try:
        matlab_transport.get_param(eng, f"{model}/{dst_block}", "Handle")
    except Exception:
        return make_error(
            "block_not_found",
            f"Destination block '{dst_block}' not found in '{model}'.",
            details={"block": dst_block, "role": "destination"},
            suggested_fix="Add the block first or check spelling. Use find to list blocks in the model.",
        )

    # Execute
    src_str = f"{src_block}/{src_port}"
    dst_str = f"{dst_block}/{dst_port}"
    try:
        result = matlab_transport.add_line(eng, model, src_str, dst_str)
        line_handle = result["value"]
    except Exception as exc:
        msg = str(exc)
        if "already connected" in msg.lower() or "already exists" in msg.lower():
            return make_error(
                "line_already_exists",
                f"Destination port '{dst_str}' is already connected.",
                details={"dst_block": dst_block, "dst_port": dst_port},
                suggested_fix="Delete the existing line first or use a different port.",
            )
        if "port" in msg.lower() and ("not found" in msg.lower() or "invalid" in msg.lower()):
            return make_error(
                "port_not_found",
                f"Invalid port specification: {msg}",
                details={"src": src_str, "dst": dst_str, "cause": msg},
                suggested_fix="Check port numbers. Use connections or inspect to discover available ports.",
            )
        return make_error(
            "runtime_error",
            f"Failed to add line from '{src_str}' to '{dst_str}'.",
            details={"src": src_str, "dst": dst_str, "cause": msg},
        )

    # Verify
    try:
        matlab_transport.get_param(eng, line_handle, "Handle")
    except Exception:
        return make_error(
            "verification_failed",
            "Line was added but could not be verified.",
            details={"write_state": "attempted"},
        )

    rollback = {
        "action": "line_delete",
        "model": model,
        "line_handle": line_handle,
        "available": False,
        "note": "line_delete not yet implemented (v2.5.0)",
    }
    if args.get("session") is not None:
        rollback["session"] = args["session"]

    return {
        "action": "line_add",
        "model": model,
        "line_handle": line_handle,
        "verified": True,
        "rollback": rollback,
    }
