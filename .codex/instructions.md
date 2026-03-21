# Codex Instructions

All project rules and architecture are documented in `.claude/CLAUDE.md`.
Detailed on-demand rules are in `.claude/rules/`.

Read `.claude/CLAUDE.md` first. When the task involves:
- CLI contract changes or adding actions → also read `.claude/rules/agent-first-cli.md`
- Releasing or version bumps → also read `.claude/skills/release/SKILL.md`, `.github/workflows/release.yml`, `scripts/check_release_metadata.py`, and `scripts/build_release_notes.py`

Subagent delegation is allowed in this repository for well-scoped work that materially advances the task, especially:
- code review before completion
- parallel investigation of independent codebase questions
- isolated implementation subtasks with clear file ownership
