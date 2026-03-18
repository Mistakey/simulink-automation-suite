from simulink_cli.errors import make_error
from simulink_cli.json_io import as_list
from simulink_cli.validation import validate_text_field
from simulink_cli.session import connect_to_session

FIELDS = {
    "session": {
        "type": "string",
        "required": False,
        "default": None,
        "description": "Session override for this command.",
    },
}

ERRORS = ["runtime_error"]

DESCRIPTION = "List currently opened Simulink models."


def _get_opened_models(eng):
    return sorted([str(x) for x in as_list(eng.find_system("Type", "block_diagram"))])


def validate(args):
    err = validate_text_field("session", args.get("session"))
    if err:
        return err
    return None


def execute(args):
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
        models = _get_opened_models(eng)
        return {"models": models}
    except Exception as exc:
        return make_error(
            "runtime_error",
            "Failed to list opened models.",
            details={"cause": str(exc)},
        )
