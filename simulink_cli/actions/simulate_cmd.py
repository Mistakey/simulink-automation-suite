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
    "stop_time": {
        "type": "number",
        "required": False,
        "default": None,
        "description": "Override simulation stop time (seconds). Does not modify the model.",
    },
    "max_step": {
        "type": "number",
        "required": False,
        "default": None,
        "description": "Override solver maximum step size (seconds). Does not modify the model.",
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

    for field_name in ("stop_time", "max_step"):
        value = args.get(field_name)
        if value is not None and (not isinstance(value, (int, float)) or value <= 0):
            return make_error(
                "invalid_input",
                f"Field '{field_name}' must be a positive number.",
                details={"field": field_name, "value": value},
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
    sim_params = {}
    if args.get("stop_time") is not None:
        sim_params["StopTime"] = args["stop_time"]
    if args.get("max_step") is not None:
        sim_params["MaxStep"] = args["max_step"]

    try:
        result = matlab_transport.sim(eng, model, **sim_params)
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

    response = {
        "action": "simulate",
        "model": model,
        "warnings": warnings,
    }
    if sim_params:
        response["overrides"] = {k: v for k, v in sim_params.items()}
    return response
