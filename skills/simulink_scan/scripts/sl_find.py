import re

from skills._shared.json_io import as_list
from skills._shared.errors import make_error
from .sl_actions import resolve_scan_root_path, get_opened_models


def find_blocks(
    eng,
    model_name=None,
    subsystem=None,
    name=None,
    block_type=None,
    max_results=200,
    fields=None,
):
    if not name and not block_type:
        return make_error(
            "invalid_input",
            "At least one of 'name' or 'block_type' must be provided.",
            details={"field": "name/block_type"},
            suggested_fix="Provide at least one of name or block_type.",
        )

    resolved = resolve_scan_root_path(eng, model_name, subsystem)
    if "error" in resolved:
        return resolved

    target_model = resolved["model"]
    scan_root = resolved["scan_root"]

    try:
        search_args = [scan_root]
        if name and block_type:
            safe_name = re.escape(name)
            search_args.extend(["RegExp", "on", "Name", f"(?i).*{safe_name}.*", "BlockType", block_type])
        elif name:
            safe_name = re.escape(name)
            search_args.extend(["RegExp", "on", "Name", f"(?i).*{safe_name}.*"])
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
            results.append({
                "path": path,
                "name": block_name,
                "type": btype,
                "parent": parent,
            })

        results = sorted(results, key=lambda item: item.get("path", ""))
        total_results = len(results)

        truncated = False
        if isinstance(max_results, int) and max_results >= 0 and total_results > max_results:
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
