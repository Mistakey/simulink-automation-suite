"""model_update action — compile/update a loaded Simulink model diagram."""

from simulink_cli import matlab_transport
from simulink_cli.errors import make_error
from simulink_cli.validation import validate_matlab_name_field, validate_text_field
from simulink_cli.session import safe_connect_to_session

DESCRIPTION = "Compile/update a loaded Simulink model diagram."

FIELDS = {
    "model": {
        "type": "string",
        "required": True,
        "default": None,
        "description": "Model name to update/compile.",
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
    "update_failed",
    "runtime_error",
]


def validate(args):
    """Validate model_update arguments. Returns error dict or None."""
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
    """Execute model_update: compile/update a loaded model diagram."""
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

    # Execute update
    try:
        result = matlab_transport.update_diagram(eng, model)
        output = result.get("value", "") or ""
        warnings = result.get("warnings", [])
    except Exception as exc:
        msg = str(exc).lower()
        if "compile" in msg or "update" in msg or "diagram" in msg:
            return make_error(
                "update_failed",
                f"Failed to update model '{model}': {exc}",
                details={"model": model, "cause": str(exc)},
                suggested_fix="Check model for errors (unconnected ports, algebraic loops, type mismatches).",
            )
        return make_error(
            "runtime_error",
            f"Unexpected error updating model '{model}': {exc}",
            details={"model": model, "cause": str(exc)},
        )

    diagnostics = (
        [line.strip() for line in output.split("\n") if line.strip()]
        if output
        else []
    )

    return {
        "action": "model_update",
        "model": model,
        "diagnostics": diagnostics,
        "warnings": warnings,
    }
