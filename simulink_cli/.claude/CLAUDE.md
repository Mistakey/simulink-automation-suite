# Agent-First CLI Design Philosophy

> This CLI is designed for **AI agent invocation**, not human interaction.
> Core distinction: Human DX optimizes for discoverability and forgiveness; Agent DX optimizes for predictability and defense-in-depth.
>
> Reference: [Rewrite Your CLI for AI Agents](https://justin.poehnelt.com/posts/rewrite-your-cli-for-ai-agents/)

---

## 1. JSON Payload as Primary Interface

Agents prefer structured JSON over bespoke flags — JSON maps directly to action schemas with zero translation loss.

- `--json '{...}'` is the primary agent entrypoint; flag mode exists for human convenience but is secondary
- The two modes are mutually exclusive — mixing returns an error, never silently merges
- Payload must be a JSON object with required `action` field: `{"action":"scan", "model":"demo"}`

**Rule**: both JSON mode and flag mode must produce identical internal representations. Changes to one path must be reflected in the other.

## 2. Schema Introspection Replaces Documentation

Agents can't google the docs without blowing up the token budget. The CLI itself must be the canonical documentation source.

- A `schema` action returns the full action catalog: fields, types, defaults, enums, descriptions, error codes
- Per-action field metadata dicts are the **single source of truth**. Schema output aggregates them at runtime.
- Static docs (SKILL.md) encode workflow invariants that schema cannot express (e.g., "always dry-run before write"). They must never duplicate field lists or execution templates already available through `schema`.

**Rule**: if a field is not declared in the action's metadata dict, it does not exist for agents. Tests should enforce schema completeness.

## 3. Context Window Discipline

Large outputs overwhelm agent context. Every action that returns lists must support bounded, projectable output.

Three mechanisms:

| Mechanism | Purpose | Example |
|---|---|---|
| **Field projection** (`fields`) | Return only requested keys | `"fields": ["name", "type"]` |
| **Count limits** (`max_blocks`, `max_params`, etc.) | Cap list length | `"max_blocks": 20` |
| **Truncation metadata** (`truncated`, `total_count`) | Tell agent when data is clipped | `"truncated": true, "total_count": 150` |

**Rules**:
- Default responses stay compact. Never return unbounded lists.
- Default to shallow scans; escalate to deep/recursive only when explicitly requested.
- Always include truncation metadata so agents can decide whether to paginate.

## 4. Input Hardening Against Hallucinations

Agents hallucinate. Treat all input as untrusted — same as you would for a web API.

**Validation tiers** (strictest to most permissive):

| Tier | Target | Policy |
|---|---|---|
| General text | model names, subsystem paths, session names | Reject control chars, reserved chars (`?#%`), leading/trailing whitespace, empty, length overflow |
| Domain identifiers | block paths, parameter names | Permissive — MATLAB identifiers can contain newlines and special chars. Reject only null bytes. |
| Arbitrary values | parameter values | Most permissive — accept nearly anything. Reject only null bytes. |
| Type enforcement | all fields in JSON mode | Strict: `bool` for boolean (not `1`/`0`), `int` for integer, `list` for array. No coercion. |

**Anti-patterns** (never do these):
- Silently trim or coerce malformed input — fail fast with a stable error code
- Silently ignore unknown fields — return an error naming the unrecognized field
- Accept truthy/falsy values as boolean — require actual `true`/`false`

## 5. Write Safety: Three Tiers

Not every mutation needs the same ceremony. Three tiers, from strictest to lightest:

### Full Guarded

dry_run default true → apply_payload → precondition check → execute → read-back verify → rollback payload.

Applies to: `set_param`.

Use for operations that **overwrite existing state** where a single undo operation exists. The four layers:

1. **Dry-run by default**: preview the diff without touching the model. Return both an `apply_payload` (to execute) and a `rollback` payload (to undo).
2. **Precondition guard**: accept an `expected_current_value`; reject if observed value differs, preventing stale writes.
3. **Read-back verification**: after write, immediately re-read and compare. Error if mismatch.
4. **Rollback in every response**: both dry-run and committed writes include a rollback payload to restore original state.

Response must always include a `write_state` field:
- `"not_attempted"` — dry-run preview, no mutation occurred
- `"verified"` — write succeeded and read-back confirmed
- Error responses indicate whether rollback is needed

### Checked Mutation

Precondition check → execute → verify → rollback payload. No dry_run preview.

Applies to: `block_add`, `block_delete`, `line_add`, `line_delete`, `model_new`.

Use for operations that **create or remove structure**. Precondition and rollback matter, but previewing an add/delete adds little value. Rollback may be `available: false` if atomic undo is not possible (e.g., `block_delete` destroys params and connections).

### Operational

Execute → error handling → necessary constraints. No dry_run or rollback.

Applies to: `model_open`, `model_save`, `model_close`, `model_update`, `simulate`.

Constraints still apply (e.g., `close` checks dirty state, `simulate` validates model loaded), but these are not mutation-preview operations.

**Rule**: when adding new write actions, choose the appropriate tier. Default to Checked Mutation unless the operation overwrites existing values (Full Guarded) or is a non-destructive lifecycle operation (Operational).

## 6. Error Contract

Stable envelope — never change its shape:

```json
{"error": "<code>", "message": "<text>", "details": {}, "suggested_fix": "<action>"}
```

**Rules**:
- Exit code: `0` = success, `1` = any error
- `suggested_fix` must be concrete and agent-actionable (e.g., a JSON payload the agent can re-submit)
- Reuse existing error codes before inventing new ones. New codes must appear in the action's error list.
- Error codes are part of the public API — treat them as stable identifiers, not display strings

## 7. Action Module Contract

Each action is a self-contained module registered in a central registry. Every module must export:

| Export | Type | Purpose |
|---|---|---|
| `DESCRIPTION` | `str` | One-line description for schema |
| `FIELDS` | `dict` | Field metadata: type, required, default, description, enum |
| `ERRORS` | `list[str]` | Error codes this action can produce |
| `validate(args)` | `fn → None \| dict` | Pre-execution validation; return error dict or None |
| `execute(args)` | `fn → dict` | Run the action; return result dict |

Routing is always: `validate()` → `execute()`. If validation returns a dict, it is emitted as error without calling execute.

**Rule**: no action may bypass the validate → execute pipeline. No side effects in `validate()`.

## 8. Session Matching: Exact-Name Only

Session resolution uses **strict exact-name matching** — no fuzzy search, no substring, no partial match.

Resolution priority:
1. Explicit session → exact match or error
2. Single session available → auto-select
3. Saved session in state file + still alive → reuse
4. Multiple sessions, no saved preference → error (agent must choose explicitly)
5. No sessions → error

**Never add fuzzy matching.** Agents need deterministic resolution; ambiguity causes cascading errors.

## 9. Multi-Surface Consistency

If MCP or other agent surfaces are added:
- Reuse the same action registry and field metadata — no split definitions
- Emit the same JSON envelope for success and error
- Use the same schema output as the machine-readable contract

One source of truth, multiple surfaces.
