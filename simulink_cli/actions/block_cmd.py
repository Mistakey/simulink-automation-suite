"""block_add action — add a block to a loaded Simulink model."""

from simulink_cli import matlab_transport
from simulink_cli.errors import make_error
from simulink_cli.validation import validate_matlab_name_field, validate_text_field
from simulink_cli.session import safe_connect_to_session

DESCRIPTION = "Add a block to a loaded Simulink model."

FIELDS = {
    "source": {
        "type": "string",
        "required": True,
        "default": None,
        "description": "Library source path (e.g. 'simulink/Math Operations/Gain'). Some library categories contain literal newlines in the path (e.g. 'simulink/Signal\\nRouting/Mux'); use JSON \\n escape. The library root is auto-loaded on first use.",
    },
    "destination": {
        "type": "string",
        "required": True,
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


def validate(args):
    """Validate block_add arguments. Returns error dict or None."""
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


def execute(args):
    """Execute block_add: add a library block to a loaded model."""
    eng, err = safe_connect_to_session(args.get("session"))
    if err is not None:
        return err

    source = args["source"]
    destination = args["destination"]
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

    # Precondition 2: source library block exists (auto-load library on miss)
    try:
        matlab_transport.get_param(eng, source, "Handle")
    except Exception:
        library_root = source.split("/")[0]
        try:
            matlab_transport.load_system(eng, library_root)
            matlab_transport.get_param(eng, source, "Handle")
        except Exception:
            return make_error(
                "source_not_found",
                f"Library source '{source}' not found.",
                details={"source": source, "auto_load_attempted": library_root},
                suggested_fix=(
                    f"Attempted auto-load of '{library_root}' but source still not found. "
                    f"Check the library path. Use find_system to browse available library blocks."
                ),
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
    position = args.get("position")
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

    # Auto-layout
    if args.get("auto_layout"):
        try:
            matlab_transport.call_no_output(eng, "Simulink.BlockDiagram.arrangeSystem", model_root)
        except Exception:
            pass  # Best-effort; block was already added successfully

    rollback = {
        "action": "block_delete",
        "destination": destination,
        "available": True,
    }
    if args.get("session") is not None:
        rollback["session"] = args["session"]

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
