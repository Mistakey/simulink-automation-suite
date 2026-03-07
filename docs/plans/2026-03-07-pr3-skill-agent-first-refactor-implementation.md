# PR3 Skill Agent-First Refactor Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refactor skill and docs into composable, deterministic runbooks aligned with implemented CLI behavior and error recovery paths.

**Architecture:** Keep runtime scripts intact except doc-alignment necessities. Rebuild skill docs around command selection, recovery routing by error code, and minimal-token defaults. Add lightweight consistency tests to reduce future drift between docs and code contracts.

**Tech Stack:** Markdown docs, Python `unittest` for lightweight contract checks

---

Skill references: `@test-driven-development`, `@verification-before-completion`

### Task 1: Restructure `SKILL.md` into Agent-First Runbook

**Files:**
- Modify: `skills/simulink_scan/SKILL.md`

**Step 1: Write the failing test/check**

Create a docs contract test to assert required sections/keywords exist:
- decision flow
- default JSON path
- token discipline
- recovery hooks

**Step 2: Run check to verify it fails**

Run: `python -m unittest discover -s tests -p "test_docs_contract.py" -v`
Expected: FAIL (test file/sections missing).

**Step 3: Write minimal implementation**

Rewrite `SKILL.md` structure:
- preflight
- action selection
- execution templates
- recovery matrix references
- output compaction rules

**Step 4: Run check to verify it passes**

Run: `python -m unittest discover -s tests -p "test_docs_contract.py" -v`
Expected: PASS for skill section checks.

**Step 5: Commit**

```bash
git add skills/simulink_scan/SKILL.md tests/test_docs_contract.py
git commit -m "docs(skill): refactor skill into agent-first composable runbook"
```

### Task 2: Add Error-Code Recovery Matrix in `reference.md`

**Files:**
- Modify: `skills/simulink_scan/reference.md`
- Modify: `tests/test_docs_contract.py`

**Step 1: Write the failing test/check**

Extend doc contract checks to require matrix entries for key codes:
- `session_required`
- `session_not_found`
- `model_required`
- `inactive_parameter`
- `invalid_json`

**Step 2: Run check to verify it fails**

Run: `python -m unittest discover -s tests -p "test_docs_contract.py" -v`
Expected: FAIL.

**Step 3: Write minimal implementation**

Add table in `reference.md`:
- error code
- likely cause
- exact next command
- expected success signal

**Step 4: Run check to verify it passes**

Run: `python -m unittest discover -s tests -p "test_docs_contract.py" -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add skills/simulink_scan/reference.md tests/test_docs_contract.py
git commit -m "docs(reference): add error recovery matrix for deterministic retries"
```

### Task 3: Align `README.md` and `test-scenarios.md`

**Files:**
- Modify: `README.md`
- Modify: `skills/simulink_scan/test-scenarios.md`
- Modify: `tests/test_docs_contract.py`

**Step 1: Write the failing test/check**

Add checks for:
- `README.md` includes schema + output controls examples
- scenarios include recovery-chain examples tied to error codes

**Step 2: Run check to verify it fails**

Run: `python -m unittest discover -s tests -p "test_docs_contract.py" -v`
Expected: FAIL.

**Step 3: Write minimal implementation**

Update docs with command examples and recovery-focused scenarios.

**Step 4: Run check to verify it passes**

Run: `python -m unittest discover -s tests -p "test_docs_contract.py" -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add README.md skills/simulink_scan/test-scenarios.md tests/test_docs_contract.py
git commit -m "docs: align README and scenarios with agent-first CLI contracts"
```

### Task 4: Final Full Verification for PR3

**Files:**
- Verify all changed files in PR3 scope

**Step 1: Run complete test suite**

Run: `python -m unittest discover -s tests -p "test_*.py" -v`
Expected: all tests pass.

**Step 2: Manual docs spot-check**

Run:
- `git diff -- README.md skills/simulink_scan/SKILL.md skills/simulink_scan/reference.md skills/simulink_scan/test-scenarios.md`

Expected:
- No behavior contradiction
- error codes and commands consistent with code contract

**Step 3: Commit PR3 final polish if needed**

```bash
git add README.md skills/simulink_scan/SKILL.md skills/simulink_scan/reference.md skills/simulink_scan/test-scenarios.md tests/test_docs_contract.py
git commit -m "chore(docs): finalize agent-first documentation consistency"
```
