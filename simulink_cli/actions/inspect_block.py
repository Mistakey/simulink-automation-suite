from simulink_cli import matlab_transport
from simulink_cli.errors import make_error
from simulink_cli.json_io import as_list, project_top_level_fields
from simulink_cli.validation import validate_matlab_name_field, validate_text_field
from simulink_cli.model_helpers import resolve_inspect_target_path
from simulink_cli.session import safe_connect_to_session


DESCRIPTION = "Read block parameters and effective values."

FIELDS = {
    "model": {
        "type": "string",
        "required": False,
        "default": None,
        "description": "Optional specific model name from list_opened output.",
    },
    "target": {
        "type": "string",
        "required": True,
        "default": None,
        "description": "Block path to inspect.",
    },
    "param": {
        "type": "string",
        "required": False,
        "default": "All",
        "description": "Parameter name to read, or All for dialog parameters.",
    },
    "active_only": {
        "type": "boolean",
        "required": False,
        "default": False,
        "description": "Return only active parameters when param=All.",
    },
    "strict_active": {
        "type": "boolean",
        "required": False,
        "default": False,
        "description": "Fail when requested parameter is inactive.",
    },
    "resolve_effective": {
        "type": "boolean",
        "required": False,
        "default": False,
        "description": "Resolve known effective value for inactive parameter.",
    },
    "summary": {
        "type": "boolean",
        "required": False,
        "default": False,
        "description": "Include compact summary lists when param=All.",
    },
    "session": {
        "type": "string",
        "required": False,
        "default": None,
        "description": "Session override for this command.",
    },
    "max_params": {
        "type": "integer",
        "required": False,
        "default": None,
        "description": "Limit number of parameters returned when param=All.",
    },
    "fields": {
        "type": "array",
        "items": "string",
        "required": False,
        "default": None,
        "description": "Projected top-level response fields to include.",
    },
}

ERRORS = [
    "engine_unavailable",
    "no_session",
    "session_not_found",
    "session_required",
    "model_not_found",
    "block_not_found",
    "param_not_found",
    "inactive_parameter",
    "runtime_error",
]


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


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
        return [
            str(x)
            for x in as_list(matlab_transport.get_param(eng, target_path, param_name)["value"])
        ]
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
            values[key] = matlab_transport.get_param(eng, target_path, key)["value"]
        except Exception as exc:
            values[key] = f"<unavailable: {exc}>"
    return values


# ---------------------------------------------------------------------------
# Core inspect logic
# ---------------------------------------------------------------------------


def _inspect_block(
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
        matlab_transport.get_param(eng, target_path, "Handle")
    except Exception as exc:
        return make_error(
            "block_not_found",
            f"Block not found '{target_path}'.",
            details={"target": target_path, "cause": str(exc)},
            suggested_fix="Run scan to discover valid block paths, then retry with --target.",
        )

    try:
        dialog_params = matlab_transport.get_param(eng, target_path, "DialogParameters")["value"]
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
                    value = matlab_transport.get_param(eng, target_path, param_name)["value"]
                except Exception:
                    return make_error(
                        "param_not_found",
                        f"Parameter '{param_name}' is not available on target block.",
                        details={"target": target_path, "param": param_name},
                        suggested_fix='Run inspect with --param "All" to list available parameters.',
                    )

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
                details = {"target": target_path, "param": param_name}
                if resolution:
                    details["effective_from"] = resolution.get("resolved_path")
                return make_error(
                    "inactive_parameter",
                    "Requested parameter is inactive in current configuration.",
                    details=details,
                    suggested_fix="Retry with --resolve-effective or omit --strict-active.",
                )

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


# ---------------------------------------------------------------------------
# Action protocol: validate / execute
# ---------------------------------------------------------------------------


def validate(args):
    for field_name in ("model", "target"):
        error = validate_matlab_name_field(field_name, args.get(field_name))
        if error is not None:
            return error
    error = validate_text_field("session", args.get("session"))
    if error is not None:
        return error

    if not args.get("target"):
        return make_error(
            "invalid_input",
            "Field 'target' is required.",
            details={"field": "target"},
        )

    max_params = args.get("max_params")
    if max_params is not None and (not isinstance(max_params, int) or max_params <= 0):
        return make_error(
            "invalid_input",
            "Field 'max_params' must be a positive integer.",
            details={"field": "max_params", "value": max_params},
        )

    return None


def execute(args):
    eng, err = safe_connect_to_session(args.get("session"))
    if err is not None:
        return err
    return _inspect_block(
        eng,
        block_path=args.get("target"),
        param_name=args.get("param", "All"),
        model_name=args.get("model"),
        active_only=args.get("active_only", False),
        strict_active=args.get("strict_active", False),
        resolve_effective=args.get("resolve_effective", False),
        summary=args.get("summary", False),
        max_params=args.get("max_params"),
        fields=args.get("fields"),
    )
