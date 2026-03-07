# Agent-First CLI Optimization Design (P1-P3)

Date: 2026-03-07
Status: Approved
Scope: End-to-end optimization of `simulink-scan` skill and CLI scripts for AI-agent workflows.

Reference:
- Justin Poehnelt, "Rewrite your CLI for AI agents" ([link](https://justin.poehnelt.com/posts/rewrite-your-cli-for-ai-agents/))

## Goals

1. Make all machine-facing failures deterministic and code-driven.
2. Make CLI capability discoverable by agents without external docs parsing.
3. Provide explicit output-size and output-shape controls for token discipline.
4. Refactor skill docs into reusable, agent-first execution/recovery patterns.
5. Deliver incrementally in three PRs to keep review, rollback, and session handoff simple.

## Non-Goals

1. No write/edit Simulink operations.
2. No protocol-level changes outside current CLI+skill scope.
3. No broad package/repo restructuring beyond required files.

## PR Strategy

### PR1 (P1): Unified Error Contract

- Introduce stable error payload shape and stable error codes across:
  - `sl_core.py`
  - `sl_scan.py`
  - `sl_session.py`
- Remove dynamic natural-language `error` values.
- Ensure top-level exception fallback also emits stable machine JSON.

### PR2 (P2): Schema + Context Controls + Deterministic Ordering

- Add machine-readable introspection action (`schema` or equivalent).
- Add output controls for large payloads:
  - scan limits
  - inspect limits
  - selected fields
- Make ordering deterministic for repeatability:
  - models
  - blocks
  - parameter lists

### PR3 (P3): Skill/Reference Agent-First Refactor

- Rewrite `SKILL.md` into composable decision/run/recovery blocks.
- Add explicit error-code-to-next-command recovery matrix.
- Align `reference.md`, `README.md`, and `test-scenarios.md` with implemented CLI behavior.

## Target Architecture

## Error Layer

Introduce centralized error helpers (single source of truth):

- `error`: stable code
- `message`: concise human-readable summary
- `details`: structured contextual data
- `suggested_fix`: next action guidance for automated retries

All command paths return the same envelope for failures.

## Capability Introspection Layer

Expose a no-engine command that returns:

- available actions
- per-action fields
- field type / required / default / enum
- response contracts and error codes
- examples

This enables agent self-adaptation without scraping docs.

## Output Control Layer

Add explicit token controls:

- scan: max item count + optional field projection
- inspect: max parameter count + optional field projection
- return `total_count` and `truncated` metadata when clipping occurs

## Doc/Skill Layer

Shift from narrative-only docs to operational contracts:

- deterministic workflow
- explicit retry branches per error code
- compact default paths
- escalation paths for deep inspection

## Data Flow

1. Parse/validate request (`flags` or `--json`).
2. If introspection action: return schema directly.
3. Resolve session with strict semantics.
4. Execute domain operation.
5. Normalize/sort/clip output.
6. Emit JSON.

Failure at any step returns normalized error envelope.

## Error Code Set (Authoritative)

Input/Request:
- `invalid_input`
- `invalid_json`
- `unknown_parameter`
- `json_conflict`

Session:
- `no_session`
- `session_required`
- `session_not_found`
- `state_write_failed`
- `state_clear_failed`

Target Resolution:
- `model_required`
- `model_not_found`
- `subsystem_not_found`
- `invalid_subsystem_type`
- `block_not_found`

Inspection/Runtime:
- `inactive_parameter`
- `runtime_error`

## Testing Strategy

1. PR1: contract tests for stable error codes and envelope shape.
2. PR2: schema tests + output controls + deterministic ordering tests.
3. PR3: documentation consistency tests and scenario coverage updates.
4. Every PR runs full suite:
   - `python -m unittest discover -s tests -p "test_*.py" -v`

## Risks and Mitigations

1. Risk: behavior drift between docs and code.
   Mitigation: add docs consistency checks and keep docs changes in same PR.
2. Risk: too much change in one PR.
   Mitigation: strict PR boundaries and serial merge order.
3. Risk: agent incompatibility during transition.
   Mitigation: keep old success payloads where safe and add explicit schema contract.

## Acceptance Criteria

1. All failures expose stable machine-readable codes.
2. Agents can discover command contract via CLI introspection.
3. Large responses can be controlled explicitly.
4. Skill docs provide deterministic recovery playbooks.
5. All tests pass per PR and at final integration point.
