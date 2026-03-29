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
        "required": False,
        "default": None,
        "description": "Parameter name (mutually exclusive with 'params').",
    },
    "value": {
        "type": "string",
        "required": False,
        "default": None,
        "description": "New parameter value (mutually exclusive with 'params').",
    },
    "params": {
        "type": "object",
        "required": False,
        "default": None,
        "description": "Multiple parameter-value pairs for atomic update (mutually exclusive with 'param'/'value').",
    },
    "expected_current_value": {
        "type": "string",
        "required": False,
        "default": None,
        "description": "Optional guarded-execute precondition from a single-param dry-run preview.",
    },
    "expected_current_values": {
        "type": "object",
        "required": False,
        "default": None,
        "description": "Optional guarded-execute precondition from a multi-param dry-run preview.",
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
    err = validate_matlab_name_field("target", args.get("target"))
    if err is not None:
        return err
    err = validate_text_field("session", args.get("session"))
    if err is not None:
        return err

    target = args.get("target")
    if target is None or (isinstance(target, str) and not target):
        return make_error(
            "invalid_input",
            "Field 'target' is required.",
            details={"field": "target"},
        )

    param = args.get("param")
    value = args.get("value")
    params = args.get("params")

    single_mode = param is not None or value is not None
    multi_mode = params is not None

    if single_mode and multi_mode:
        return make_error(
            "invalid_input",
            "Fields 'param'/'value' and 'params' are mutually exclusive.",
            details={"field": "params"},
        )
    if not single_mode and not multi_mode:
        return make_error(
            "invalid_input",
            "Either 'param'+'value' or 'params' must be provided.",
            details={"field": "param"},
        )

    if single_mode:
        for field_name in ("param", "value"):
            if field_name == "param":
                err = validate_matlab_name_field(field_name, args.get(field_name))
            else:
                err = validate_value_field(field_name, args.get(field_name))
            if err is not None:
                return err
        for required_field in ("param", "value"):
            val = args.get(required_field)
            if val is None or (
                required_field != "value"
                and isinstance(val, str)
                and not val
            ):
                return make_error(
                    "invalid_input",
                    f"Field '{required_field}' is required when using single-param mode.",
                    details={"field": required_field},
                )
        err = validate_value_field("expected_current_value", args.get("expected_current_value"))
        if err is not None:
            return err

    if multi_mode:
        if not params:
            return make_error(
                "invalid_input",
                "Field 'params' must not be empty.",
                details={"field": "params"},
            )
        for k, v in params.items():
            if not isinstance(k, str) or not k:
                return make_error(
                    "invalid_input",
                    "All keys in 'params' must be non-empty strings.",
                    details={"field": "params"},
                )
            err = validate_matlab_name_field(k, k)
            if err is not None:
                return err
            if not isinstance(v, str):
                return make_error(
                    "invalid_input",
                    f"All values in 'params' must be strings, got {type(v).__name__} for key '{k}'.",
                    details={"field": "params", "key": k},
                )

    return None


def execute(args):
    """Execute set_param action against a live MATLAB session."""
    eng, err = safe_connect_to_session(args.get("session"))
    if err is not None:
        return err

    if args.get("params") is not None:
        return _execute_multi(eng, args)
    return _execute_single(eng, args)


def _execute_single(eng, args):
    """Single-param set_param — dry-run preview and guarded execute."""
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
            suggested_fix="Run find or scan to locate the correct block path.",
        )

    # 1. Validate parameter exists and read current value
    try:
        current_value = str(matlab_transport.get_param(eng, target, param)["value"])
    except Exception:
        return make_error(
            "param_not_found",
            f"Parameter '{param}' not found on block '{target}'.",
            details={"target": target, "param": param},
            suggested_fix="Run inspect --param All to list available parameters.",
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


def _execute_multi(eng, args):
    """Multi-param set_param — atomic update of multiple parameters."""
    target = args["target"]
    params = args["params"]
    dry_run = args.get("dry_run", True)

    # 0. Validate target block exists
    try:
        matlab_transport.get_param(eng, target, "Handle")
    except Exception:
        return make_error(
            "block_not_found",
            f"Block '{target}' not found in the model.",
            details={"target": target},
            suggested_fix="Run find or scan to locate the correct block path.",
        )

    # 1. Read all current values
    current_values = {}
    for param_name in params:
        try:
            current_values[param_name] = str(
                matlab_transport.get_param(eng, target, param_name)["value"]
            )
        except Exception:
            return make_error(
                "param_not_found",
                f"Parameter '{param_name}' not found on block '{target}'.",
                details={"target": target, "param": param_name},
                suggested_fix="Run inspect --param All to list available parameters.",
            )

    rollback = {
        "action": "set_param",
        "target": target,
        "params": dict(current_values),
        "dry_run": False,
    }
    apply_payload = {
        "action": "set_param",
        "target": target,
        "params": {k: str(v) for k, v in params.items()},
        "dry_run": False,
        "expected_current_values": dict(current_values),
    }
    if args.get("session") is not None:
        rollback["session"] = args["session"]
        apply_payload["session"] = args["session"]

    # 2. Dry-run: return diff, do NOT write
    if dry_run:
        changes = [
            {"param": k, "current_value": current_values[k], "proposed_value": str(v)}
            for k, v in params.items()
        ]
        return {
            "action": "set_param",
            "dry_run": True,
            "write_state": "not_attempted",
            "target": target,
            "changes": changes,
            "apply_payload": apply_payload,
            "rollback": rollback,
        }

    # 3. Precondition check
    expected_current_values = args.get("expected_current_values")
    if expected_current_values is not None:
        for param_name, expected_val in expected_current_values.items():
            observed_val = current_values.get(param_name)
            if observed_val != expected_val:
                return make_error(
                    "precondition_failed",
                    "Preview is stale; current value changed before execute.",
                    details={
                        "target": target,
                        "param": param_name,
                        "expected_current_value": expected_val,
                        "observed_current_value": observed_val,
                        "write_state": "not_attempted",
                        "safe_to_retry": True,
                        "recommended_recovery": "rerun_dry_run",
                    },
                    suggested_fix="Rerun dry-run to capture the latest values before executing.",
                )

    # 4. Atomic write
    write_state = "not_attempted"
    try:
        write_state = "attempted"
        matlab_transport.set_param_multi(eng, target, params)
    except Exception as exc:
        return make_error(
            "set_param_failed",
            f"Failed to set parameters on '{target}'.",
            details={
                "target": target,
                "params": {k: str(v) for k, v in params.items()},
                "write_state": write_state,
                "rollback": rollback,
                "safe_to_retry": False,
                "recommended_recovery": "rollback",
                "cause": str(exc),
            },
            suggested_fix="Inspect the current values and use rollback if the model may have changed.",
        )

    # 5. Read-back verification
    for param_name, expected_val in params.items():
        try:
            observed = str(
                matlab_transport.get_param(eng, target, param_name)["value"]
            )
        except Exception:
            return make_error(
                "verification_failed",
                f"Write could not be verified for parameter '{param_name}' on '{target}'.",
                details={
                    "target": target,
                    "param": param_name,
                    "write_state": "verification_failed",
                    "rollback": rollback,
                    "safe_to_retry": False,
                    "recommended_recovery": "rollback",
                },
                suggested_fix="Inspect the observed values and replay rollback if needed.",
            )
        if observed != str(expected_val):
            return make_error(
                "verification_failed",
                f"Write could not be verified for parameter '{param_name}' on '{target}'.",
                details={
                    "target": target,
                    "param": param_name,
                    "value": str(expected_val),
                    "write_state": "verification_failed",
                    "rollback": rollback,
                    "observed": observed,
                    "safe_to_retry": False,
                    "recommended_recovery": "rollback",
                },
                suggested_fix="Inspect the observed value and replay rollback if you need to restore the prior state.",
            )

    changes = [
        {"param": k, "previous_value": current_values[k], "new_value": str(v)}
        for k, v in params.items()
    ]
    return {
        "action": "set_param",
        "dry_run": False,
        "write_state": "verified",
        "target": target,
        "changes": changes,
        "verified": True,
        "rollback": rollback,
    }
