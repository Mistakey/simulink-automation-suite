**Language:** **English** | [简体中文](README.zh-CN.md)

# Simulink Automation Suite

![Claude Code Plugin](https://img.shields.io/badge/Claude_Code-Plugin-4A5568)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![MATLAB](https://img.shields.io/badge/MATLAB-Engine-orange)

Simulink Automation Suite is a Claude Code plugin for read-only Simulink automation workflows through MATLAB Engine for Python.

- Canonical plugin name: `simulink-automation-suite`
- Current shipped skill: `simulink-scan`
- Runtime Python module path: `skills.simulink_scan` (module naming only)

---

## Positioning

Simulink Automation Suite is built to make Simulink analysis agent-native in Claude Code:

- It exposes Simulink context as deterministic, machine-readable tool outputs.
- It lets AI reason on real model topology/parameters instead of screenshots.
- It keeps workflows real-time and token-efficient with clipping/projection controls.

In short: the plugin helps AI *understand first, then assist*.

![Positioning diagram](docs/assets/readme/positioning-ai-plugin-simulink.png)

---

## Why This Plugin Exists

Common AI+Simulink workflows are often one of these:

1. Screenshot-based discussion: fast but shallow, visual-only understanding.
2. Export-and-parse flow: richer context but heavy, delayed, and token-expensive.

This plugin provides a third path: direct, structured, runtime model analysis for agents.

![Capability overview](docs/assets/readme/capability-overview.png)

---

## How It Works

1. Claude Code invokes the `simulink-scan` skill for Simulink analysis tasks.
2. The skill resolves MATLAB session context (`session list/use/current/clear`) with exact-name matching.
3. It executes one of the core actions: `schema`, `list_opened`, `scan`, `connections`, `inspect`, or `highlight`.
4. Results are returned as machine-readable JSON on `stdout`.
5. Failures use stable error codes for reliable agent recovery.

---

## Prerequisites

Before using session-bound actions (`list_opened`, `scan`, `connections`, `inspect`, `highlight`):

1. Install and activate MATLAB on your machine.
2. Install MATLAB Engine for Python in the same Python interpreter that runs this plugin.
3. In MATLAB Command Window, run:

```matlab
matlab.engine.shareEngine
```

Troubleshooting:

- `engine_unavailable`: MATLAB Engine for Python is unavailable in the active Python environment. Fix interpreter/environment installation.
- `no_session`: MATLAB Engine is available, but no shared MATLAB session is visible. Run `matlab.engine.shareEngine` in MATLAB, then retry.

---

## Quick Start

### 1. Add the marketplace source

```bash
/plugin marketplace add Mistakey/simulink-automation-suite
```

### 2. Install the plugin from marketplace

```bash
/plugin install simulink-automation-suite@simulink-automation-marketplace
```

### 3. Invoke the namespaced skill

```text
/simulink-automation-suite:simulink-scan Scan gmp_pmsm_sensored_sil_mdl recursively and focus on controller subsystems.
```

### 4. Verify plugin registration (optional)

```bash
/plugin list simulink-automation-suite@simulink-automation-marketplace
```

---

## Scenario Examples

For end-to-end Claude Code prompts and screenshots (single bilingual page), see:

- [docs/examples/claude-code-scenarios.md](docs/examples/claude-code-scenarios.md)

---

## Core Actions

| Action | Purpose | Example |
|---|---|---|
| `schema` | Return machine-readable command contract | `python -m skills.simulink_scan schema` |
| `list_opened` | List currently opened Simulink models | `python -m skills.simulink_scan list_opened` |
| `scan` | Read model/subsystem topology | `python -m skills.simulink_scan scan --model "my_model" --recursive` |
| `connections` | Read upstream/downstream key modules for a target block | `python -m skills.simulink_scan connections --target "my_model/Gain" --direction both --depth 1 --detail summary` |
| `inspect` | Read block parameters/effective values | `python -m skills.simulink_scan inspect --model "my_model" --target "my_model/Gain" --param "All"` |
| `highlight` | Highlight a block in Simulink (UI-only, no model mutation) | `python -m skills.simulink_scan highlight --target "my_model/Gain"` |
| `session` | Manage active MATLAB shared session | `python -m skills.simulink_scan session list` |

---

## Output Controls

Use output clipping/projected fields when you need compact payloads:

```bash
python -m skills.simulink_scan scan --model "my_model" --max-blocks 200 --fields "name,type"
python -m skills.simulink_scan inspect --model "my_model" --target "my_model/Gain" --param "All" --max-params 50 --fields "target,values"
python -m skills.simulink_scan connections --target "my_model/Gain" --detail ports --max-edges 50 --fields "target,edges,total_edges,truncated"
```

---

## JSON Request Mode

`--json` is a first-class entrypoint and is mutually exclusive with flag-based action arguments.
`schema` returns structured metadata for each action field (type, required/default/enum, description).

```bash
python -m skills.simulink_scan --json "{\"action\":\"schema\"}"
python -m skills.simulink_scan --json "{\"action\":\"list_opened\",\"session\":\"MATLAB_12345\"}"
python -m skills.simulink_scan --json "{\"action\":\"scan\",\"model\":\"my_model\",\"recursive\":true,\"session\":\"MATLAB_12345\"}"
python -m skills.simulink_scan --json '{"action":"connections","target":"my_model/Gain","direction":"both","depth":1,"detail":"summary","max_edges":50,"fields":["target","upstream_blocks","downstream_blocks"]}'
```

---

## Strict Defaults and Error Contract

- Session matching is exact-only (no fuzzy matching).
- If multiple MATLAB shared sessions exist, pass `--session` explicitly for MATLAB-bound actions.
- Unknown JSON fields return `unknown_parameter`.
- Invalid JSON or wrong JSON field types return `invalid_json`.

Error envelope:

```json
{
  "error": "<stable_code>",
  "message": "<human_readable_message>",
  "details": {},
  "suggested_fix": "<optional_next_step>"
}
```

Common error codes:

- `invalid_input`
- `invalid_json`
- `unknown_parameter`
- `json_conflict`
- `no_session`
- `session_required`
- `session_not_found`
- `model_required`
- `model_not_found`
- `subsystem_not_found`
- `invalid_subsystem_type`
- `block_not_found`
- `inactive_parameter`
- `runtime_error`

If no MATLAB shared session exists, run `matlab.engine.shareEngine` in MATLAB and retry.

---

## What's Inside

```text
simulink-automation-suite/
|-- .claude-plugin/
|   |-- plugin.json
|   |-- marketplace.json
|-- skills/
|   |-- simulink_scan/
|       |-- SKILL.md
|       |-- reference.md
|       |-- test-scenarios.md
|       |-- scripts/
|-- tests/
|-- docs/
|-- README.md
|-- README.zh-CN.md
```

---

## Verification

```bash
python -m unittest discover -s tests -p "test_*.py" -v
claude plugin validate .
```

---

## Roadmap

- **Current (v1.2.x):** solid read-only analysis foundation with `schema`, `session`, `list_opened`, `scan`, `connections`, `inspect`, `highlight`, plus strict agent-facing contracts.
- **Next:** strengthen agent workflow orchestration and reliability while preserving deterministic contracts and recovery paths.
- **Future:** add new skills for edit/build/repair scenarios without renaming the plugin (`simulink-automation-suite` remains the stable identity).

![Roadmap](docs/assets/readme/roadmap.png)
