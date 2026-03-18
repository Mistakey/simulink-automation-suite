from simulink_cli.json_io import as_list
from simulink_cli.errors import make_error


def get_opened_models(eng):
    models = [str(x) for x in as_list(eng.find_system("Type", "block_diagram"))]
    return sorted(models)


def resolve_scan_root_path(eng, model_name=None, subsystem_path=None):
    opened_models = get_opened_models(eng)
    target_model = model_name

    if model_name:
        if model_name not in opened_models:
            return make_error(
                "model_not_found",
                f"Model '{model_name}' is not opened in the current MATLAB session.",
                details={"model": model_name, "models": opened_models},
                suggested_fix="Run list_opened and pass a model from the returned list.",
            )
    else:
        if len(opened_models) > 1:
            return make_error(
                "model_required",
                "Multiple opened models found. Pass --model to disambiguate.",
                details={"models": opened_models},
                suggested_fix="Pass --model with one of the listed model names.",
            )
        if len(opened_models) == 1:
            target_model = opened_models[0]
        else:
            target_model = eng.bdroot()

    if not target_model:
        return make_error(
            "model_not_found",
            "No active model found. Please open a Simulink model.",
            details={"model": model_name, "models": opened_models},
            suggested_fix="Open a Simulink model, then retry with --model if needed.",
        )

    if not subsystem_path:
        return {"model": target_model, "scan_root": target_model}

    if subsystem_path == target_model or subsystem_path.startswith(f"{target_model}/"):
        full_path = subsystem_path
    else:
        full_path = f"{target_model}/{subsystem_path}"

    try:
        eng.get_param(full_path, "Handle")
    except Exception as exc:
        return make_error(
            "subsystem_not_found",
            f"Subsystem not found '{full_path}'.",
            details={"model": target_model, "path": full_path, "cause": str(exc)},
            suggested_fix="Run a shallow scan on the model root and pick an existing subsystem path.",
        )

    if full_path != target_model:
        try:
            if eng.get_param(full_path, "BlockType") != "SubSystem":
                return make_error(
                    "invalid_subsystem_type",
                    f"Path '{full_path}' is not a SubSystem block.",
                    details={"model": target_model, "path": full_path},
                    suggested_fix="Choose a SubSystem block path or omit --subsystem for model root scan.",
                )
        except Exception as exc:
            return make_error(
                "runtime_error",
                f"Failed to verify subsystem '{full_path}'.",
                details={"path": full_path, "cause": str(exc)},
            )

    return {"model": target_model, "scan_root": full_path}


def resolve_inspect_target_path(eng, block_path, model_name=None):
    if not model_name:
        return {"target": block_path}

    opened_models = get_opened_models(eng)
    if model_name not in opened_models:
        return make_error(
            "model_not_found",
            f"Model '{model_name}' is not opened in the current MATLAB session.",
            details={"model": model_name, "models": opened_models},
            suggested_fix="Run list_opened and pass an opened model name.",
        )

    prefix = f"{model_name}/"
    if block_path == model_name or block_path.startswith(prefix):
        return {"target": block_path}

    return {"target": f"{prefix}{block_path}"}
