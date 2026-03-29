# Validation checklist

Use this checklist before reporting bootstrap success.

## Required checks

### Agent registration

- PASS: target agent id exists in `openclaw agents list --json`
- FAIL: target agent id is missing

### Workspace path match

- PASS: agent record points to the expected workspace path
- FAIL: agent record points somewhere else

### Workspace existence

- PASS: workspace directory exists on disk
- FAIL: workspace directory does not exist

### Continuity files

- PASS: `PROJECT_STATE.md` exists
- PASS: `SESSION_START.txt` exists
- WARN: file exists but is empty, placeholder-only, or clearly incomplete
- FAIL: required file is missing

### Discord prepare mode

- PASS: proposed guild/channel allowlist and route binding are complete and conflict-free
- WARN: patch is complete but depends on unresolved policy details such as mention behavior
- FAIL: ids are missing or the room already belongs to another agent

### Discord apply mode

- PASS: post-patch config contains the expected route and allowlist entries
- FAIL: patch failed or post-patch verification does not match the intended state

## Overall result rules

- `Overall: PASS` when every required check passes
- `Overall: WARN` when required checks pass but one or more non-blocking issues remain
- `Overall: FAIL` when any required check fails

## Report format

Use a short, explicit report:

- `Overall: PASS|WARN|FAIL`
- `Agent: <agentId>`
- `Workspace: <workspacePath>`
- `Discord: not requested | prepared | applied | failed`
- `Checks:`
  - `PASS: ...`
  - `WARN: ...`
  - `FAIL: ...`
- `Next: ...` only when action is still needed

## Be strict about these blockers

Do not claim success if any of these are unresolved:

- agent missing from CLI registration
- workspace mismatch
- requested Discord apply did not land correctly
- required continuity file missing
