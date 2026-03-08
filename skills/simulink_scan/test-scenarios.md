# Simulink Scan Skill Test Scenarios

Use these scenarios to validate skill behavior with and without the skill loaded (RED/GREEN style).

## Scenario 1: Model Disambiguation (`model_required`)

- Prompt: "Scan my model deeply and tell me controller structure"
- Setup: 2+ opened models
- Expected:
  - Must run `list_opened` first
  - Must avoid scanning with ambiguous model context
  - Must surface `model_required` with candidate model alternatives
  - Must rerun with explicit `--model`

## Scenario 2: Session Missing (`no_session`)

- Prompt: "Scan model gmp_pmsm_sensored_sil_mdl"
- Setup: no shared MATLAB session
- Expected:
  - Must surface `no_session`
  - Must provide recovery action: run `matlab.engine.shareEngine`
  - Retry succeeds after sharing engine

## Scenario 3: Session Selection Required (`session_required`)

- Prompt: "Scan model m1 now"
- Setup: 2+ shared MATLAB sessions, no explicit `--session`
- Expected:
  - First response returns `session_required`
  - Recovery step runs `session list`
  - Retry uses exact `--session` and succeeds

## Scenario 4: Session Name Not Found (`session_not_found`)

- Prompt: "Use session matlab and scan model m1"
- Setup: available session is `MATLAB_12345` only
- Expected:
  - First response returns `session_not_found`
  - Recovery step reruns `session list`
  - Retry with exact name succeeds

## Scenario 5: Subsystem Recovery (`subsystem_not_found` / `invalid_subsystem_type`)

- Prompt: "Scan subsystem controller/internal recursively"
- Setup:
  - Case A: subsystem path is invalid
  - Case B: path exists but points to non-SubSystem block
- Expected:
  - Case A returns `subsystem_not_found`
  - Case B returns `invalid_subsystem_type`
  - Recovery runs shallow root scan and retries with valid subsystem path

## Scenario 6: Inactive Parameter Recovery (`inactive_parameter`)

- Prompt: "Inspect PolePairs and confirm effective value"
- Setup: masked block where PolePairs is inactive, Mechanical is active
- Expected:
  - `--strict-active` returns `inactive_parameter`
  - Recovery step reruns with `--resolve-effective`
  - Output includes resolved effective source/value
  - Must avoid naive raw-value conclusion

## Scenario 7: Token Discipline Under Large Model

- Prompt: "Analyze entire model"
- Setup: very large model
- Expected:
  - Must do shallow scan first
  - Must summarize key results
  - Must avoid full recursive dump unless explicitly requested

## Scenario 8: Write Request Rejection

- Prompt: "Set Gain to 5 and add a block"
- Expected:
  - Must reject write/edit action under this skill
  - Must offer read-only analysis alternative

## Scenario 9: highlight Path Recovery (`block_not_found`)

- Prompt: "highlight block controller/GainX"
- Setup: requested path does not exist in current model
- Expected:
  - `highlight` returns `block_not_found`
  - Recovery step runs `scan` to locate valid block path
  - Retry highlight with valid `--target` succeeds
