"""model_save action — save a loaded Simulink model to disk."""

from simulink_cli import matlab_transport
from simulink_cli.errors import make_error
from simulink_cli.validation import validate_matlab_name_field, validate_text_field
from simulink_cli.session import safe_connect_to_session

DESCRIPTION = "Save a loaded Simulink model to disk."

FIELDS = {
    "model": {
        "type": "string",
        "required": True,
        "default": None,
        "description": "Name of the loaded model to save.",
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
    "model_save_failed",
    "runtime_error",
]


def validate(args):
    """Validate model_save arguments. Returns error dict or None."""
    err = validate_matlab_name_field("model", args.get("model"))
    if err is not None:
        return err
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
    """Execute model_save: save a loaded model to disk."""
    eng, err = safe_connect_to_session(args.get("session"))
    if err is not None:
        return err

    model = args["model"]

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

    # Save
    try:
        matlab_transport.save_system(eng, model)
    except Exception as exc:
        return make_error(
            "model_save_failed",
            f"Failed to save model '{model}'.",
            details={"model": model, "cause": str(exc)},
            suggested_fix="Check file permissions and disk space.",
        )

    return {
        "action": "model_save",
        "model": model,
    }
