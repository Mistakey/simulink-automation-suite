import argparse
import json
import sys
from pathlib import Path

import matlab.engine


STATE_FILE = Path(__file__).with_name(".sl_pilot_state.json")


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(message)


def emit_json(payload):
    print(json.dumps(payload, ensure_ascii=True, default=str))


def as_list(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def load_state():
    if not STATE_FILE.exists():
        return {}
    try:
        with STATE_FILE.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, dict):
            return data
    except Exception:
        return {}
    return {}


def save_state(state):
    with STATE_FILE.open("w", encoding="utf-8") as handle:
        json.dump(state, handle, ensure_ascii=True, indent=2)


def clear_state():
    if STATE_FILE.exists():
        STATE_FILE.unlink()


def get_saved_session_name():
    state = load_state()
    value = state.get("active_session")
    if isinstance(value, str) and value:
        return value
    return None


def set_saved_session_name(name):
    state = load_state()
    state["active_session"] = name
    save_state(state)


def render_no_session_guide():
    border = "+-----------------------------------------------------------+"
    lines = [
        border,
        "| CRITICAL ERROR: No shared MATLAB session found.          |",
        "| ACTION REQUIRED:                                         |",
        "| 1) Open MATLAB Command Window.                           |",
        "| 2) Run: matlab.engine.shareEngine                        |",
        border,
    ]
    sys.stderr.write("\n" + "\n".join(lines) + "\n\n")


def discover_sessions():
    try:
        return as_list(matlab.engine.find_matlab())
    except Exception as exc:
        raise RuntimeError(f"Failed to discover MATLAB sessions: {exc}")


def resolve_target_session(explicit_session=None):
    sessions = discover_sessions()
    if not sessions:
        render_no_session_guide()
        raise RuntimeError(
            "No shared MATLAB session found. Ask user to run matlab.engine.shareEngine in MATLAB."
        )

    if explicit_session:
        if explicit_session not in sessions:
            sys.stderr.write(
                f"[ERROR] Session '{explicit_session}' not found. Available sessions: {sessions}\n"
            )
            raise RuntimeError(f"Session '{explicit_session}' not found.")
        return explicit_session, sessions, "explicit"

    saved = get_saved_session_name()
    if saved:
        if saved in sessions:
            return saved, sessions, "saved"
        sys.stderr.write(
            f"[WARN] Saved session '{saved}' is unavailable. Falling back automatically.\n"
        )

    return sessions[0], sessions, "auto"


def connect_to_session(target_name=None):
    target, sessions, source = resolve_target_session(target_name)
    if len(sessions) > 1 and source == "auto":
        sys.stderr.write(
            f"[INFO] Multiple sessions found {sessions}. Connecting to '{target}'.\n"
        )

    try:
        return matlab.engine.connect_matlab(target)
    except Exception as exc:
        raise RuntimeError(f"Failed to connect to MATLAB session '{target}': {exc}")


def get_model_structure(eng):
    try:
        model_name = eng.bdroot()
        if not model_name:
            return {"error": "No active model found. Please open a Simulink model."}

        blocks = as_list(eng.find_system(model_name, "SearchDepth", 1, "Type", "block"))
        block_list = []
        for blk in blocks:
            if blk == model_name:
                continue
            block_list.append({"name": blk, "type": eng.get_param(blk, "BlockType")})

        return {"model": model_name, "blocks": block_list, "connections": []}
    except Exception as exc:
        return {"error": str(exc)}


def highlight_block(eng, block_path):
    try:
        eng.hilite_system(block_path, "find", nargout=0)
        return {"status": "success", "highlighted": block_path}
    except Exception as exc:
        return {"error": str(exc)}


def inspect_block(eng, block_path, param_name):
    try:
        eng.get_param(block_path, "Handle")
    except Exception as exc:
        return {"error": f"Block not found '{block_path}': {exc}"}

    try:
        if param_name != "All":
            value = eng.get_param(block_path, param_name)
            return {"target": block_path, "param": param_name, "value": value}

        dialog_params = eng.get_param(block_path, "DialogParameters")
        param_keys = [str(x) for x in as_list(eng.fieldnames(dialog_params))]
        values = {}
        for key in param_keys:
            try:
                values[key] = eng.get_param(block_path, key)
            except Exception as exc:
                values[key] = f"<unavailable: {exc}>"

        return {
            "target": block_path,
            "param": "All",
            "available_params": param_keys,
            "values": values,
        }
    except Exception as exc:
        return {"error": str(exc)}


def list_opened_models(eng):
    try:
        models = [str(x) for x in as_list(eng.find_system("Type", "block_diagram"))]
        return {"models": models}
    except Exception as exc:
        return {"error": str(exc)}


def command_session_list():
    sessions = discover_sessions()
    return {
        "sessions": sessions,
        "active_session": get_saved_session_name(),
        "count": len(sessions),
    }


def command_session_use(name):
    sessions = discover_sessions()
    if not sessions:
        render_no_session_guide()
        return {
            "error": "No shared MATLAB session found. Ask user to run matlab.engine.shareEngine in MATLAB."
        }
    if name not in sessions:
        return {"error": f"Session '{name}' not found.", "sessions": sessions}

    set_saved_session_name(name)
    return {"status": "success", "active_session": name}


def command_session_current():
    saved = get_saved_session_name()
    sessions = discover_sessions()
    return {
        "active_session": saved,
        "is_available": bool(saved and saved in sessions),
        "sessions": sessions,
    }


def command_session_clear():
    clear_state()
    return {"status": "success", "active_session": None}


def build_parser():
    parser = JsonArgumentParser(description="Simulink AI Bridge Core")
    subparsers = parser.add_subparsers(dest="action", required=True)

    scan_parser = subparsers.add_parser("scan", help="Read active model topology")
    scan_parser.add_argument("--session", help="Session override for this command")

    highlight_parser = subparsers.add_parser("highlight", help="Highlight a block")
    highlight_parser.add_argument(
        "--target", required=True, help="Block path to highlight"
    )
    highlight_parser.add_argument("--session", help="Session override for this command")

    inspect_parser = subparsers.add_parser("inspect", help="Inspect block parameters")
    inspect_parser.add_argument("--target", required=True, help="Block path to inspect")
    inspect_parser.add_argument(
        "--param",
        default="All",
        help="Parameter name to read, or 'All' to read available dialog parameters",
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
        return get_model_structure(eng)
    if args.action == "highlight":
        return highlight_block(eng, args.target)
    if args.action == "inspect":
        return inspect_block(eng, args.target, args.param)
    if args.action == "list_opened":
        return list_opened_models(eng)

    return {"error": f"Unsupported action '{args.action}'"}


if __name__ == "__main__":
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
