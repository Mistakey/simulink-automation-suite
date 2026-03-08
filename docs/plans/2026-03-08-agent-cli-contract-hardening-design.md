# Agent CLI Contract Hardening Design

**Date:** 2026-03-08  
**Status:** Approved for implementation

## Goal

Harden `simulink-scan` so AI agents can invoke actions deterministically without guessing parameter contracts, output budgets, or recovery paths.

## Problem

The CLI already supports machine-readable JSON, but there are still contract gaps for agent reliability:

- `schema` currently exposes weak type strings (for example `"<class 'str'>"`) and does not encode required/default/enum metadata.
- Output control patterns are not fully unified across high-volume actions.
- Follow-on changes can cause docs/implementation drift unless strict contract tests are expanded.

## Scope

In scope:

- Replace current schema payload with structured metadata for all actions.
- Standardize input validation and parameter constraints for all actions.
- Standardize output budget and projection controls for high-volume actions (`scan`, `inspect`, `connections`).
- Align README/SKILL/reference/scenarios with the hardened contract.
- Expand tests to enforce schema/json/docs/output-control consistency.

Out of scope:

- Model mutation/edit capabilities.
- Renaming plugin or skill identifiers.
- Replacing current session model behavior.

## Design Principles

1. **Deterministic contracts**  
   Every action in `schema` must define machine-usable field metadata: type, required, default, enum, description.

2. **Budget-first outputs**  
   High-volume actions must support bounded outputs and predictable truncation metadata.

3. **Error-code stability**  
   Keep stable error codes; improve validation detail rather than introducing unnecessary new codes.

4. **Docs-as-contract**  
   Documentation and tests must block contract drift.

## Contract Changes

### 1) Schema Payload Structure

Current:

- action fields map to Python class string representations.

Target:

- action fields map to structured dictionaries:
  - `type`
  - `required`
  - `default` (when applicable)
  - `enum` (when applicable)
  - `description`
- action-level `description`.
- top-level `version`.

### 2) Input Validation Rules

Unify validation semantics:

- text field hygiene remains strict on path/session-like parameters.
- enum validation for constrained fields.
- positive integer checks for all `max_*` and depth values.
- stable `invalid_input` envelope with field-local diagnostics.

### 3) Output Budget Controls

- `scan`: retain `max_blocks` + `fields`.
- `inspect`: retain `max_params` + `fields`.
- `connections`: add `max_edges` + `fields`.
- return `total_count`/`truncated` style metadata for clipped lists where applicable.

### 4) Connections Output Contract

Defaults:

- `direction=both`
- `depth=1`
- `detail=summary`

Detail tiers:

- `summary`: upstream/downstream block summaries.
- `ports`: include edge endpoints.
- `lines`: include line-level details.

Optional:

- `include_handles` only effective for `detail=lines`.

## Data-Flow and Runtime

### `sl_core.py`

- Define canonical action metadata and derive schema payload from it.
- Parse/validate both flags and JSON against the same metadata.
- Route actions to runtime functions with normalized defaults.

### `sl_scan.py`

- Keep read-only behavior.
- Add budget-aware edge clipping and optional field projection for `connections`.
- Keep deterministic ordering and deduping.

## Testing Strategy

1. **Schema tests**
   - enforce presence of structured metadata fields.
   - verify action definitions include required/default/enum information.

2. **JSON parsing tests**
   - validate acceptance of correct payloads for each action.
   - validate rejection of type/field/constraint violations.

3. **Output control tests**
   - scan/inspect/connections clipping and projection behavior.

4. **Docs contract tests**
   - ensure docs reflect all action names and key control flags.
   - ensure `connections` contract is documented in all entry points.

## Risks and Mitigations

- **Risk:** schema format change could break hidden callers.  
  **Mitigation:** this repository relies on skill/docs-driven agents; update docs/tests in same change and verify end-to-end.

- **Risk:** budget controls under- or over-truncate important info.  
  **Mitigation:** expose totals and truncation flags; keep sensible defaults.

- **Risk:** drift between docs and runtime.  
  **Mitigation:** expand docs contract tests and make them mandatory in full test run.

## Success Criteria

- Full test suite passes.
- `schema` is sufficient for an agent to construct valid requests without hardcoded knowledge.
- High-volume actions have explicit and tested budget controls.
- docs + tests + runtime contracts stay aligned.
