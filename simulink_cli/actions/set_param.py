"""Set-param action — set a block parameter with dry-run preview and rollback."""

from simulink_cli.errors import make_error
from simulink_cli.validation import validate_text_field
from simulink_cli.session import connect_to_session

DESCRIPTION = "Set a block parameter with dry-run preview and rollback support."

FIELDS = {
    "target": {
        "type": "string",
        "required": True,
        "default": None,
        "description": "Block path to modify.",
    },
    "param": {
        "type": "string",
        "required": True,
        "default": None,
        "description": "Parameter name to set.",
    },
    "value": {
        "type": "string",
        "required": True,
        "default": None,
        "description": "New value for the parameter.",
    },
    "dry_run": {
        "type": "boolean",
        "required": False,
        "default": True,
        "description": "Preview change without writing (default: true).",
    },
    "model": {
        "type": "string",
        "required": False,
        "default": None,
        "description": "Optional model name for path resolution.",
    },
    "session": {
        "type": "string",
        "required": False,
        "default": None,
        "description": "Session override for this command.",
    },
}

ERRORS = [
    "block_not_found",
    "param_not_found",
    "set_param_failed",
    "model_not_found",
    "runtime_error",
]


def validate(args):
    """Validate set_param arguments. Returns error dict or None."""
    for field_name in ("target", "param", "value", "model", "session"):
        err = validate_text_field(field_name, args.get(field_name))
        if err is not None:
            return err

    for required_field in ("target", "param", "value"):
        val = args.get(required_field)
        if val is None or (isinstance(val, str) and not val):
            return make_error(
                "invalid_input",
                f"Field '{required_field}' is required.",
                details={"field": required_field},
            )

    return None


def execute(args):
    """Execute set_param action against a live MATLAB session."""
    session = args.get("session")

    try:
        eng = connect_to_session(session)
    except RuntimeError as exc:
        error_code = str(exc).strip()
        if error_code == "no_session":
            return make_error(
                "no_session",
                "No shared MATLAB session found.",
                details={},
                suggested_fix="Run matlab.engine.shareEngine in MATLAB, then retry.",
            )
        if error_code == "session_not_found":
            return make_error(
                "session_not_found",
                f"Session '{session}' not found.",
                details={"session": session},
                suggested_fix="Run `session list` and pass an exact session name.",
            )
        if error_code == "session_required":
            return make_error(
                "session_required",
                "Multiple MATLAB sessions found. Pass --session to disambiguate.",
                details={},
                suggested_fix="Run `session list` and pass an exact session name via --session.",
            )
        return make_error(
            "runtime_error",
            "Failed to connect to MATLAB session.",
            details={"cause": str(exc)},
        )

    target = args["target"]
    param = args["param"]
    value = args["value"]
    dry_run = args.get("dry_run", True)

    # 0. Validate target block exists
    try:
        eng.get_param(target, "Handle")
    except Exception:
        return make_error(
            "block_not_found",
            f"Block '{target}' not found in the model.",
            details={"target": target},
            suggested_fix="Run simulink-scan find or scan to locate the correct block path.",
        )

    # 1. Validate parameter exists and read current value
    try:
        current_value = str(eng.get_param(target, param))
    except Exception:
        return make_error(
            "param_not_found",
            f"Parameter '{param}' not found on block '{target}'.",
            details={"target": target, "param": param},
            suggested_fix="Run simulink-scan inspect to list available parameters.",
        )

    rollback = {
        "action": "set_param",
        "target": target,
        "param": param,
        "value": current_value,
        "dry_run": False,
    }

    # 2. Dry-run: return diff, do NOT write
    if dry_run:
        return {
            "action": "set_param",
            "dry_run": True,
            "target": target,
            "param": param,
            "current_value": current_value,
            "proposed_value": str(value),
            "rollback": rollback,
        }

    # 3. Execute: write + read-back verification
    try:
        eng.set_param(target, param, str(value))
    except Exception as exc:
        return make_error(
            "set_param_failed",
            f"Failed to set parameter '{param}' on '{target}'.",
            details={
                "target": target,
                "param": param,
                "value": str(value),
                "cause": str(exc),
            },
            suggested_fix="Check that the value is valid for this parameter type.",
        )

    try:
        verified_value = str(eng.get_param(target, param))
    except Exception:
        verified_value = None

    return {
        "action": "set_param",
        "dry_run": False,
        "target": target,
        "param": param,
        "previous_value": current_value,
        "new_value": str(value),
        "verified": verified_value == str(value),
        "rollback": rollback,
    }
