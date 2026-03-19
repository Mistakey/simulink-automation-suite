"""Session command — manage active MATLAB shared session selection."""

from simulink_cli.errors import make_error
from simulink_cli.validation import validate_text_field
from simulink_cli.session import (
    command_session_clear,
    command_session_current,
    command_session_list,
    command_session_use,
)

DESCRIPTION = "Manage active MATLAB shared session selection."

_SESSION_ACTIONS = {"list", "use", "current", "clear"}

FIELDS = {
    "session_action": {
        "type": "string",
        "required": True,
        "default": None,
        "enum": ["list", "use", "current", "clear"],
        "description": "Session management operation.",
        "positional": True,
    },
    "name": {
        "type": "string",
        "required": False,
        "default": None,
        "description": "Session name, required when session_action=use.",
        "positional_optional": True,
    },
}

ERRORS = [
    "engine_unavailable",
    "no_session",
    "session_not_found",
    "session_required",
    "state_write_failed",
    "state_clear_failed",
]


def validate(args):
    """Validate session command arguments. Returns error dict or None."""
    sa = args.get("session_action")
    if not isinstance(sa, str) or sa not in _SESSION_ACTIONS:
        return make_error(
            "invalid_input",
            f"session_action must be one of {sorted(_SESSION_ACTIONS)}.",
            details={"field": "session_action"},
        )

    if sa == "use":
        name = args.get("name")
        if not name:
            return make_error(
                "invalid_input",
                "Field 'name' is required when session_action=use.",
                details={"field": "name"},
            )
        result = validate_text_field("name", name)
        if result:
            return result
    elif args.get("name") is not None:
        return make_error(
            "unknown_parameter",
            "Field 'name' is only supported when session_action=use.",
            details={"field": "name"},
        )

    return None


def execute(args):
    """Execute session management command."""
    sa = args["session_action"]
    if sa == "list":
        return command_session_list()
    if sa == "use":
        return command_session_use(args["name"])
    if sa == "current":
        return command_session_current()
    if sa == "clear":
        return command_session_clear()
    return make_error(
        "invalid_input",
        f"Unsupported session_action '{sa}'.",
    )
