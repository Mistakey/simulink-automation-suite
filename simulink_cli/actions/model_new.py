"""model_new action — create a new Simulink model."""

from simulink_cli import matlab_transport
from simulink_cli.errors import make_error
from simulink_cli.validation import validate_matlab_name_field, validate_text_field
from simulink_cli.session import safe_connect_to_session

DESCRIPTION = "Create a new Simulink model."

FIELDS = {
    "name": {
        "type": "string",
        "required": True,
        "default": None,
        "description": "Name for the new model.",
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
    "model_already_loaded",
    "verification_failed",
    "runtime_error",
]


def validate(args):
    """Validate model_new arguments. Returns error dict or None."""
    err = validate_matlab_name_field("name", args.get("name"))
    if err is not None:
        return err
    err = validate_text_field("session", args.get("session"))
    if err is not None:
        return err

    name = args.get("name")
    if name is None or (isinstance(name, str) and not name):
        return make_error(
            "invalid_input",
            "Field 'name' is required.",
            details={"field": "name"},
        )
    return None


def execute(args):
    """Execute model_new: create a new Simulink model."""
    eng, err = safe_connect_to_session(args.get("session"))
    if err is not None:
        return err

    name = args["name"]

    # Precondition: model not already loaded
    try:
        matlab_transport.get_param(eng, name, "Handle")
        return make_error(
            "model_already_loaded",
            f"Model '{name}' is already loaded.",
            details={"name": name},
            suggested_fix="Use a different name or close the existing model first.",
        )
    except Exception:
        pass  # Expected — model not loaded, proceed

    # Execute
    try:
        matlab_transport.new_system(eng, name)
    except Exception as exc:
        return make_error(
            "runtime_error",
            f"Failed to create model '{name}'.",
            details={"name": name, "cause": str(exc)},
            suggested_fix="Check the model name for invalid characters.",
        )

    # Verify
    try:
        matlab_transport.get_param(eng, name, "Handle")
    except Exception:
        return make_error(
            "verification_failed",
            f"Model '{name}' was created but could not be verified.",
            details={"name": name, "write_state": "verification_failed"},
        )

    rollback = {
        "action": "model_close",
        "model": name,
        "available": False,
        "note": "model_close not yet implemented; use MATLAB close_system('"
        + name
        + "', 0) manually to undo",
    }
    if args.get("session") is not None:
        rollback["session"] = args["session"]

    return {
        "action": "model_new",
        "name": name,
        "verified": True,
        "rollback": rollback,
    }
