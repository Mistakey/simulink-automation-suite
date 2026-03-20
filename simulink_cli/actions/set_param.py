"""Set-param action — set a block parameter with dry-run preview and rollback."""

from simulink_cli import matlab_transport
from simulink_cli.errors import make_error
from simulink_cli.validation import (
    validate_matlab_name_field,
    validate_text_field,
    validate_value_field,
)
from simulink_cli.session import safe_connect_to_session

DESCRIPTION = "Set a block parameter with dry-run preview and rollback support."

FIELDS = {
    "target": {
        "type": "string",
        "required": True,
        "default": None,
        "description": "Full block path to modify.",
    },
    "param": {
        "type": "string",
        "required": True,
        "default": None,
        "description": "Parameter name.",
    },
    "value": {
        "type": "string",
        "required": True,
        "default": None,
        "description": "New parameter value (always string — MATLAB handles conversion).",
    },
    "expected_current_value": {
        "type": "string",
        "required": False,
        "default": None,
        "description": "Optional guarded-execute precondition from a dry-run preview.",
    },
    "dry_run": {
        "type": "boolean",
        "required": False,
        "default": True,
        "description": "Preview mode — show diff without writing. Defaults to true.",
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
    "block_not_found",
    "param_not_found",
    "set_param_failed",
    "precondition_failed",
    "verification_failed",
    "runtime_error",
]


def validate(args):
    """Validate set_param arguments. Returns error dict or None."""
    for field_name in ("target", "param"):
        err = validate_matlab_name_field(field_name, args.get(field_name))
        if err is not None:
            return err
    err = validate_text_field("session", args.get("session"))
    if err is not None:
        return err
    for field_name in ("value", "expected_current_value"):
        err = validate_value_field(field_name, args.get(field_name))
        if err is not None:
            return err

    for required_field in ("target", "param", "value"):
        val = args.get(required_field)
        if val is None or (
            required_field != "value"
            and isinstance(val, str)
            and not val
        ):
            return make_error(
                "invalid_input",
                f"Field '{required_field}' is required.",
                details={"field": required_field},
            )

    return None


def execute(args):
    """Execute set_param action against a live MATLAB session."""
    eng, err = safe_connect_to_session(args.get("session"))
    if err is not None:
        return err

    target = args["target"]
    param = args["param"]
    value = args["value"]
    dry_run = args.get("dry_run", True)

    # 0. Validate target block exists
    try:
        matlab_transport.get_param(eng, target, "Handle")
    except Exception:
        return make_error(
            "block_not_found",
            f"Block '{target}' not found in the model.",
            details={"target": target},
            suggested_fix="Run simulink-scan find or scan to locate the correct block path.",
        )

    # 1. Validate parameter exists and read current value
    try:
        current_value = str(matlab_transport.get_param(eng, target, param)["value"])
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

    apply_payload = {
        "action": "set_param",
        "target": target,
        "param": param,
        "value": str(value),
        "dry_run": False,
        "expected_current_value": current_value,
    }
    if args.get("session") is not None:
        rollback["session"] = args["session"]
        apply_payload["session"] = args["session"]

    # 2. Dry-run: return diff, do NOT write
    if dry_run:
        return {
            "action": "set_param",
            "dry_run": True,
            "write_state": "not_attempted",
            "target": target,
            "param": param,
            "current_value": current_value,
            "proposed_value": str(value),
            "apply_payload": apply_payload,
            "rollback": rollback,
        }

    expected_current_value = args.get("expected_current_value")
    if expected_current_value is not None and current_value != expected_current_value:
        return make_error(
            "precondition_failed",
            "Preview is stale; current value changed before execute.",
            details={
                "target": target,
                "param": param,
                "expected_current_value": expected_current_value,
                "observed_current_value": current_value,
                "write_state": "not_attempted",
                "safe_to_retry": True,
                "recommended_recovery": "rerun_dry_run",
            },
            suggested_fix="Rerun dry-run to capture the latest value before executing.",
        )

    # 3. Execute: write + read-back verification
    write_state = "not_attempted"
    try:
        write_state = "attempted"
        matlab_transport.set_param(eng, target, param, str(value))
        observed = str(matlab_transport.get_param(eng, target, param)["value"])
    except Exception as exc:
        return make_error(
            "set_param_failed",
            f"Failed to set parameter '{param}' on '{target}'.",
            details={
                "target": target,
                "param": param,
                "value": str(value),
                "write_state": write_state,
                "rollback": rollback,
                "safe_to_retry": False,
                "recommended_recovery": "rollback",
                "cause": str(exc),
            },
            suggested_fix="Inspect the current value and use rollback if the model may have changed.",
        )

    if observed != str(value):
        return make_error(
            "verification_failed",
            f"Write could not be verified for parameter '{param}' on '{target}'.",
            details={
                "target": target,
                "param": param,
                "value": str(value),
                "write_state": "verification_failed",
                "rollback": rollback,
                "observed": observed,
                "safe_to_retry": False,
                "recommended_recovery": "rollback",
            },
            suggested_fix="Inspect the observed value and replay rollback if you need to restore the prior state.",
        )

    return {
        "action": "set_param",
        "dry_run": False,
        "write_state": "verified",
        "target": target,
        "param": param,
        "previous_value": current_value,
        "new_value": str(value),
        "verified": True,
        "rollback": rollback,
    }
