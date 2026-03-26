"""block_delete action — delete a block from a loaded Simulink model."""

from simulink_cli import matlab_transport
from simulink_cli.errors import make_error
from simulink_cli.validation import validate_matlab_name_field, validate_text_field
from simulink_cli.session import safe_connect_to_session

DESCRIPTION = "Delete a block from a loaded Simulink model."

FIELDS = {
    "destination": {
        "type": "string",
        "required": True,
        "default": None,
        "description": "Full block path in model (e.g. 'my_model/Gain1').",
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
    "block_not_found",
    "verification_failed",
    "runtime_error",
]


def validate(args):
    """Validate block_delete arguments. Returns error dict or None."""
    err = validate_matlab_name_field("destination", args.get("destination"))
    if err is not None:
        return err
    err = validate_text_field("session", args.get("session"))
    if err is not None:
        return err

    destination = args.get("destination")
    if destination is None or (isinstance(destination, str) and not destination):
        return make_error(
            "invalid_input",
            "Field 'destination' is required.",
            details={"field": "destination"},
        )
    return None


def execute(args):
    """Execute block_delete: remove a block from a loaded model."""
    eng, err = safe_connect_to_session(args.get("session"))
    if err is not None:
        return err

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

    # Precondition 2: block exists
    try:
        matlab_transport.get_param(eng, destination, "Handle")
    except Exception:
        return make_error(
            "block_not_found",
            f"Block '{destination}' not found.",
            details={"destination": destination},
            suggested_fix=f"Use scan or find to list blocks in '{model_root}'.",
        )

    # Execute
    try:
        matlab_transport.delete_block(eng, destination)
    except Exception as exc:
        return make_error(
            "runtime_error",
            f"Failed to delete block '{destination}'.",
            details={"destination": destination, "cause": str(exc)},
            suggested_fix="Verify the block path and that the model is not locked.",
        )

    # Verify — reverse check: block must no longer exist
    try:
        matlab_transport.get_param(eng, destination, "Handle")
        # If get_param succeeds, block still exists — verification failed
        return make_error(
            "verification_failed",
            f"Block '{destination}' was targeted for deletion but still exists.",
            details={"destination": destination, "write_state": "verification_failed"},
        )
    except Exception:
        pass  # Expected — block is gone, deletion confirmed

    rollback = {
        "action": "block_add",
        "destination": destination,
        "available": False,
        "note": (
            "block_add requires the original library source; "
            "use MATLAB add_block('<source>', '"
            + destination
            + "') manually to restore"
        ),
    }
    if args.get("session") is not None:
        rollback["session"] = args["session"]

    return {
        "action": "block_delete",
        "destination": destination,
        "verified": True,
        "rollback": rollback,
    }
