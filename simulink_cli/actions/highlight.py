from simulink_cli.errors import make_error
from simulink_cli.validation import validate_text_field
from simulink_cli.session import connect_to_session

FIELDS = {
    "target": {
        "type": "string",
        "required": True,
        "default": None,
        "description": "Block path to highlight.",
    },
    "session": {
        "type": "string",
        "required": False,
        "default": None,
        "description": "Session override for this command.",
    },
}

ERRORS = ["block_not_found", "runtime_error"]

DESCRIPTION = "Highlight a target block in Simulink UI."


def validate(args):
    target = args.get("target")
    if target is None or (isinstance(target, str) and not target):
        return make_error(
            "invalid_input",
            "Field 'target' is required.",
            details={"field": "target"},
        )
    err = validate_text_field("target", target)
    if err:
        return err
    err = validate_text_field("session", args.get("session"))
    if err:
        return err
    return None


def execute(args):
    target = args["target"]
    session = args.get("session")

    try:
        eng = connect_to_session(session)
    except RuntimeError as exc:
        return make_error(
            "runtime_error",
            f"Failed to connect to MATLAB session: {exc}",
            details={"cause": str(exc)},
        )

    try:
        eng.get_param(target, "Handle")
    except Exception as exc:
        return make_error(
            "block_not_found",
            f"Block not found '{target}'.",
            details={"target": target, "cause": str(exc)},
            suggested_fix="Run scan to discover valid block paths, then retry with --target.",
        )

    try:
        eng.hilite_system(target, "find", nargout=0)
        return {"status": "success", "highlighted": target}
    except Exception as exc:
        return make_error(
            "runtime_error",
            "Failed to highlight block.",
            details={"target": target, "cause": str(exc)},
        )
