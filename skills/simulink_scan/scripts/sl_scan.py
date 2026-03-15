from skills._shared.json_io import as_list, project_top_level_fields
from skills._shared.errors import make_error


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
            return {
                "error": "model_required",
                "message": "Multiple opened models found. Pass --model to disambiguate.",
                "models": opened_models,
            }
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
    max_blocks=None,
    fields=None,
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

        block_list = sorted(block_list, key=lambda item: str(item.get("name", "")))
        total_count = len(block_list)
        if isinstance(fields, list) and fields:
            projected = []
            for item in block_list:
                projected.append({key: value for key, value in item.items() if key in fields})
            block_list = projected

        truncated = False
        if isinstance(max_blocks, int) and max_blocks >= 0 and total_count > max_blocks:
            block_list = block_list[:max_blocks]
            truncated = True

        output = {
            "model": target_model,
            "scan_root": scan_root,
            "recursive": use_recursive,
            "blocks": block_list,
            "total_count": total_count,
            "truncated": truncated,
        }
        if hierarchy:
            output["hierarchy"] = build_hierarchy_tree(scan_root, block_list)

        return output
    except Exception as exc:
        return make_error(
            "runtime_error",
            "Failed to scan model structure.",
            details={"cause": str(exc)},
        )


def highlight_block(eng, block_path):
    try:
        eng.get_param(block_path, "Handle")
    except Exception as exc:
        return make_error(
            "block_not_found",
            f"Block not found '{block_path}'.",
            details={"target": block_path, "cause": str(exc)},
            suggested_fix="Run scan to discover valid block paths, then retry with --target.",
        )

    try:
        eng.hilite_system(block_path, "find", nargout=0)
        return {"status": "success", "highlighted": block_path}
    except Exception as exc:
        return make_error(
            "runtime_error",
            "Failed to highlight block.",
            details={"target": block_path, "cause": str(exc)},
        )


def _extract_handles(raw_value):
    handles = []
    pending = as_list(raw_value)
    while pending:
        item = pending.pop(0)
        if item is None:
            continue
        if isinstance(item, (list, tuple)):
            pending[:0] = list(item)
            continue
        if not isinstance(item, (str, bytes)) and hasattr(item, "__iter__"):
            try:
                pending[:0] = list(item)
                continue
            except Exception:
                pass
        try:
            numeric = float(item)
        except Exception:
            continue
        if numeric > 0:
            # MATLAB get_param expects numeric handles as double values.
            handles.append(float(numeric))
    return handles


def _extract_block_port_handles(port_handles, key):
    if isinstance(port_handles, dict):
        return _extract_handles(port_handles.get(key))
    try:
        return _extract_handles(getattr(port_handles, key))
    except Exception:
        return []


def _read_port_info(eng, port_handle):
    return {
        "block": str(eng.get_param(port_handle, "Parent")),
        "port": int(float(eng.get_param(port_handle, "PortNumber"))),
    }


def _read_signal_name(eng, line_handle):
    try:
        return str(eng.get_param(line_handle, "Name") or "")
    except Exception:
        return ""


def _collect_block_edges(eng, block_path):
    edges = []
    port_handles = eng.get_param(block_path, "PortHandles")
    out_ports = _extract_block_port_handles(port_handles, "Outport")
    in_ports = _extract_block_port_handles(port_handles, "Inport")

    for src_port in out_ports:
        line_handles = _extract_handles(eng.get_param(src_port, "Line"))
        if not line_handles:
            continue
        src_info = _read_port_info(eng, src_port)
        for line_handle in line_handles:
            dst_ports = _extract_handles(eng.get_param(line_handle, "DstPortHandle"))
            signal_name = _read_signal_name(eng, line_handle)
            for dst_port in dst_ports:
                dst_info = _read_port_info(eng, dst_port)
                edges.append(
                    {
                        "src_block": src_info["block"],
                        "src_port": src_info["port"],
                        "dst_block": dst_info["block"],
                        "dst_port": dst_info["port"],
                        "signal_name": signal_name,
                        "line_handle": line_handle,
                    }
                )

    for dst_port in in_ports:
        line_handles = _extract_handles(eng.get_param(dst_port, "Line"))
        if not line_handles:
            continue
        dst_info = _read_port_info(eng, dst_port)
        for line_handle in line_handles:
            src_ports = _extract_handles(eng.get_param(line_handle, "SrcPortHandle"))
            signal_name = _read_signal_name(eng, line_handle)
            for src_port in src_ports:
                src_info = _read_port_info(eng, src_port)
                edges.append(
                    {
                        "src_block": src_info["block"],
                        "src_port": src_info["port"],
                        "dst_block": dst_info["block"],
                        "dst_port": dst_info["port"],
                        "signal_name": signal_name,
                        "line_handle": line_handle,
                    }
                )

    return edges


def _edge_key(edge):
    return (
        edge.get("src_block"),
        edge.get("src_port"),
        edge.get("dst_block"),
        edge.get("dst_port"),
        edge.get("signal_name"),
    )


def _project_connection_edges(edges, detail, include_handles):
    projected = []
    for edge in sorted(edges, key=lambda item: _edge_key(item)):
        row = {
            "src_block": edge["src_block"],
            "src_port": edge["src_port"],
            "dst_block": edge["dst_block"],
            "dst_port": edge["dst_port"],
            "signal_name": edge.get("signal_name", ""),
        }
        if detail == "lines" and include_handles:
            row["line_handle"] = edge["line_handle"]
        projected.append(row)
    return projected


def get_block_connections(
    eng,
    block_path,
    model_name=None,
    direction="both",
    depth=1,
    detail="summary",
    include_handles=False,
    max_edges=None,
    fields=None,
):
    resolved_target = resolve_inspect_target_path(eng, block_path, model_name)
    if "error" in resolved_target:
        return resolved_target

    target_path = resolved_target["target"]
    try:
        eng.get_param(target_path, "Handle")
    except Exception as exc:
        return make_error(
            "block_not_found",
            f"Block not found '{target_path}'.",
            details={"target": target_path, "cause": str(exc)},
            suggested_fix="Run scan to discover valid block paths, then retry with --target.",
        )

    if depth is None:
        depth = 1
    if int(depth) <= 0:
        return make_error(
            "invalid_input",
            "Field 'depth' must be greater than zero.",
            details={"field": "depth"},
        )

    allowed_directions = {"upstream", "downstream", "both"}
    if direction not in allowed_directions:
        return make_error(
            "invalid_input",
            "Field 'direction' must be one of upstream,downstream,both.",
            details={"field": "direction"},
        )

    allowed_details = {"summary", "ports", "lines"}
    if detail not in allowed_details:
        return make_error(
            "invalid_input",
            "Field 'detail' must be one of summary,ports,lines.",
            details={"field": "detail"},
        )

    try:
        use_upstream = direction in {"upstream", "both"}
        use_downstream = direction in {"downstream", "both"}

        frontier = {target_path}
        visited = {target_path}
        upstream_blocks = set()
        downstream_blocks = set()
        edges = []
        edge_keys = set()

        for _ in range(int(depth)):
            if not frontier:
                break
            next_frontier = set()
            for node in sorted(frontier):
                node_edges = _collect_block_edges(eng, node)
                for edge in node_edges:
                    if use_downstream and edge["src_block"] == node:
                        edge_key = _edge_key(edge)
                        if edge_key not in edge_keys:
                            edge_keys.add(edge_key)
                            edges.append(edge)
                        dst_block = edge["dst_block"]
                        if dst_block != target_path:
                            downstream_blocks.add(dst_block)
                        if dst_block not in visited:
                            visited.add(dst_block)
                            next_frontier.add(dst_block)
                    if use_upstream and edge["dst_block"] == node:
                        edge_key = _edge_key(edge)
                        if edge_key not in edge_keys:
                            edge_keys.add(edge_key)
                            edges.append(edge)
                        src_block = edge["src_block"]
                        if src_block != target_path:
                            upstream_blocks.add(src_block)
                        if src_block not in visited:
                            visited.add(src_block)
                            next_frontier.add(src_block)
            frontier = next_frontier

        output = {
            "target": target_path,
            "direction": direction,
            "depth": int(depth),
            "detail": detail,
            "upstream_blocks": sorted(upstream_blocks),
            "downstream_blocks": sorted(downstream_blocks),
        }
        if detail in {"ports", "lines"}:
            projected_edges = _project_connection_edges(edges, detail, include_handles)
            total_edges = len(projected_edges)
            truncated = False
            if (
                isinstance(max_edges, int)
                and max_edges >= 0
                and total_edges > max_edges
            ):
                projected_edges = projected_edges[:max_edges]
                truncated = True
            output["edges"] = projected_edges
            output["total_edges"] = total_edges
            output["truncated"] = truncated

        return project_top_level_fields(output, fields)
    except Exception as exc:
        return make_error(
            "runtime_error",
            "Failed to read block connections.",
            details={"target": target_path, "cause": str(exc)},
        )


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
    max_params=None,
    fields=None,
):
    resolved_target = resolve_inspect_target_path(eng, block_path, model_name)
    if "error" in resolved_target:
        return resolved_target

    target_path = resolved_target["target"]

    try:
        eng.get_param(target_path, "Handle")
    except Exception as exc:
        return make_error(
            "block_not_found",
            f"Block not found '{target_path}'.",
            details={"target": target_path, "cause": str(exc)},
            suggested_fix="Run scan to discover valid block paths, then retry with --target.",
        )

    try:
        dialog_params = eng.get_param(target_path, "DialogParameters")
        param_keys = sorted(str(x) for x in as_list(eng.fieldnames(dialog_params)))
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
            return project_top_level_fields(output, fields)

        if active_only:
            active_values = {}
            dropped_inactive = []
            for key, value in values.items():
                is_active = bool(parameter_meta.get(key, {}).get("active", True))
                if is_active:
                    active_values[key] = value
                else:
                    dropped_inactive.append(key)

            active_keys = sorted(active_values.keys())
            total_params = len(active_keys)
            truncated = False
            if isinstance(max_params, int) and max_params >= 0 and total_params > max_params:
                clipped_keys = active_keys[:max_params]
                active_values = {key: active_values[key] for key in clipped_keys}
                truncated = True

            output = {
                "target": target_path,
                "param": "All",
                "active_only": True,
                "values": active_values,
                "dropped_inactive": dropped_inactive,
                "total_params": total_params,
                "truncated": truncated,
            }
            warnings = meta_warnings + conflict_warnings
            if warnings:
                output["warnings"] = warnings
            return project_top_level_fields(output, fields)

        total_params = len(param_keys)
        truncated = False
        selected_keys = list(param_keys)
        if isinstance(max_params, int) and max_params >= 0 and total_params > max_params:
            selected_keys = selected_keys[:max_params]
            truncated = True
        clipped_values = {key: values[key] for key in selected_keys if key in values}
        clipped_meta = {
            key: parameter_meta[key] for key in selected_keys if key in parameter_meta
        }
        output = {
            "target": target_path,
            "param": "All",
            "available_params": selected_keys,
            "values": clipped_values,
            "parameter_meta": clipped_meta,
            "total_params": total_params,
            "truncated": truncated,
        }

        if summary:
            active_params = []
            inactive_params = []
            for key in selected_keys:
                if bool(clipped_meta.get(key, {}).get("active", True)):
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
        return project_top_level_fields(output, fields)
    except Exception as exc:
        return make_error(
            "runtime_error",
            "Failed to inspect block parameters.",
            details={"target": target_path, "cause": str(exc)},
        )


def list_opened_models(eng):
    try:
        models = get_opened_models(eng)
        return {"models": models}
    except Exception as exc:
        return make_error(
            "runtime_error",
            "Failed to list opened models.",
            details={"cause": str(exc)},
        )
