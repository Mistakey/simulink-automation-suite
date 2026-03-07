# Simulink Scan Skill Test Scenarios

Use these scenarios to validate skill behavior with and without the skill loaded (RED/GREEN style).

## Scenario 1: Multiple Models, No Explicit Target

- Prompt: "Scan my model deeply and tell me controller structure"
- Setup: 2+ opened models
- Expected:
  - Must run `list_opened` first
  - Must avoid scanning with ambiguous model context
  - Must surface `model_required` and candidate model alternatives
  - Must rerun with explicit `--model`

## Scenario 2: Inactive Parameter Misread Risk

- Prompt: "Inspect PolePairs and confirm effective value"
- Setup: masked block where PolePairs is inactive, Mechanical is active
- Expected:
  - Must avoid naive raw-value conclusion
  - Must use `--strict-active` or `--resolve-effective`
  - Must mention effective source when resolved

## Scenario 3: Subsystem Path Invalid

- Prompt: "Scan subsystem X recursively"
- Setup: subsystem name is wrong
- Expected:
  - Must return tool error
  - Must suggest likely alternatives from shallow top-level scan

## Scenario 4: Session Missing

- Prompt: "Scan model gmp_pmsm_sensored_sil_mdl"
- Setup: no shared MATLAB session
- Expected:
  - Must surface JSON error
  - Must provide action: run `matlab.engine.shareEngine`

## Scenario 5: Write Request Rejection

- Prompt: "Set Gain to 5 and add a block"
- Expected:
  - Must reject write/edit action under this skill
  - Must offer read-only analysis alternative

## Scenario 6: Token Discipline Under Large Model

- Prompt: "Analyze entire model"
- Setup: very large model
- Expected:
  - Must do shallow scan first
  - Must summarize key results
  - Must avoid full recursive dump unless explicitly requested

## Scenario 7: Session Recovery Chain (`session_required`)

- Prompt: "Scan model m1 now"
- Setup: 2+ shared MATLAB sessions, no explicit `--session`
- Expected:
  - First response returns `session_required`
  - Recovery step runs `session list`
  - Retry uses exact `--session` and succeeds

## Scenario 8: Subsystem Recovery Chain (`subsystem_not_found`)

- Prompt: "Scan subsystem controller/internal recursively"
- Setup: subsystem path is invalid
- Expected:
  - First response returns `subsystem_not_found`
  - Recovery step runs shallow root scan
  - Retry uses a valid subsystem path and succeeds

## Scenario 9: Inactive Parameter Recovery Chain (`inactive_parameter`)

- Prompt: "Give me the effective PolePairs value"
- Setup: requested parameter is inactive in current mask config
- Expected:
  - `--strict-active` returns `inactive_parameter`
  - Recovery step reruns with `--resolve-effective`
  - Output includes resolved effective source/value
