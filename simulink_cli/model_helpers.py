from simulink_cli import matlab_transport
from simulink_cli.json_io import as_list
from simulink_cli.errors import make_error


def _details_with_warnings(details, warnings):
    if not warnings:
        return details
    enriched = dict(details)
    enriched["warnings"] = list(warnings)
    return enriched


def _get_opened_models_result(eng):
    models_result = matlab_transport.find_system(eng, "Type", "block_diagram")
    warnings = list(models_result["warnings"])
    try:
        models = [str(x) for x in as_list(models_result["value"])]
    except Exception as exc:
        exc.matlab_warnings = warnings
        raise
    return {
        "value": sorted(models),
        "warnings": warnings,
    }


def get_opened_models(eng):
    return _get_opened_models_result(eng)["value"]


def resolve_scan_root_path(eng, model_name=None, subsystem_path=None):
    opened_models_result = _get_opened_models_result(eng)
    opened_models = opened_models_result["value"]
    warnings = list(opened_models_result["warnings"])
    target_model = model_name

    if model_name:
        if model_name not in opened_models:
            return make_error(
                "model_not_found",
                f"Model '{model_name}' is not opened in the current MATLAB session.",
                details=_details_with_warnings(
                    {"model": model_name, "models": opened_models}, warnings
                ),
                suggested_fix="Run list_opened and pass a model from the returned list.",
            )
    else:
        if len(opened_models) > 1:
            return make_error(
                "model_required",
                "Multiple opened models found. Pass --model to disambiguate.",
                details=_details_with_warnings(
                    {"models": opened_models}, warnings
                ),
                suggested_fix="Pass --model with one of the listed model names.",
            )
        if len(opened_models) == 1:
            target_model = opened_models[0]
        else:
            try:
                bdroot_result = matlab_transport.bdroot(eng)
                warnings.extend(bdroot_result["warnings"])
                target_model = bdroot_result["value"]
            except Exception as exc:
                all_warnings = list(warnings)
                all_warnings.extend(getattr(exc, "matlab_warnings", []))
                return make_error(
                    "model_not_found",
                    "No active model found. Please open a Simulink model.",
                    details=_details_with_warnings(
                        {
                            "model": model_name,
                            "models": opened_models,
                            "cause": str(exc),
                        },
                        all_warnings,
                    ),
                    suggested_fix="Open a Simulink model, then retry with --model if needed.",
                )

    if not target_model:
        return make_error(
            "model_not_found",
            "No active model found. Please open a Simulink model.",
            details=_details_with_warnings(
                {"model": model_name, "models": opened_models}, warnings
            ),
            suggested_fix="Open a Simulink model, then retry with --model if needed.",
        )

    if not subsystem_path:
        result = {"model": target_model, "scan_root": target_model}
        if warnings:
            result["warnings"] = warnings
        return result

    if subsystem_path == target_model or subsystem_path.startswith(f"{target_model}/"):
        full_path = subsystem_path
    else:
        full_path = f"{target_model}/{subsystem_path}"

    try:
        handle_result = matlab_transport.get_param(eng, full_path, "Handle")
        warnings.extend(handle_result["warnings"])
    except Exception as exc:
        all_warnings = list(warnings)
        all_warnings.extend(getattr(exc, "matlab_warnings", []))
        return make_error(
            "subsystem_not_found",
            f"Subsystem not found '{full_path}'.",
            details=_details_with_warnings(
                {"model": target_model, "path": full_path, "cause": str(exc)},
                all_warnings,
            ),
            suggested_fix="Run a shallow scan on the model root and pick an existing subsystem path.",
        )

    if full_path != target_model:
        try:
            block_type_result = matlab_transport.get_param(
                eng, full_path, "BlockType"
            )
            warnings.extend(block_type_result["warnings"])
            block_type = block_type_result["value"]
            if block_type != "SubSystem":
                return make_error(
                    "invalid_subsystem_type",
                    f"Path '{full_path}' is not a SubSystem block.",
                    details=_details_with_warnings(
                        {"model": target_model, "path": full_path}, warnings
                    ),
                    suggested_fix="Choose a SubSystem block path or omit --subsystem for model root scan.",
                )
        except Exception as exc:
            all_warnings = list(warnings)
            all_warnings.extend(getattr(exc, "matlab_warnings", []))
            return make_error(
                "runtime_error",
                f"Failed to verify subsystem '{full_path}'.",
                details=_details_with_warnings(
                    {"path": full_path, "cause": str(exc)}, all_warnings
                ),
            )

    result = {"model": target_model, "scan_root": full_path}
    if warnings:
        result["warnings"] = warnings
    return result


def resolve_inspect_target_path(eng, block_path, model_name=None):
    if not model_name:
        return {"target": block_path}

    opened_models_result = _get_opened_models_result(eng)
    opened_models = opened_models_result["value"]
    warnings = list(opened_models_result["warnings"])
    if model_name not in opened_models:
        return make_error(
            "model_not_found",
            f"Model '{model_name}' is not opened in the current MATLAB session.",
            details=_details_with_warnings(
                {"model": model_name, "models": opened_models}, warnings
            ),
            suggested_fix="Run list_opened and pass an opened model name.",
        )

    prefix = f"{model_name}/"
    if block_path == model_name or block_path.startswith(prefix):
        result = {"target": block_path}
        if warnings:
            result["warnings"] = warnings
        return result

    result = {"target": f"{prefix}{block_path}"}
    if warnings:
        result["warnings"] = warnings
    return result
