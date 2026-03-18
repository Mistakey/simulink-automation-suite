---
globs: ["simulink_cli/**/*.py", "skills/**/*.py", "tests/test_input*.py", "tests/test_json*.py", "tests/test_schema*.py"]
---

# Agent-First CLI Design Rules

> Based on [Rewrite Your CLI for AI Agents](https://justin.poehnelt.com/posts/rewrite-your-cli-for-ai-agents/) and former AGENTS.md §4.

Core distinction: **Human DX** optimizes for discoverability/forgiveness; **Agent DX** optimizes for predictability/defense-in-depth. This plugin targets Agent DX.

## 1. Raw JSON Payload First

- `--json` is the primary agent entrypoint, mapping directly to action/API structure.
- Mutually exclusive with flag-based arguments — mixing returns `json_conflict`.
- Never invent translation layers. The JSON payload IS the schema.

## 2. Runtime Schema Introspection

- `schema` action enables full runtime self-discovery: type, required, default, enum, description, error codes.
- Per-action `FIELDS` dicts are the single source of truth for field metadata. `core.py` aggregates them for schema output.
- The CLI itself is the canonical documentation source. Static docs supplement but never replace `schema` output.

## 3. Context Window Discipline

- Large outputs support response budgets: `max_blocks` / `max_params` / `max_edges` + `fields` projection.
- Default responses stay compact and bounded. Never return unnecessary data.
- Responses include `total_*` and `truncated` fields so agents know when data is clipped.
- Default to shallow scans; escalate to recursive/hierarchy only when explicitly requested.

## 4. Input Hardening Against Hallucinations

The CLI is frequently invoked by AI/LLM agents — **always assume inputs can be adversarial**.

Implemented in `validate_text_field()` and `validate_json_type()`:

| Threat | Validation |
|---|---|
| Control characters | Reject `ord(char) < 32` |
| Reserved characters | Reject `?`, `#`, `%` in path/session fields |
| Leading/trailing whitespace | Reject — no silent trimming |
| Empty strings | Reject on required fields |
| Length overflow | Enforce `max_len=256` on text fields |
| Type mismatches | Strict: boolean→`bool`, integer→`int`, array→`list` |
| Unknown fields | Return `unknown_parameter` — never silently ignore |
| Invalid JSON | Return `invalid_json` with parser message |
| Unrecognized CLI args | Map to `unknown_parameter` via `JsonArgumentParser.error()` |

Anti-pattern: silently coercing or ignoring malformed input. Fail fast with stable error code.

## 5. Structured Agent Skills (SKILL.md)

- Ship `SKILL.md` with YAML frontmatter for each capability.
- Encode invariants not obvious from `--help`: preflight steps, action selection tree, execution templates, recovery routing (error code → next action).
- Keep `SKILL.md`, `reference.md`, `test-scenarios.md` aligned with runtime behavior.

## 6. Multi-Surface Consistency

- If MCP/extensions are added, reuse the same per-action `FIELDS` dicts and `_ACTIONS` registry — no split definitions.
- `schema` output is the single machine-readable contract regardless of invocation surface.

## 7. Safety Rails

- Current capabilities are read-only. `highlight` is visual-only, must not mutate.
- Future write capabilities must ship with: `--dry-run`, explicit confirmation, rollback-aware design.
- Write capabilities are separate skills, never bolted onto `simulink-scan`.

## 8. Error Contract

Stable envelope (never change shape):

```json
{"error": "<code>", "message": "<text>", "details": {}, "suggested_fix": "<optional>"}
```

- Reuse existing error codes. `suggested_fix` is concrete and agent-actionable.
- Exit code 1 for errors, 0 for success.
- Recovery routing in `SKILL.md` maps each error code to a specific next action.
