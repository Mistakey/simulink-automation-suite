from .sl_common import as_list


def get_opened_models(eng):
    return [str(x) for x in as_list(eng.find_system("Type", "block_diagram"))]


def resolve_scan_root_path(eng, model_name=None, subsystem_path=None):
    target_model = model_name
    if not target_model:
        target_model = eng.bdroot()

    if not target_model:
        return {"error": "No active model found. Please open a Simulink model."}

    if model_name:
        opened_models = get_opened_models(eng)
        if model_name not in opened_models:
            return {
                "error": f"Model '{model_name}' is not opened in the current MATLAB session.",
                "models": opened_models,
            }

    if not subsystem_path:
        return {"model": target_model, "scan_root": target_model}

    if subsystem_path == target_model or subsystem_path.startswith(f"{target_model}/"):
        full_path = subsystem_path
    else:
        full_path = f"{target_model}/{subsystem_path}"

    try:
        eng.get_param(full_path, "Handle")
    except Exception as exc:
        return {
            "error": f"Subsystem not found '{full_path}': {exc}",
            "model": target_model,
        }

    if full_path != target_model:
        try:
            if eng.get_param(full_path, "BlockType") != "SubSystem":
                return {
                    "error": f"Path '{full_path}' is not a SubSystem block.",
                    "model": target_model,
                }
        except Exception as exc:
            return {"error": f"Failed to verify subsystem '{full_path}': {exc}"}

    return {"model": target_model, "scan_root": full_path}


def build_hierarchy_tree(scan_root, blocks):
    root_name = scan_root.split("/")[-1]
    root = {
        "name": root_name,
        "path": scan_root,
        "type": "SubSystem",
        "children": [],
    }
    nodes = {scan_root: root}

    for item in sorted(blocks, key=lambda x: x["name"].count("/")):
        path = item["name"]
        parent_path = path.rsplit("/", 1)[0] if "/" in path else scan_root
        parent = nodes.get(parent_path, root)
        node = {
            "name": path.split("/")[-1],
            "path": path,
            "type": item["type"],
            "children": [],
        }
        nodes[path] = node
        children = parent.get("children")
        if isinstance(children, list):
            children.append(node)

    return root


def get_model_structure(
    eng,
    model_name=None,
    recursive=False,
    subsystem_path=None,
    hierarchy=False,
):
    try:
        resolved = resolve_scan_root_path(eng, model_name, subsystem_path)
        if "error" in resolved:
            return resolved

        target_model = resolved["model"]
        scan_root = resolved["scan_root"]
        use_recursive = recursive or hierarchy
        search_options = ["FollowLinks", "on", "LookUnderMasks", "all"]

        if use_recursive:
            blocks = as_list(
                eng.find_system(scan_root, *search_options, "Type", "block")
            )
        else:
            blocks = as_list(
                eng.find_system(
                    scan_root,
                    *search_options,
                    "SearchDepth",
                    1,
                    "Type",
                    "block",
                )
            )

        block_list = []
        for blk in blocks:
            if blk == scan_root:
                continue
            block_list.append({"name": blk, "type": eng.get_param(blk, "BlockType")})

        output = {
            "model": target_model,
            "scan_root": scan_root,
            "recursive": use_recursive,
            "blocks": block_list,
            "connections": [],
        }
        if hierarchy:
            output["hierarchy"] = build_hierarchy_tree(scan_root, block_list)

        return output
    except Exception as exc:
        return {"error": str(exc)}


def highlight_block(eng, block_path):
    try:
        eng.hilite_system(block_path, "find", nargout=0)
        return {"status": "success", "highlighted": block_path}
    except Exception as exc:
        return {"error": str(exc)}


def resolve_inspect_target_path(eng, block_path, model_name=None):
    if not model_name:
        return {"target": block_path}

    opened_models = get_opened_models(eng)
    if model_name not in opened_models:
        return {
            "error": f"Model '{model_name}' is not opened in the current MATLAB session.",
            "models": opened_models,
        }

    prefix = f"{model_name}/"
    if block_path == model_name or block_path.startswith(prefix):
        return {"target": block_path}

    return {"target": f"{prefix}{block_path}"}


def _to_on_off_bool(value):
    if value is None:
        return None
    text = str(value).strip().lower()
    if text == "on":
        return True
    if text == "off":
        return False
    return None


def _safe_get_param_list(eng, target_path, param_name):
    try:
        return [str(x) for x in as_list(eng.get_param(target_path, param_name))]
    except Exception:
        return []


def build_parameter_meta(param_keys, mask_names, mask_visibilities, mask_enables):
    parameter_meta = {
        key: {
            "visible": True,
            "enabled": True,
            "active": True,
            "source": "dialog",
        }
        for key in param_keys
    }

    warnings = []
    if not mask_names:
        return parameter_meta, warnings

    max_len = max(len(mask_names), len(mask_visibilities), len(mask_enables))
    if len({len(mask_names), len(mask_visibilities), len(mask_enables)}) > 1:
        warnings.append(
            "Mask metadata length mismatch detected; visibility/enabled states were inferred where missing."
        )

    for idx in range(max_len):
        if idx >= len(mask_names):
            continue
        name = str(mask_names[idx])
        visible = (
            _to_on_off_bool(mask_visibilities[idx])
            if idx < len(mask_visibilities)
            else None
        )
        enabled = (
            _to_on_off_bool(mask_enables[idx]) if idx < len(mask_enables) else None
        )

        visible_value = True if visible is None else visible
        enabled_value = True if enabled is None else enabled
        active_value = visible_value and enabled_value

        parameter_meta[name] = {
            "visible": visible_value,
            "enabled": enabled_value,
            "active": active_value,
            "source": "mask",
        }

    return parameter_meta, warnings


def build_conflict_warnings(values, parameter_meta):
    warnings = []
    if "Mechanical" in values and "PolePairs" in values:
        mechanical_active = bool(
            parameter_meta.get("Mechanical", {}).get("active", True)
        )
        polepairs_active = bool(parameter_meta.get("PolePairs", {}).get("active", True))
        if mechanical_active != polepairs_active:
            if mechanical_active:
                warnings.append(
                    "'PolePairs' exists but is inactive in current mask configuration; effective pole-pair value comes from 'Mechanical' vector index 3."
                )
            else:
                warnings.append(
                    "'Mechanical' exists but is inactive in current mask configuration; effective pole-pair value comes from 'PolePairs'."
                )
    return warnings


def _extract_mechanical_polepairs_resolution(values, parameter_meta):
    if "Mechanical" not in values or "PolePairs" not in values:
        return None

    mechanical_active = bool(parameter_meta.get("Mechanical", {}).get("active", True))
    polepairs_active = bool(parameter_meta.get("PolePairs", {}).get("active", True))
    if mechanical_active == polepairs_active:
        return None

    if mechanical_active:
        mechanical_value = str(values.get("Mechanical", "")).strip()
        inner = mechanical_value.strip("[]")
        parts = [part for part in inner.replace(",", " ").split() if part]
        resolved_value = parts[2] if len(parts) >= 3 else None
        return {
            "requested_param": "PolePairs",
            "resolved_param": "Mechanical",
            "resolved_path": "Mechanical[3]",
            "resolved_value": resolved_value,
            "effective_note": "Parameter is inactive in current mask configuration.",
            "warning": "'PolePairs' is inactive; effective pole pairs come from Mechanical vector index 3.",
        }

    return {
        "requested_param": "Mechanical",
        "resolved_param": "PolePairs",
        "resolved_path": "PolePairs",
        "resolved_value": values.get("PolePairs"),
        "effective_note": "Parameter is inactive in current mask configuration.",
        "warning": "'Mechanical' is inactive; effective pole pairs come from 'PolePairs'.",
    }


def build_effective_resolution_map(values, parameter_meta):
    resolution_map = {}

    pmsm_resolution = _extract_mechanical_polepairs_resolution(values, parameter_meta)
    if pmsm_resolution:
        requested = pmsm_resolution["requested_param"]
        resolution_map[requested] = pmsm_resolution

    return resolution_map


def _collect_dialog_values(eng, target_path, param_keys):
    values = {}
    for key in param_keys:
        try:
            values[key] = eng.get_param(target_path, key)
        except Exception as exc:
            values[key] = f"<unavailable: {exc}>"
    return values


def inspect_block(
    eng,
    block_path,
    param_name,
    model_name=None,
    active_only=False,
    strict_active=False,
    resolve_effective=False,
    summary=False,
):
    resolved_target = resolve_inspect_target_path(eng, block_path, model_name)
    if "error" in resolved_target:
        return resolved_target

    target_path = resolved_target["target"]

    try:
        eng.get_param(target_path, "Handle")
    except Exception as exc:
        return {"error": f"Block not found '{target_path}': {exc}"}

    try:
        dialog_params = eng.get_param(target_path, "DialogParameters")
        param_keys = [str(x) for x in as_list(eng.fieldnames(dialog_params))]
        values = _collect_dialog_values(eng, target_path, param_keys)

        mask_names = _safe_get_param_list(eng, target_path, "MaskNames")
        mask_visibilities = _safe_get_param_list(eng, target_path, "MaskVisibilities")
        mask_enables = _safe_get_param_list(eng, target_path, "MaskEnables")
        parameter_meta, meta_warnings = build_parameter_meta(
            param_keys, mask_names, mask_visibilities, mask_enables
        )
        conflict_warnings = build_conflict_warnings(values, parameter_meta)
        resolution_map = build_effective_resolution_map(values, parameter_meta)

        if param_name != "All":
            if param_name in values:
                value = values[param_name]
            else:
                try:
                    value = eng.get_param(target_path, param_name)
                except Exception:
                    return {
                        "error": "unknown_parameter",
                        "param": param_name,
                        "message": f"Parameter '{param_name}' is not available on target block.",
                    }

            meta = parameter_meta.get(
                param_name,
                {
                    "visible": True,
                    "enabled": True,
                    "active": True,
                    "source": "instance",
                },
            )
            is_active = bool(meta.get("active", True))
            resolution = resolution_map.get(param_name)

            if strict_active and not is_active:
                error_output = {
                    "error": "inactive_parameter",
                    "param": param_name,
                    "message": "Requested parameter is inactive in current configuration.",
                }
                if resolution:
                    error_output["effective_from"] = resolution.get("resolved_path")
                return error_output

            output = {
                "target": target_path,
                "param": param_name,
                "value": value,
                "meta": meta,
            }

            warnings = list(meta_warnings)
            if not is_active:
                output["effective_note"] = (
                    "Parameter is inactive in current mask configuration."
                )
                if resolution:
                    output["effective_from"] = resolution.get("resolved_path")
                else:
                    warnings.append(
                        f"'{param_name}' is inactive in current mask configuration and has no resolver mapping."
                    )

            if resolve_effective and not is_active:
                if resolution:
                    output.update(
                        {
                            "requested_param": param_name,
                            "resolved_param": resolution.get("resolved_param"),
                            "resolved_path": resolution.get("resolved_path"),
                            "resolved_value": resolution.get("resolved_value"),
                        }
                    )
                else:
                    warnings.append(
                        f"Unable to resolve effective value for inactive parameter '{param_name}'."
                    )

            for item in conflict_warnings:
                if item not in warnings:
                    warnings.append(item)
            warnings = [item for item in warnings if item]
            if warnings:
                output["warnings"] = warnings
            return output

        if active_only:
            active_values = {}
            dropped_inactive = []
            for key, value in values.items():
                is_active = bool(parameter_meta.get(key, {}).get("active", True))
                if is_active:
                    active_values[key] = value
                else:
                    dropped_inactive.append(key)

            output = {
                "target": target_path,
                "param": "All",
                "active_only": True,
                "values": active_values,
                "dropped_inactive": dropped_inactive,
            }
            warnings = meta_warnings + conflict_warnings
            if warnings:
                output["warnings"] = warnings
            return output

        output = {
            "target": target_path,
            "param": "All",
            "available_params": param_keys,
            "values": values,
            "parameter_meta": parameter_meta,
        }

        if summary:
            active_params = []
            inactive_params = []
            for key in param_keys:
                if bool(parameter_meta.get(key, {}).get("active", True)):
                    active_params.append(key)
                else:
                    inactive_params.append(key)

            effective_overrides = []
            for requested, resolution in resolution_map.items():
                if requested in inactive_params:
                    effective_overrides.append(
                        {
                            "requested_param": requested,
                            "resolved_param": resolution.get("resolved_param"),
                            "resolved_path": resolution.get("resolved_path"),
                        }
                    )

            output["active_params"] = active_params
            output["inactive_params"] = inactive_params
            output["effective_overrides"] = effective_overrides

        warnings = meta_warnings + conflict_warnings
        if warnings:
            output["warnings"] = warnings
        return output
    except Exception as exc:
        return {"error": str(exc)}


def list_opened_models(eng):
    try:
        models = get_opened_models(eng)
        return {"models": models}
    except Exception as exc:
        return {"error": str(exc)}
