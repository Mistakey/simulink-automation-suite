from skills._shared.json_io import as_list, project_top_level_fields
from skills._shared.errors import make_error
from .sl_actions import resolve_inspect_target_path


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
