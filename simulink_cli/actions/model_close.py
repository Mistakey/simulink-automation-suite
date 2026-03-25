"""model_close action — close a loaded Simulink model."""

from simulink_cli import matlab_transport
from simulink_cli.errors import make_error
from simulink_cli.validation import validate_matlab_name_field, validate_text_field
from simulink_cli.session import safe_connect_to_session

DESCRIPTION = "Close a loaded Simulink model."

FIELDS = {
    "model": {
        "type": "string",
        "required": True,
        "default": None,
        "description": "Model name to close.",
    },
    "force": {
        "type": "boolean",
        "required": False,
        "default": False,
        "description": "Close even if model has unsaved changes.",
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
    "model_dirty",
    "runtime_error",
]


def validate(args):
    """Validate model_close arguments. Returns error dict or None."""
    err = validate_matlab_name_field("model", args.get("model"))
    if err is not None:
        return err
    force = args.get("force")
    if force is not None and not isinstance(force, bool):
        return make_error(
            "invalid_input",
            "Field 'force' must be a boolean.",
            details={"field": "force"},
        )

    err = validate_text_field("session", args.get("session"))
    if err is not None:
        return err

    model = args.get("model")
    if model is None or (isinstance(model, str) and not model):
        return make_error(
            "invalid_input",
            "Field 'model' is required.",
            details={"field": "model"},
        )
    return None


def execute(args):
    """Execute model_close: close a loaded Simulink model."""
    eng, err = safe_connect_to_session(args.get("session"))
    if err is not None:
        return err

    model = args["model"]
    force = args.get("force", False)

    # Check model is loaded
    try:
        matlab_transport.get_param(eng, model, "Handle")
    except Exception:
        return make_error(
            "model_not_found",
            f"Model '{model}' is not loaded.",
            details={"model": model},
            suggested_fix="Open or create the model first with model_open or model_new.",
        )

    # Check dirty state unless force
    if not force:
        try:
            dirty = matlab_transport.get_param(eng, model, "Dirty")
            if dirty["value"] == "on":
                return make_error(
                    "model_dirty",
                    f"Model '{model}' has unsaved changes.",
                    details={"model": model},
                    suggested_fix=(
                        f"Save first with {{\"action\":\"model_save\",\"model\":\"{model}\"}}"
                        f" or close with {{\"action\":\"model_close\",\"model\":\"{model}\",\"force\":true}}"
                    ),
                )
        except Exception:
            pass  # If we can't read dirty state, proceed with close

    # Execute
    try:
        matlab_transport.close_system(eng, model)
    except Exception as exc:
        return make_error(
            "runtime_error",
            f"Failed to close model '{model}'.",
            details={"model": model, "cause": str(exc)},
        )

    return {
        "action": "model_close",
        "model": model,
        "force": force,
    }
