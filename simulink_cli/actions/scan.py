"""Scan action — read model or subsystem topology."""

from simulink_cli.errors import make_error
from simulink_cli.json_io import as_list
from simulink_cli.validation import validate_text_field
from simulink_cli.model_helpers import resolve_scan_root_path
from simulink_cli.session import safe_connect_to_session

DESCRIPTION = "Read model or subsystem topology with optional hierarchy view."

FIELDS = {
    "model": {
        "type": "string",
        "required": False,
        "default": None,
        "description": "Optional specific model name from list_opened output.",
    },
    "subsystem": {
        "type": "string",
        "required": False,
        "default": None,
        "description": "Optional subsystem path under model.",
    },
    "recursive": {
        "type": "boolean",
        "required": False,
        "default": False,
        "description": "Recursively scan all nested blocks under scan root.",
    },
    "hierarchy": {
        "type": "boolean",
        "required": False,
        "default": False,
        "description": "Include hierarchy tree in output (implies recursive).",
    },
    "session": {
        "type": "string",
        "required": False,
        "default": None,
        "description": "Session override for this command.",
    },
    "max_blocks": {
        "type": "integer",
        "required": False,
        "default": None,
        "description": "Limit number of block entries returned.",
    },
    "fields": {
        "type": "array",
        "items": "string",
        "required": False,
        "default": None,
        "description": "Projected block fields to include.",
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


def _build_hierarchy_tree(scan_root, blocks):
    """Build a nested tree from a flat list of blocks."""
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


def validate(args):
    """Validate scan arguments. Returns error dict or None."""
    for field_name in ("model", "subsystem", "session"):
        err = validate_text_field(field_name, args.get(field_name))
        if err is not None:
            return err

    max_blocks = args.get("max_blocks")
    if max_blocks is not None and (not isinstance(max_blocks, int) or max_blocks <= 0):
        return make_error(
            "invalid_input",
            "Field 'max_blocks' must be a positive integer.",
            details={"field": "max_blocks", "value": max_blocks},
        )

    return None


def execute(args):
    """Execute scan action against a live MATLAB session."""
    eng, err = safe_connect_to_session(args.get("session"))
    if err is not None:
        return err

    try:
        resolved = resolve_scan_root_path(
            eng, args.get("model"), args.get("subsystem")
        )
        if "error" in resolved:
            return resolved

        target_model = resolved["model"]
        scan_root = resolved["scan_root"]
        recursive = args.get("recursive", False)
        hierarchy = args.get("hierarchy", False)
        use_recursive = recursive or hierarchy
        max_blocks = args.get("max_blocks")
        fields = args.get("fields")

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
            block_list.append(
                {"name": blk, "type": eng.get_param(blk, "BlockType")}
            )

        block_list = sorted(
            block_list, key=lambda item: str(item.get("name", ""))
        )
        total_count = len(block_list)

        truncated = False
        if (
            isinstance(max_blocks, int)
            and max_blocks >= 0
            and total_count > max_blocks
        ):
            block_list = block_list[:max_blocks]
            truncated = True

        output = {
            "model": target_model,
            "scan_root": scan_root,
            "recursive": use_recursive,
            "total_count": total_count,
            "truncated": truncated,
        }
        if hierarchy:
            output["hierarchy"] = _build_hierarchy_tree(scan_root, block_list)

        # Field projection AFTER hierarchy tree (which needs "type")
        if isinstance(fields, list) and fields:
            block_list = [
                {key: value for key, value in item.items() if key in fields}
                for item in block_list
            ]

        output["blocks"] = block_list

        return output
    except Exception as exc:
        return make_error(
            "runtime_error",
            "Failed to scan model structure.",
            details={"cause": str(exc)},
        )
