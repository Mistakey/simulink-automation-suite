from skills._shared.errors import make_error


def set_param(
    eng,
    target,
    param,
    value,
    dry_run=True,
    model=None,
):
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
            details={"target": target, "param": param, "value": str(value), "cause": str(exc)},
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
