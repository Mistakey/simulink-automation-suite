"""model_open action — open a Simulink model from file."""

from simulink_cli import matlab_transport
from simulink_cli.errors import make_error
from simulink_cli.validation import validate_matlab_name_field, validate_text_field
from simulink_cli.session import safe_connect_to_session

DESCRIPTION = "Open a Simulink model from file path or MATLAB path."

FIELDS = {
    "path": {
        "type": "string",
        "required": True,
        "default": None,
        "description": "File path or model name to open.",
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
    "runtime_error",
]


def validate(args):
    """Validate model_open arguments. Returns error dict or None."""
    err = validate_matlab_name_field("path", args.get("path"))
    if err is not None:
        return err
    err = validate_text_field("session", args.get("session"))
    if err is not None:
        return err

    path = args.get("path")
    if path is None or (isinstance(path, str) and not path):
        return make_error(
            "invalid_input",
            "Field 'path' is required.",
            details={"field": "path"},
        )
    return None


def execute(args):
    """Execute model_open: open a Simulink model.

    Note: MATLAB's open_system is idempotent — if the model is already
    open, it simply brings the window to the foreground. This is not
    treated as an error.
    """
    eng, err = safe_connect_to_session(args.get("session"))
    if err is not None:
        return err

    path = args["path"]

    try:
        matlab_transport.open_system(eng, path)
    except Exception as exc:
        error_msg = str(exc)
        if "not found" in error_msg.lower() or "cannot find" in error_msg.lower():
            return make_error(
                "model_not_found",
                f"Model or file '{path}' not found.",
                details={"path": path, "cause": error_msg},
                suggested_fix="Check the file path or ensure the model is on the MATLAB path.",
            )
        return make_error(
            "runtime_error",
            f"Failed to open '{path}'.",
            details={"path": path, "cause": error_msg},
        )

    return {
        "action": "model_open",
        "path": path,
    }
