import argparse
import difflib
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


def normalize_text(value):
    return value.strip().lower()


def resolve_session_alias(query, sessions):
    if query in sessions:
        return {"status": "exact", "matched": query}

    query_norm = normalize_text(query)
    normalized = {session: normalize_text(session) for session in sessions}

    starts_with = [s for s, sn in normalized.items() if sn.startswith(query_norm)]
    if len(starts_with) == 1:
        return {"status": "fuzzy", "matched": starts_with[0], "match_type": "prefix"}
    if len(starts_with) > 1:
        return {"status": "ambiguous", "candidates": starts_with}

    contains = [s for s, sn in normalized.items() if query_norm in sn]
    if len(contains) == 1:
        return {"status": "fuzzy", "matched": contains[0], "match_type": "contains"}
    if len(contains) > 1:
        return {"status": "ambiguous", "candidates": contains}

    close = difflib.get_close_matches(query, sessions, n=3, cutoff=0.6)
    if len(close) == 1:
        return {"status": "fuzzy", "matched": close[0], "match_type": "close"}
    if len(close) > 1:
        return {"status": "ambiguous", "candidates": close}

    return {"status": "missing"}


def get_effective_session(sessions):
    saved = get_saved_session_name()
    if saved and saved in sessions:
        return saved, "saved", saved
    if sessions:
        return sessions[0], "auto", saved
    return None, "none", saved


def resolve_target_session(explicit_session=None):
    sessions = discover_sessions()
    if not sessions:
        render_no_session_guide()
        raise RuntimeError(
            "No shared MATLAB session found. Ask user to run matlab.engine.shareEngine in MATLAB."
        )

    if explicit_session:
        resolved = resolve_session_alias(explicit_session, sessions)
        if resolved["status"] == "exact":
            return resolved["matched"], sessions, "explicit"
        if resolved["status"] == "fuzzy":
            matched = resolved["matched"]
            sys.stderr.write(
                f"[INFO] Session '{explicit_session}' matched '{matched}' ({resolved['match_type']}).\n"
            )
            return matched, sessions, "explicit_fuzzy"
        if resolved["status"] == "ambiguous":
            raise RuntimeError(
                f"Session '{explicit_session}' is ambiguous. Candidates: {resolved['candidates']}"
            )
        sys.stderr.write(
            f"[ERROR] Session '{explicit_session}' not found. Available sessions: {sessions}\n"
        )
        raise RuntimeError(f"Session '{explicit_session}' not found.")

    effective, source, saved = get_effective_session(sessions)
    if source == "auto" and saved:
        sys.stderr.write(
            f"[WARN] Saved session '{saved}' is unavailable. Falling back automatically.\n"
        )
    return effective, sessions, source


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


def get_opened_models(eng):
    return [str(x) for x in as_list(eng.find_system("Type", "block_diagram"))]


def get_model_structure(eng, model_name=None):
    try:
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

        blocks = as_list(
            eng.find_system(target_model, "SearchDepth", 1, "Type", "block")
        )
        block_list = []
        for blk in blocks:
            if blk == target_model:
                continue
            block_list.append({"name": blk, "type": eng.get_param(blk, "BlockType")})

        return {"model": target_model, "blocks": block_list, "connections": []}
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


def command_session_list():
    sessions = discover_sessions()
    effective, source, saved = get_effective_session(sessions)
    return {
        "sessions": sessions,
        "active_session": effective,
        "active_source": source,
        "configured_session": saved,
        "count": len(sessions),
    }


def command_session_use(name):
    sessions = discover_sessions()
    if not sessions:
        render_no_session_guide()
        return {
            "error": "No shared MATLAB session found. Ask user to run matlab.engine.shareEngine in MATLAB."
        }
    resolved = resolve_session_alias(name, sessions)
    if resolved["status"] == "missing":
        return {"error": f"Session '{name}' not found.", "sessions": sessions}
    if resolved["status"] == "ambiguous":
        return {
            "error": f"Session '{name}' is ambiguous.",
            "candidates": resolved["candidates"],
            "sessions": sessions,
        }

    selected = resolved["matched"]
    match_type = resolved.get("match_type", "exact")

    set_saved_session_name(selected)
    return {
        "status": "success",
        "active_session": selected,
        "input": name,
        "match_type": match_type,
    }


def command_session_current():
    sessions = discover_sessions()
    effective, source, saved = get_effective_session(sessions)
    return {
        "active_session": effective,
        "active_source": source,
        "configured_session": saved,
        "sessions": sessions,
    }


def command_session_clear():
    clear_state()
    return {"status": "success", "active_session": None}


def build_parser():
    parser = JsonArgumentParser(description="Simulink AI Bridge Core")
    subparsers = parser.add_subparsers(dest="action", required=True)

    scan_parser = subparsers.add_parser("scan", help="Read active model topology")
    scan_parser.add_argument(
        "--model", help="Optional specific model name from list_opened output"
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
        return get_model_structure(eng, getattr(args, "model", None))
    if args.action == "highlight":
        return highlight_block(eng, args.target)
    if args.action == "inspect":
        return inspect_block(eng, args.target, args.param, getattr(args, "model", None))
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
