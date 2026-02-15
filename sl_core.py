from sl_common import JsonArgumentParser, emit_json
from sl_scan import (
    get_model_structure,
    highlight_block,
    inspect_block,
    list_opened_models,
)
from sl_session import (
    command_session_clear,
    command_session_current,
    command_session_list,
    command_session_use,
    connect_to_session,
)


def build_parser():
    parser = JsonArgumentParser(description="Simulink AI Bridge Core")
    subparsers = parser.add_subparsers(dest="action", required=True)

    scan_parser = subparsers.add_parser("scan", help="Read active model topology")
    scan_parser.add_argument(
        "--model", help="Optional specific model name from list_opened output"
    )
    scan_parser.add_argument(
        "--subsystem",
        help="Optional subsystem path under the model to scan",
    )
    scan_parser.add_argument(
        "--recursive",
        action="store_true",
        help="Recursively scan all nested blocks under the scan root",
    )
    scan_parser.add_argument(
        "--hierarchy",
        action="store_true",
        help="Include hierarchy tree in scan output (implies recursive)",
    )
    scan_parser.add_argument("--session", help="Session override for this command")

    highlight_parser = subparsers.add_parser("highlight", help="Highlight a block")
    highlight_parser.add_argument(
        "--target", required=True, help="Block path to highlight"
    )
    highlight_parser.add_argument("--session", help="Session override for this command")

    inspect_parser = subparsers.add_parser("inspect", help="Inspect block parameters")
    inspect_parser.add_argument(
        "--model", help="Optional specific model name from list_opened output"
    )
    inspect_parser.add_argument("--target", required=True, help="Block path to inspect")
    inspect_parser.add_argument(
        "--param",
        default="All",
        help="Parameter name to read, or 'All' to read available dialog parameters",
    )
    inspect_parser.add_argument(
        "--active-only",
        action="store_true",
        help="When used with --param All, return only currently active/effective parameters",
    )
    inspect_parser.add_argument(
        "--strict-active",
        action="store_true",
        help="Fail with inactive_parameter error when requested parameter is inactive",
    )
    inspect_parser.add_argument(
        "--resolve-effective",
        action="store_true",
        help="When requested parameter is inactive, return known effective source/value mapping",
    )
    inspect_parser.add_argument(
        "--summary",
        action="store_true",
        help="When used with --param All, include compact active/inactive/effective summary lists",
    )
    inspect_parser.add_argument("--session", help="Session override for this command")

    list_opened_parser = subparsers.add_parser("list_opened", help="List loaded models")
    list_opened_parser.add_argument(
        "--session", help="Session override for this command"
    )

    session_parser = subparsers.add_parser(
        "session", help="Manage active MATLAB session"
    )
    session_subparsers = session_parser.add_subparsers(
        dest="session_action", required=True
    )

    session_subparsers.add_parser("list", help="List available MATLAB shared sessions")

    session_use_parser = session_subparsers.add_parser(
        "use", help="Set active session for future commands"
    )
    session_use_parser.add_argument("name", help="Session name, e.g. MATLAB_12345")

    session_subparsers.add_parser(
        "current", help="Show currently configured active session"
    )
    session_subparsers.add_parser("clear", help="Clear active session configuration")
    return parser


def run_action(args):
    if args.action == "session":
        if args.session_action == "list":
            return command_session_list()
        if args.session_action == "use":
            return command_session_use(args.name)
        if args.session_action == "current":
            return command_session_current()
        if args.session_action == "clear":
            return command_session_clear()
        return {"error": f"Unsupported session action '{args.session_action}'"}

    eng = connect_to_session(getattr(args, "session", None))

    if args.action == "scan":
        return get_model_structure(
            eng,
            model_name=getattr(args, "model", None),
            recursive=getattr(args, "recursive", False),
            subsystem_path=getattr(args, "subsystem", None),
            hierarchy=getattr(args, "hierarchy", False),
        )
    if args.action == "highlight":
        return highlight_block(eng, args.target)
    if args.action == "inspect":
        return inspect_block(
            eng,
            args.target,
            args.param,
            getattr(args, "model", None),
            active_only=getattr(args, "active_only", False),
            strict_active=getattr(args, "strict_active", False),
            resolve_effective=getattr(args, "resolve_effective", False),
            summary=getattr(args, "summary", False),
        )
    if args.action == "list_opened":
        return list_opened_models(eng)

    return {"error": f"Unsupported action '{args.action}'"}


if __name__ == "__main__":
    import sys

    try:
        parser = build_parser()
        parsed = parser.parse_args()
        result = run_action(parsed)
        emit_json(result)
        if isinstance(result, dict) and "error" in result:
            sys.exit(1)
    except ValueError as exc:
        emit_json({"error": str(exc)})
        sys.exit(1)
    except RuntimeError as exc:
        emit_json({"error": str(exc)})
        sys.exit(1)
    except Exception as exc:
        emit_json({"error": f"Unexpected error: {exc}"})
        sys.exit(1)
