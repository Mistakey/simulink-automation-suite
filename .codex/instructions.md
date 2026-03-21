# Codex Instructions

All project rules and architecture are documented in `.claude/CLAUDE.md`.

Read `.claude/CLAUDE.md` first. When the task involves:
- CLI contract changes or adding actions → also read `simulink_cli/CLAUDE.md`
- Releasing or version bumps → also read `.claude/skills/release/SKILL.md`

## Quick Commands

```bash
# Run all tests
python -m unittest discover -s tests -p "test_*.py" -v

# Run single test
python -m unittest tests.test_schema_action -v

# Local invocation
python -m simulink_cli schema
python -m simulink_cli --json '{"action":"schema"}'
```
