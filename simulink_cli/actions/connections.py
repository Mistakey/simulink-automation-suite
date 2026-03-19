"""Connections action — read upstream/downstream block relationships."""

from simulink_cli.errors import make_error
from simulink_cli.json_io import as_list, project_top_level_fields
from simulink_cli.validation import validate_text_field
from simulink_cli.model_helpers import resolve_inspect_target_path
from simulink_cli.session import safe_connect_to_session

DESCRIPTION = "Read upstream/downstream block relationships from a target block."

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
        "description": "Block path to analyze.",
    },
    "direction": {
        "type": "string",
        "required": False,
        "default": "both",
        "enum": ["upstream", "downstream", "both"],
        "description": "Traversal direction from target block.",
    },
    "depth": {
        "type": "integer",
        "required": False,
        "default": 1,
        "description": "Traversal depth in hops.",
    },
    "detail": {
        "type": "string",
        "required": False,
        "default": "summary",
        "enum": ["summary", "ports", "lines"],
        "description": "Output detail level.",
    },
    "include_handles": {
        "type": "boolean",
        "required": False,
        "default": False,
        "description": "Include line handles in lines detail output.",
    },
    "max_edges": {
        "type": "integer",
        "required": False,
        "default": None,
        "description": "Limit number of connection edges returned.",
    },
    "fields": {
        "type": "array",
        "items": "string",
        "required": False,
        "default": None,
        "description": "Projected top-level response fields to include.",
    },
    "session": {
        "type": "string",
        "required": False,
        "default": None,
        "description": "Session override for this command.",
    },
}

ERRORS = [
    "engine_unavailable",
    "no_session",
    "session_not_found",
    "session_required",
    "model_not_found",
    "block_not_found",
    "runtime_error",
]


# ---------------------------------------------------------------------------
# Internal helpers (ported from sl_connections.py)
# ---------------------------------------------------------------------------


def _extract_handles(raw_value):
    """Flatten nested iterables and extract positive numeric handles."""
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
    """Collect all edges (inport + outport) for a single block."""
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
            dst_ports = _extract_handles(
                eng.get_param(line_handle, "DstPortHandle")
            )
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
            src_ports = _extract_handles(
                eng.get_param(line_handle, "SrcPortHandle")
            )
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


# ---------------------------------------------------------------------------
# Protocol: validate / execute
# ---------------------------------------------------------------------------


def validate(args):
    """Validate connections arguments. Returns error dict or None."""
    for field_name in ("model", "target", "session"):
        err = validate_text_field(field_name, args.get(field_name))
        if err is not None:
            return err

    target = args.get("target")
    if target is None or (isinstance(target, str) and not target):
        return make_error(
            "invalid_input",
            "Field 'target' is required.",
            details={"field": "target"},
        )

    depth = args.get("depth")
    if depth is not None and (not isinstance(depth, int) or depth <= 0):
        return make_error(
            "invalid_input",
            "Field 'depth' must be a positive integer.",
            details={"field": "depth", "value": depth},
        )

    max_edges = args.get("max_edges")
    if max_edges is not None and (not isinstance(max_edges, int) or max_edges <= 0):
        return make_error(
            "invalid_input",
            "Field 'max_edges' must be a positive integer.",
            details={"field": "max_edges", "value": max_edges},
        )

    direction = args.get("direction", "both")
    allowed_directions = {"upstream", "downstream", "both"}
    if direction not in allowed_directions:
        return make_error(
            "invalid_input",
            "Field 'direction' must be one of upstream,downstream,both.",
            details={"field": "direction"},
        )

    detail = args.get("detail", "summary")
    allowed_details = {"summary", "ports", "lines"}
    if detail not in allowed_details:
        return make_error(
            "invalid_input",
            "Field 'detail' must be one of summary,ports,lines.",
            details={"field": "detail"},
        )

    return None


def execute(args):
    """Execute connections action against a live MATLAB session."""
    eng, err = safe_connect_to_session(args.get("session"))
    if err is not None:
        return err

    block_path = args["target"]
    model_name = args.get("model")
    direction = args.get("direction", "both")
    depth = args.get("depth", 1) or 1
    detail = args.get("detail", "summary")
    include_handles = args.get("include_handles", False)
    max_edges = args.get("max_edges")
    fields = args.get("fields")

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
        use_upstream = direction in {"upstream", "both"}
        use_downstream = direction in {"downstream", "both"}

        frontier = {target_path}
        visited = {target_path}
        upstream_blocks = set()
        downstream_blocks = set()
        edges = []
        edge_keys = set()

        for _ in range(depth):
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
            "depth": depth,
            "detail": detail,
            "upstream_blocks": sorted(upstream_blocks),
            "downstream_blocks": sorted(downstream_blocks),
        }
        if detail in {"ports", "lines"}:
            projected_edges = _project_connection_edges(
                edges, detail, include_handles
            )
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
