"""simulate_cmd action — run simulation on a loaded Simulink model."""

from simulink_cli import matlab_transport
from simulink_cli.errors import make_error
from simulink_cli.validation import validate_matlab_name_field, validate_text_field
from simulink_cli.session import safe_connect_to_session

DESCRIPTION = "Run simulation on a loaded Simulink model."

FIELDS = {
    "model": {
        "type": "string",
        "required": True,
        "default": None,
        "description": "Model name to simulate.",
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
    "simulation_failed",
    "runtime_error",
]


def validate(args):
    """Validate simulate arguments. Returns error dict or None."""
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
    """Execute simulate: run simulation on a loaded Simulink model."""
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

    # Execute simulation
    try:
        result = matlab_transport.sim(eng, model)
        warnings = result.get("warnings", [])
    except Exception as exc:
        msg = str(exc).lower()
        if "simulation" in msg or "solver" in msg or "algebraic" in msg:
            return make_error(
                "simulation_failed",
                f"Simulation failed for model '{model}': {exc}",
                details={"model": model, "cause": str(exc)},
                suggested_fix="Check model for errors (algebraic loops, solver mismatches, unconnected ports).",
            )
        return make_error(
            "runtime_error",
            f"Unexpected error simulating model '{model}': {exc}",
            details={"model": model, "cause": str(exc)},
        )

    return {
        "action": "simulate",
        "model": model,
        "warnings": warnings,
    }
