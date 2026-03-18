from simulink_cli.errors import make_error
from simulink_cli.validation import validate_text_field
from simulink_cli.session import safe_connect_to_session
from simulink_cli.model_helpers import get_opened_models

FIELDS = {
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
    "runtime_error",
]

DESCRIPTION = "List currently opened Simulink models."


def validate(args):
    err = validate_text_field("session", args.get("session"))
    if err:
        return err
    return None


def execute(args):
    eng, err = safe_connect_to_session(args.get("session"))
    if err is not None:
        return err

    try:
        models = get_opened_models(eng)
        return {"models": models}
    except Exception as exc:
        return make_error(
            "runtime_error",
            "Failed to list opened models.",
            details={"cause": str(exc)},
        )
