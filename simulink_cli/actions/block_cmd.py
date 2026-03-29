"""block_add action — add a block to a loaded Simulink model.

Supports both library source paths (e.g. 'simulink/Math Operations/Gain')
and cross-model source paths (e.g. 'RefModel/Controller') for copying
blocks from any loaded model or library.
"""

import difflib

from simulink_cli import matlab_transport
from simulink_cli.errors import make_error
from simulink_cli.validation import validate_matlab_name_field, validate_text_field
from simulink_cli.session import safe_connect_to_session

DESCRIPTION = "Add a block to a loaded Simulink model."

FIELDS = {
    "source": {
        "type": "string",
        "required": False,
        "default": None,
        "description": "Source block path — either a library path (e.g. 'simulink/Math Operations/Gain') or a block in a loaded model (e.g. 'RefModel/Controller'). Library roots are auto-loaded on first use. Some library paths contain literal newlines (e.g. 'simulink/Signal\\nRouting/Mux'); use JSON \\n escape.",
    },
    "destination": {
        "type": "string",
        "required": False,
        "default": None,
        "description": "Full block path in model (e.g. 'my_model/Gain1').",
    },
    "position": {
        "type": "array",
        "items": "number",
        "required": False,
        "default": None,
        "description": "Block position as [left, top, right, bottom] in pixels (e.g. [50, 100, 130, 130]).",
    },
    "auto_layout": {
        "type": "boolean",
        "required": False,
        "default": False,
        "description": "Run Simulink.BlockDiagram.arrangeSystem on the parent model after adding the block.",
    },
    "blocks": {
        "type": "array",
        "required": False,
        "default": None,
        "description": "Batch mode: array of {source, destination, position?} objects. Mutually exclusive with source/destination.",
    },
    "session": {
        "type": "string",
        "required": False,
        "default": None,
        "description": "MATLAB session name override.",
    },
}

ERRORS = [
    "engine_unavailable",
    "no_session",
    "session_not_found",
    "session_required",
    "model_not_found",
    "source_not_found",
    "block_already_exists",
    "verification_failed",
    "runtime_error",
]


def _find_similar_blocks(eng, source, source_root):
    """Best-effort search for similar block paths in the loaded library/model."""
    try:
        result = matlab_transport.find_system(eng, source_root, "SearchDepth", "2")
        candidates = result.get("value", [])
        if not candidates or not isinstance(candidates, list):
            return []
        source_name = source.rsplit("/", 1)[-1].lower()
        scored = []
        for path in candidates:
            if not isinstance(path, str) or path == source_root:
                continue
            block_name = path.rsplit("/", 1)[-1].lower()
            matches = difflib.get_close_matches(source_name, [block_name], n=1, cutoff=0.4)
            if matches:
                scored.append(path)
        return scored[:5]
    except Exception:
        return []


def _validate_single(args):
    """Validate single-block args. Returns error dict or None."""
    err = validate_matlab_name_field("source", args.get("source"))
    if err is not None:
        return err
    err = validate_matlab_name_field("destination", args.get("destination"))
    if err is not None:
        return err
    err = validate_text_field("session", args.get("session"))
    if err is not None:
        return err

    source = args.get("source")
    if source is None or (isinstance(source, str) and not source):
        return make_error(
            "invalid_input",
            "Field 'source' is required.",
            details={"field": "source"},
        )
    destination = args.get("destination")
    if destination is None or (isinstance(destination, str) and not destination):
        return make_error(
            "invalid_input",
            "Field 'destination' is required.",
            details={"field": "destination"},
        )

    position = args.get("position")
    if position is not None:
        if (
            not isinstance(position, list)
            or len(position) != 4
            or not all(isinstance(v, (int, float)) for v in position)
        ):
            return make_error(
                "invalid_input",
                "Field 'position' must be a 4-element numeric array [left, top, right, bottom].",
                details={"field": "position", "value": position},
            )

    return None


def _validate_batch(blocks):
    """Validate batch blocks array. Returns error dict or None."""
    if not isinstance(blocks, list) or len(blocks) == 0:
        return make_error(
            "invalid_input",
            "Field 'blocks' must be a non-empty array.",
            details={"field": "blocks"},
        )
    if len(blocks) > 100:
        return make_error(
            "invalid_input",
            "Field 'blocks' exceeds maximum of 100 items.",
            details={"field": "blocks", "count": len(blocks)},
        )
    for i, item in enumerate(blocks):
        if not isinstance(item, dict):
            return make_error(
                "invalid_input",
                f"Field 'blocks[{i}]' must be an object.",
                details={"field": "blocks", "index": i},
            )
        source = item.get("source")
        if not isinstance(source, str) or not source:
            return make_error(
                "invalid_input",
                f"Field 'blocks[{i}].source' is required and must be a non-empty string.",
                details={"field": "blocks", "index": i},
            )
        destination = item.get("destination")
        if not isinstance(destination, str) or not destination:
            return make_error(
                "invalid_input",
                f"Field 'blocks[{i}].destination' is required and must be a non-empty string.",
                details={"field": "blocks", "index": i},
            )
        position = item.get("position")
        if position is not None:
            if (
                not isinstance(position, list)
                or len(position) != 4
                or not all(isinstance(v, (int, float)) for v in position)
            ):
                return make_error(
                    "invalid_input",
                    f"Field 'blocks[{i}].position' must be a 4-element numeric array [left, top, right, bottom].",
                    details={"field": "blocks", "index": i, "value": position},
                )
    return None


def validate(args):
    """Validate block_add arguments. Returns error dict or None."""
    blocks = args.get("blocks")
    has_single = args.get("source") is not None or args.get("destination") is not None

    if blocks is not None and has_single:
        return make_error(
            "invalid_input",
            "Field 'blocks' is mutually exclusive with 'source' and 'destination'.",
            details={"field": "blocks"},
        )

    if blocks is not None:
        return _validate_batch(blocks)

    return _validate_single(args)


def _add_one_block(eng, source, destination, position, session):
    """Add a single block using a pre-connected engine. Returns result or error dict."""
    model_root = destination.split("/")[0]

    # Precondition 1: parent model is loaded
    try:
        matlab_transport.get_param(eng, model_root, "Handle")
    except Exception:
        return make_error(
            "model_not_found",
            f"Model '{model_root}' is not loaded.",
            details={"model": model_root},
            suggested_fix=f"Open the model first: {{\"action\":\"model_open\",\"path\":\"{model_root}.slx\"}}",
        )

    # Precondition 2: source block exists (auto-load library root on miss)
    try:
        matlab_transport.get_param(eng, source, "Handle")
    except Exception:
        source_root = source.split("/")[0]
        try:
            matlab_transport.load_system(eng, source_root)
            matlab_transport.get_param(eng, source, "Handle")
        except Exception:
            suggestions = _find_similar_blocks(eng, source, source_root)
            details = {"source": source, "auto_load_attempted": source_root}
            if suggestions:
                details["suggestions"] = suggestions
            fix_msg = (
                f"Attempted auto-load of '{source_root}' but source still not found. "
                f"For library blocks, check the library path. "
                f"For cross-model copy, ensure the source model is loaded."
            )
            if suggestions:
                fix_msg += f" Similar paths: {', '.join(suggestions[:3])}"
            return make_error(
                "source_not_found",
                f"Source block '{source}' not found.",
                details=details,
                suggested_fix=fix_msg,
            )

    # Precondition 3: destination does not already exist
    try:
        matlab_transport.get_param(eng, destination, "Handle")
        return make_error(
            "block_already_exists",
            f"Block '{destination}' already exists.",
            details={"destination": destination},
            suggested_fix="Use a different destination name or delete the existing block first.",
        )
    except Exception:
        pass  # Expected — block not found, proceed

    # Execute
    try:
        matlab_transport.add_block(eng, source, destination, position=position)
    except Exception as exc:
        return make_error(
            "runtime_error",
            f"Failed to add block '{destination}'.",
            details={"source": source, "destination": destination, "cause": str(exc)},
            suggested_fix="Check the source library path and destination path for errors.",
        )

    # Verify
    try:
        matlab_transport.get_param(eng, destination, "Handle")
    except Exception:
        return make_error(
            "verification_failed",
            f"Block '{destination}' was added but could not be verified.",
            details={"destination": destination, "write_state": "verification_failed"},
        )

    rollback = {
        "action": "block_delete",
        "destination": destination,
        "available": True,
    }
    if session is not None:
        rollback["session"] = session

    result = {
        "action": "block_add",
        "source": source,
        "destination": destination,
        "verified": True,
        "rollback": rollback,
    }
    if position is not None:
        result["position"] = position
    return result


def _execute_single(args):
    """Execute block_add for a single block."""
    eng, err = safe_connect_to_session(args.get("session"))
    if err is not None:
        return err

    result = _add_one_block(
        eng,
        args["source"],
        args["destination"],
        args.get("position"),
        args.get("session"),
    )

    # Auto-layout (only if add succeeded)
    if "error" not in result and args.get("auto_layout"):
        model_root = args["destination"].split("/")[0]
        try:
            matlab_transport.call_no_output(eng, "Simulink.BlockDiagram.arrangeSystem", model_root)
        except Exception:
            pass  # Best-effort; block was already added successfully

    return result


def _execute_batch(args):
    """Execute block_add for a batch of blocks. Stops on first failure."""
    eng, err = safe_connect_to_session(args.get("session"))
    if err is not None:
        return err

    blocks = args["blocks"]
    model_root = blocks[0]["destination"].split("/")[0]

    # Check first model is loaded
    try:
        matlab_transport.get_param(eng, model_root, "Handle")
    except Exception:
        return {
            "action": "block_add",
            "completed": 0,
            "total": len(blocks),
            "results": [],
            "error": {
                "index": 0,
                "error": "model_not_found",
                "message": f"Model '{model_root}' is not loaded.",
                "item": blocks[0],
            },
        }

    results = []
    for i, item in enumerate(blocks):
        item_model_root = item["destination"].split("/")[0]
        if item_model_root != model_root:
            return {
                "action": "block_add",
                "completed": i,
                "total": len(blocks),
                "results": results,
                "error": {
                    "index": i,
                    "error": "model_not_found",
                    "message": f"Item {i} targets model '{item_model_root}' but batch started with '{model_root}'.",
                    "item": item,
                },
            }

        single_result = _add_one_block(
            eng,
            item["source"],
            item["destination"],
            item.get("position"),
            args.get("session"),
        )

        if "error" in single_result:
            return {
                "action": "block_add",
                "completed": i,
                "total": len(blocks),
                "results": results,
                "error": {
                    "index": i,
                    "error": single_result["error"],
                    "message": single_result.get("message", ""),
                    "item": item,
                },
            }

        entry = {
            "source": item["source"],
            "destination": item["destination"],
            "verified": True,
        }
        if item.get("position") is not None:
            entry["position"] = item["position"]
        results.append(entry)

    # Auto-layout after all succeed
    if args.get("auto_layout"):
        try:
            matlab_transport.call_no_output(eng, "Simulink.BlockDiagram.arrangeSystem", model_root)
        except Exception:
            pass  # Best-effort

    return {
        "action": "block_add",
        "completed": len(blocks),
        "total": len(blocks),
        "results": results,
    }


def execute(args):
    """Execute block_add: add a block or batch of blocks."""
    if args.get("blocks") is not None:
        return _execute_batch(args)
    return _execute_single(args)
