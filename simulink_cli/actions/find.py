"""Find action — search for blocks by name pattern and/or block type."""

import re

from simulink_cli.errors import make_error
from simulink_cli.json_io import as_list
from simulink_cli.validation import validate_text_field
from simulink_cli.model_helpers import resolve_scan_root_path
from simulink_cli.session import safe_connect_to_session

DESCRIPTION = "Search for blocks by name pattern and/or block type."

FIELDS = {
    "model": {
        "type": "string",
        "required": False,
        "default": None,
        "description": "Target model (same resolution as scan).",
    },
    "subsystem": {
        "type": "string",
        "required": False,
        "default": None,
        "description": "Narrow search scope to a subsystem.",
    },
    "name": {
        "type": "string",
        "required": False,
        "default": None,
        "description": "Name substring match (case-insensitive).",
    },
    "block_type": {
        "type": "string",
        "required": False,
        "default": None,
        "description": "BlockType exact match (e.g., SubSystem, Gain).",
    },
    "session": {
        "type": "string",
        "required": False,
        "default": None,
        "description": "Session override for this command.",
    },
    "max_results": {
        "type": "integer",
        "required": False,
        "default": 200,
        "description": "Limit number of results returned.",
    },
    "fields": {
        "type": "array",
        "items": "string",
        "required": False,
        "default": None,
        "description": "Projected result fields to include.",
    },
}

ERRORS = [
    "engine_unavailable",
    "no_session",
    "session_not_found",
    "session_required",
    "model_required",
    "model_not_found",
    "subsystem_not_found",
    "invalid_subsystem_type",
    "runtime_error",
]


def validate(args):
    """Validate find arguments. Returns error dict or None."""
    for field_name in ("model", "subsystem", "name", "block_type", "session"):
        err = validate_text_field(field_name, args.get(field_name))
        if err is not None:
            return err

    name = args.get("name")
    block_type = args.get("block_type")
    if not name and not block_type:
        return make_error(
            "invalid_input",
            "At least one of 'name' or 'block_type' must be provided.",
            details={"field": "name/block_type"},
            suggested_fix="Provide at least one of name or block_type.",
        )

    max_results = args.get("max_results")
    if max_results is not None and (
        not isinstance(max_results, int) or max_results <= 0
    ):
        return make_error(
            "invalid_input",
            "Field 'max_results' must be a positive integer.",
            details={"field": "max_results", "value": max_results},
        )

    return None


def execute(args):
    """Execute find action against a live MATLAB session."""
    eng, err = safe_connect_to_session(args.get("session"))
    if err is not None:
        return err

    model_name = args.get("model")
    subsystem = args.get("subsystem")
    name = args.get("name")
    block_type = args.get("block_type")
    max_results = args.get("max_results", 200)
    fields = args.get("fields")

    resolved = resolve_scan_root_path(eng, model_name, subsystem)
    if "error" in resolved:
        return resolved

    target_model = resolved["model"]
    scan_root = resolved["scan_root"]

    try:
        search_args = [scan_root]
        if name and block_type:
            safe_name = re.escape(name)
            search_args.extend(
                [
                    "RegExp",
                    "on",
                    "Name",
                    f"(?i).*{safe_name}.*",
                    "BlockType",
                    block_type,
                ]
            )
        elif name:
            safe_name = re.escape(name)
            search_args.extend(
                ["RegExp", "on", "Name", f"(?i).*{safe_name}.*"]
            )
        else:
            search_args.extend(["BlockType", block_type])

        raw_results = as_list(eng.find_system(*search_args))

        results = []
        for path in raw_results:
            path = str(path)
            if path == scan_root:
                continue
            block_name = path.rsplit("/", 1)[-1] if "/" in path else path
            parent = path.rsplit("/", 1)[0] if "/" in path else ""
            try:
                btype = str(eng.get_param(path, "BlockType"))
            except Exception:
                btype = ""
            results.append(
                {
                    "path": path,
                    "name": block_name,
                    "type": btype,
                    "parent": parent,
                }
            )

        results = sorted(results, key=lambda item: item.get("path", ""))
        total_results = len(results)

        truncated = False
        if (
            isinstance(max_results, int)
            and max_results >= 0
            and total_results > max_results
        ):
            results = results[:max_results]
            truncated = True

        if isinstance(fields, list) and fields:
            results = [
                {key: value for key, value in item.items() if key in fields}
                for item in results
            ]

        return {
            "model": target_model,
            "scan_root": scan_root,
            "query": {"name": name, "block_type": block_type},
            "results": results,
            "total_results": total_results,
            "truncated": truncated,
        }
    except Exception as exc:
        return make_error(
            "runtime_error",
            "Failed to search blocks.",
            details={"cause": str(exc)},
        )
