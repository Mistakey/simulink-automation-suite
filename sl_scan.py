from sl_common import as_list


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


def inspect_block(eng, block_path, param_name, model_name=None):
    resolved_target = resolve_inspect_target_path(eng, block_path, model_name)
    if "error" in resolved_target:
        return resolved_target

    target_path = resolved_target["target"]

    try:
        eng.get_param(target_path, "Handle")
    except Exception as exc:
        return {"error": f"Block not found '{target_path}': {exc}"}

    try:
        if param_name != "All":
            value = eng.get_param(target_path, param_name)
            return {"target": target_path, "param": param_name, "value": value}

        dialog_params = eng.get_param(target_path, "DialogParameters")
        param_keys = [str(x) for x in as_list(eng.fieldnames(dialog_params))]
        values = {}
        for key in param_keys:
            try:
                values[key] = eng.get_param(target_path, key)
            except Exception as exc:
                values[key] = f"<unavailable: {exc}>"

        return {
            "target": target_path,
            "param": "All",
            "available_params": param_keys,
            "values": values,
        }
    except Exception as exc:
        return {"error": str(exc)}


def list_opened_models(eng):
    try:
        models = get_opened_models(eng)
        return {"models": models}
    except Exception as exc:
        return {"error": str(exc)}
