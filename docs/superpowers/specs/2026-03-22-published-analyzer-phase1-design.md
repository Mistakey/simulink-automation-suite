# Published Analyzer Phase 1 Design

Date: 2026-03-22
Scope: published `simulink-analyzer` agent, `simulink-automation` skill responsibility split, handoff contract, output contract, manifest, docs, and tests

## Background

The simulink-automation-suite plugin currently ships a single unified skill (`simulink-automation`) that guides the main agent through both read analysis and write operations. All CLI output — scan results, connection graphs, parameter lists, multi-step analysis reasoning — lands directly in the main agent's conversation context.

This creates a compounding context cost:

- A 5-step analysis workflow (scan → find → inspect → connections → inspect) generates 25–35 KB of context including CLI commands, responses, and intermediate reasoning.
- None of this can be discarded by the main agent once it enters the conversation.
- Repeated analysis workflows in a single session degrade context quality and displace earlier conversation content.
- Existing CLI output controls (max_blocks, max_params, max_edges, fields projection) bound individual responses but do not address accumulated multi-step context.

The core problem is not that individual results are too large. The core problem is that the main agent cannot release intermediate analysis context after consuming it.

A subagent running in isolation solves this: all CLI invocations, intermediate outputs, and analysis reasoning stay in the subagent's context. Only a structured summary returns to the main agent.

## Goals

- Publish a `simulink-analyzer` agent as a first-class plugin component for read-only model analysis.
- Split skill and agent responsibilities so read analysis runs in isolated context and write operations remain in the main agent's conversation.
- Define an explicit handoff contract between the skill and the agent, covering direct handling, delegation, and composite request decomposition.
- Define a stable output contract for the analyzer agent that the main agent can reliably consume.
- Ship updated manifest, docs, and tests that treat the agent as part of the product surface.

## Non-Goals

- No task-type agent team or coordinator pattern. If the single analyzer hits its own context limits on large analyses, team decomposition is a future evaluation, not a Phase 1 deliverable.
- No long-lived resident agents. Each analyzer dispatch is stateless; the agent does not retain memory across dispatches. Live Simulink models change from multiple sources, making cached agent state unsafe.
- No CLI action contract expansion. No new actions, parameters, output shapes, or error codes are introduced.
- No repurposing of `reference.md` as a general analyzer handbook. It remains a write-operation response reference.
- No release-policy decoupling of schema version from plugin version. Schema version bumps with plugin major.minor per current policy. Decoupling is deferred infrastructure work.
- No changes to the CLI runtime (`simulink_cli/` code) beyond the schema version literal.

## Product Boundary

This version explicitly targets:

- one published read-analysis agent
- one existing skill refocused on writes, meta-queries, and quick lookups
- explicit handoff contract between skill and agent
- structured six-section output envelope for all analyzer responses
- product-level dispatch contract requiring explicit session and model context

This version explicitly does not target:

- multi-agent orchestration or parallel analysis
- agent-to-agent communication
- conditional routing based on expected output size (connections depth, scan max_blocks)
- automatic fallback from agent to direct CLI when the agent is unavailable

## Design Summary

### 1. Publish a read-analysis agent alongside the existing skill

The plugin gains a second component type: a published agent. The skill and agent have non-overlapping responsibilities determined by function, not by output size optimization.

- **Agent** (`simulink-analyzer`): topology scanning, block search, connection tracing, full-parameter inspection, and multi-step read analysis workflows.
- **Skill** (`simulink-automation`): write operations (set_param, model lifecycle), session management, single-parameter quick inspection, highlight, and schema discovery.

### 2. Handoff is a product contract, not just platform matching

Platform description matching provides the first layer of routing. The skill contains an explicit Responsibility & Handoff section that serves as the product contract layer — it tells the main agent what to handle directly, what to delegate, and how to decompose composite requests.

### 3. Analyzer output follows a fixed six-section envelope

Every analyzer response uses the same section structure. Section names are fixed constants treated as stable API. The main agent can reliably locate any section by name.

### 4. Dispatch requires explicit resolved context

Session and model are required product-level dispatch inputs. This is an agent orchestration rule, not a restatement of CLI schema required fields. The analyzer must not infer session or model by calling discovery actions.

## Product Surface

After this release, the plugin ships:

| Component | Type | Trigger |
|-----------|------|---------|
| `simulink-automation` | Skill | Loaded when user request involves Simulink modification, session management, or quick parameter lookup |
| `simulink-analyzer` | Agent | Dispatched when user request involves model analysis, topology exploration, connection tracing, or multi-step read workflows |

Both are declared in `plugin.json`. Skills use directory auto-discovery; agents use explicit file paths per repository manifest policy (`PLUGIN_SCHEMA_NOTES.md`).

## Skill / Agent Responsibility Split

| Action | Route | Handler | Rationale |
|--------|-------|---------|-----------|
| `session` (list/current/use/clear) | Direct | Skill | Meta-query; main agent needs session context for dispatch decisions |
| `list_opened` | Direct | Skill | Meta-query; main agent needs model list for dispatch decisions |
| `schema` | Direct | Skill | Self-discovery; main agent may need action catalog |
| `highlight` | Direct | Skill | UI side-effect; no analysis output to isolate |
| `inspect` (specific target + specific param) | Direct | Skill | Single-value response (~0.3 KB); main agent needs the value in context |
| `inspect` (no specific param or param=All) | Delegate | Agent | Full parameter list; potentially large output |
| `scan` (any configuration) | Delegate | Agent | Topology output; potentially large |
| `find` (any criteria) | Delegate | Agent | Search results; potentially large |
| `connections` (any configuration) | Delegate | Agent | Connection graph; potentially large |
| `set_param` | Direct | Skill | Write operation; requires user interaction for safety |
| `model_new` / `model_open` / `model_save` | Direct | Skill | Write/lifecycle operations |
| Multi-step read analysis | Delegate | Agent | Workflow-level context isolation |

The boundary between direct and delegated actions is based on the functional nature of each action, not on runtime output size estimation. `connections(depth=1, detail=summary)` and `scan(recursive=false, max_blocks=10)` are acknowledged as small-output scenarios that still route through the agent in this version. If usage data shows these patterns are frequent and latency-sensitive, they become candidates for the direct-handling whitelist in a future release.

## Responsibility & Handoff Contract

The skill must include an explicit Responsibility & Handoff section. This section is the product contract layer — it is read by the main agent when the skill is loaded and determines behavior regardless of how platform matching resolved.

The handoff contract must address four scenarios:

### Scenario 1: Platform correctly dispatches agent

User asks "analyze this model's topology." Platform matches agent description and dispatches directly. Skill is not involved. No handoff needed.

### Scenario 2: Platform loads skill but does not dispatch agent

User asks "what blocks are in this model?" Platform loads skill but does not auto-dispatch the agent. The skill's Responsibility & Handoff section tells the main agent: topology scanning is handled by the simulink-analyzer agent. Main agent reads this and dispatches.

### Scenario 3: Composite request

User asks "check the PID controller parameters, then set Kp to 2.0." Platform loads skill (write operation detected). Skill's composite-request rule tells the main agent: dispatch analyzer for the analysis portion first, then use analysis results to execute the write workflow.

### Scenario 4: Direct handling

User asks "what is the Gain of block X?" Skill's direct-handling list tells the main agent: single-parameter inspection with a specific target and specific param is handled directly. Main agent calls the CLI without dispatching the agent.

## Analyzer Output Contract

Every analyzer response must use this exact six-section envelope. Section names are fixed. Order is fixed. No additional sections are permitted.

```markdown
## Context
- Session: {session_name}
- Model: {model_name}
- Scope: {subsystem or "full model"}

## Answer
[Direct answer to the task, 1–5 sentences]

## Evidence
- [Key data points supporting the answer, one per line]

## Actions Performed
- action(key_params) → key result metrics (e.g., total_count=47, truncated=false)

## Limitations
- [Truncations, unverified items, or speculative conclusions; "None" if complete]

## Suggested Followup
- [Recommended next step if analysis is incomplete; "None" if complete]
```

### Envelope rules

- Section names are stable API. Adding a section is a minor change. Removing or renaming a section is a breaking change.
- The Context section must reflect the actual session and model used, matching the dispatch inputs.
- The Answer section must contain quantitative data where applicable, not only qualitative descriptions.
- The Actions Performed section must list every CLI invocation the agent made, enabling traceability and debugging.
- The Limitations section must explicitly surface any truncation (`truncated=true` from CLI responses) or scope restrictions.
- The agent must not execute write actions (set_param, model_new, model_open, model_save).
- The agent must not call session management or list_opened actions to infer context. Session and model come from the dispatch.

## Dispatch Contract

Dispatch to the analyzer agent requires explicit resolved context. This is a product-level orchestration rule, not a restatement of CLI schema required fields.

| Parameter | Required | Source | Notes |
|-----------|----------|--------|-------|
| `session` | Always | Main agent resolves via direct `session current` or `list_opened` before dispatch | Agent must not self-discover |
| `model` | Always | Main agent resolves via direct `list_opened` before dispatch | Agent must not self-discover |
| `target` | When task focuses on a specific block | Main agent provides resolved block path | Required for block-level analysis |
| `subsystem` | Optional | Main agent provides to narrow scope | Used by agent for scoped scan/find |

The dispatch itself is a natural-language task description accompanied by the resolved context parameters. The agent decides which CLI actions to invoke based on the task description.

## Agent File Structure

The agent is defined as a single markdown file with YAML frontmatter and an inline playbook:

```
agents/
  simulink-analyzer.md
```

File format follows the plugin agent convention: frontmatter defines name, description, model, color, and tools; the markdown body is the system prompt containing the playbook.

The playbook includes:

- Role definition (read-only Simulink model analyzer)
- CLI invocation pattern (`python -m simulink_cli --json '{...}'`)
- Schema self-discovery instruction (call `schema` action for action catalog)
- Analysis strategies (scan-first for topology, find for targeted search, connections for signal tracing)
- Six-section output envelope template and enforcement rules
- Write prohibition declaration
- Explicit context requirement (session/model from dispatch, no self-inference)

Phase 1 targets approximately 50–80 lines for the playbook. If the playbook exceeds 80 lines in future iterations, it should be extracted to a standalone `analyzer-playbook.md` file referenced by the agent definition.

## Manifest Changes

### plugin.json

Add `agents` field with explicit file paths. Update version and description.

```json
{
  "name": "simulink-automation-suite",
  "description": "Simulink automation suite plugin for Claude Code with model analysis agent and parameter editing skill.",
  "version": "2.2.0",
  "author": {
    "name": "kelch"
  },
  "skills": [
    "./skills/"
  ],
  "agents": [
    "./agents/simulink-analyzer.md"
  ],
  "keywords": [
    "simulink",
    "matlab",
    "automation",
    "claude-code",
    "agent-first",
    "scan",
    "analysis",
    "edit"
  ]
}
```

`skills` continues to use directory auto-discovery. `agents` uses explicit file paths per repository manifest policy (`PLUGIN_SCHEMA_NOTES.md` line 17: "Use explicit file paths for `agents` if agents are added later"). Each entry in `agents` is a path to a specific published agent file. Adding a new agent requires adding its path to this array.

### marketplace.json

Update `plugins[0].version` to `2.2.0`. Update `plugins[0].description` to match plugin.json.

## Documentation Changes

### SKILL.md

The existing workflow strategy, discovery, and output discipline sections remain. The following changes are required:

- Add a **Responsibility & Handoff** section (see contract above).
- Remove or reduce read-analysis workflow strategy content that is now the agent's responsibility. The skill retains enough context for the direct-handling cases (single-param inspect, session management) but does not need to teach multi-step analysis workflows.
- Add a one-line reference to the analyzer agent for deep analysis tasks.

### README.md / README.zh-CN.md

Update product description to a dual-capability narrative:

- Read Analysis — the simulink-analyzer agent autonomously explores model topology, traces connections, audits parameters, and returns structured findings without polluting conversation context.
- Write Automation — the simulink-automation skill guides safe parameter modification with dry-run preview, precondition guards, and rollback support.

### reference.md

No changes. Remains a write-operation response shape reference.

## Test Changes

### New: test_agent_definition_contract.py

Tests iterate over agent files declared in the `agents` array of `plugin.json`. This ties the test surface directly to the manifest — an agent file that is not listed in the manifest is not tested, and a manifest entry that points to a missing file fails. Tests validate product-owned contract only; platform-internal frontmatter details (model, color, tools) are left to `claude plugin validate .`.

| Test | Assertion |
|------|-----------|
| `test_manifest_agents_not_empty` | `plugin.json` `agents` array contains at least one entry |
| `test_each_declared_agent_file_exists` | Every path in the `agents` array resolves to an existing `.md` file |
| `test_each_agent_has_name_and_description` | YAML frontmatter contains `name` and `description` fields |
| `test_each_agent_playbook_has_exact_envelope_shape` | Markdown body contains exactly the six required H2 sections (`Context`, `Answer`, `Evidence`, `Actions Performed`, `Limitations`, `Suggested Followup`) in this exact order, with no additional H2 sections |
| `test_each_agent_playbook_forbids_writes` | Body contains write-prohibition declaration |
| `test_each_agent_playbook_requires_explicit_context` | Body contains explicit session/model requirement declaration |

The envelope shape test (`test_each_agent_playbook_has_exact_envelope_shape`) must extract the ordered list of H2 headings from the playbook body and assert equality against the canonical section list. A reordered, missing, or extra H2 section fails the test.

### Extended: test_plugin_manifest_contract.py

- `plugin.json` contains `agents` key
- `agents` value is a non-empty list
- Each entry in `agents` is a string path ending in `.md`
- Each declared agent file exists on disk

### Extended: test_docs_contract.py

- README.md describes analyzer agent capability (keyword check)
- README.zh-CN.md describes analyzer agent capability
- Each agent `name` from published agent frontmatter appears in at least one README

### Extended: test_docs_contract.py — Handoff contract coverage

The Responsibility & Handoff section in `SKILL.md` is a product contract, not just documentation. Tests must verify its structural content, not only its existence.

| Test | Assertion |
|------|-----------|
| `test_skill_has_handoff_section` | SKILL.md contains a section titled "Responsibility & Handoff" |
| `test_handoff_declares_direct_handling_bucket` | Handoff section contains a direct-handling subsection listing actions the skill handles without delegation |
| `test_handoff_direct_bucket_covers_required_actions` | Direct-handling bucket mentions: `session`, `list_opened`, `schema`, `highlight`, and `inspect` with specific param qualifier |
| `test_handoff_declares_delegation_bucket` | Handoff section contains a delegation subsection listing actions routed to the analyzer agent |
| `test_handoff_delegation_bucket_covers_required_actions` | Delegation bucket mentions: `scan`, `find`, `connections`, `inspect` without specific param, and multi-step analysis |
| `test_handoff_declares_composite_request_rule` | Handoff section contains a composite-request subsection describing the analyze-then-write decomposition |

These tests use keyword presence checks within the identified subsections, not brittle full-text matching. The goal is to ensure the three buckets (direct / delegate / composite) exist and cover the required action categories. Exact wording may evolve; structural coverage must not regress.

## Versioning and Release Impact

### Version numbers

| Location | Value | Rationale |
|----------|-------|-----------|
| `plugin.json` version | `2.2.0` | New capability: minor bump |
| `marketplace.json` version | `2.2.0` | Synced with plugin version |
| `core.py` schema version | `"2.2"` | Current release policy requires schema major.minor = plugin major.minor |
| Git tag | `v2.2.0` | Standard release tag |

The schema version bump to "2.2" does not reflect a CLI action contract change. It is a scope-control decision: the current release policy enforces `schema_version == f"{plugin_major}.{plugin_minor}"` via `check_release_metadata.py`, and modifying that policy is out of scope for this release. Decoupling schema version from plugin version is recorded as deferred infrastructure work.

### Roadmap version reallocation

The Phase 1 sub-phases design (`2026-03-21-phase1-sub-phases-design.md`) allocated v2.2.0 to Block Placement (`block_add`). This release reallocates v2.2.0 to the published analyzer agent. The roadmap should be updated:

| Original | Revised |
|----------|---------|
| v2.2.0 — Block Placement | v2.3.0 — Block Placement |
| v2.3.0 — Signal Routing | v2.4.0 — Signal Routing |

### Release notes

This is a minor release with a new product surface. Curated release notes are required per current release policy. The notes should be positioned as a product architecture release, not a capability expansion release.

## Verification

Minimum verification before claiming completion:

```bash
# Full test suite
python -m unittest discover -s tests -p "test_*.py" -v

# Agent and manifest contract tests specifically
python -m unittest tests.test_agent_definition_contract -v
python -m unittest tests.test_plugin_manifest_contract tests.test_marketplace_manifest_contract -v
python -m unittest tests.test_docs_contract -v

# Release metadata
python scripts/check_release_metadata.py --tag v2.2.0

# Plugin validation
claude plugin validate .

# Schema output (should show version "2.2", same action set)
python -m simulink_cli schema
```

The schema output must show version "2.2" with no changes to the action set, field definitions, or error codes compared to version "2.1".

## Risks and Mitigations

- **Risk:** Analyzer summary loses critical information that the user needs, requiring re-dispatch.
  **Mitigation:** The six-section envelope requires quantitative data in Answer, explicit data points in Evidence, and explicit gaps in Limitations. Summary quality is the primary metric to observe post-release. If follow-up dispatches exceed 30% of analysis tasks, the playbook needs iteration.

- **Risk:** Platform description matching triggers the agent for tasks better handled directly by the skill (e.g., single-param inspect), or fails to trigger the agent for analysis tasks.
  **Mitigation:** The skill's Responsibility & Handoff section provides a product-contract fallback. When the skill is loaded, it explicitly tells the main agent which tasks to delegate. This covers both false-positive and false-negative matching scenarios.

- **Risk:** Schema version "2.2" misleads CLI consumers into expecting action contract changes.
  **Mitigation:** This is a known trade-off documented in the Versioning section. The schema output is verified to contain the same action set. Decoupling is deferred work.

- **Risk:** Roadmap version reallocation causes confusion with the Phase 1 sub-phases design.
  **Mitigation:** Update `docs/roadmap.md` and note the reallocation in release notes.

- **Risk:** The agent's inline playbook grows beyond maintainable size.
  **Mitigation:** Phase 1 targets 50–80 lines. If the playbook exceeds 80 lines, extract to a standalone reference file. The threshold is documented as a design constraint.

## Acceptance Criteria

This version is complete only when all of the following are true:

1. `agents/simulink-analyzer.md` exists at the path declared in `plugin.json` `agents` array and passes all agent definition contract tests.
2. `plugin.json` declares `agents` field with explicit file paths and is validated by `claude plugin validate .`.
3. `SKILL.md` contains a Responsibility & Handoff section with three verifiable buckets:
   - Direct-handling bucket covering session, list_opened, schema, highlight, and inspect-with-specific-param.
   - Delegation bucket covering scan, find, connections, inspect-without-specific-param, and multi-step analysis.
   - Composite-request rule describing analyze-then-write decomposition.
4. The analyzer playbook defines exactly six H2 sections (Context, Answer, Evidence, Actions Performed, Limitations, Suggested Followup) in fixed order with no extra H2 sections, enforced by `test_each_agent_playbook_has_exact_envelope_shape`.
5. The analyzer playbook contains write-prohibition and explicit-context-requirement declarations, enforced by contract tests.
6. README.md and README.zh-CN.md describe both the analyzer agent and the automation skill as product capabilities.
7. `test_docs_contract.py` verifies that every published agent name from manifest-declared agent files appears in README documentation.
8. Handoff contract tests verify structural content of the three buckets and their required action coverage, not only section existence.
9. All release metadata passes `check_release_metadata.py --tag v2.2.0` under current policy.
10. Full test suite passes with no regressions.
11. `python -m simulink_cli schema` returns version "2.2" with an unchanged action set.
