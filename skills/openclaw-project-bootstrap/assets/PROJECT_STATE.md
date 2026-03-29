# PROJECT_STATE.md

## Project

- Name: {{PROJECT_NAME}}
- Purpose: {{PURPOSE}}
- Agent ID: {{AGENT_ID}}
- Workspace: {{WORKSPACE_PATH}}
- Bootstrap Status: {{BOOTSTRAP_STATUS}}
- Validation Result: {{VALIDATION_RESULT}}

## Bootstrap summary

- Created By: openclaw-project-bootstrap
- Created At: {{CREATED_AT_OR_DATE}}
- Last Verified: {{LAST_VERIFIED_OR_PENDING}}
- Standard Workspace Seed: {{STANDARD_SEED_STATUS}}
- Current Blocker: {{CURRENT_BLOCKER_OR_NONE}}

## Routing

- Discord Guild ID: {{DISCORD_GUILD_ID_OR_NA}}
- Discord Channel ID: {{DISCORD_CHANNEL_ID_OR_NA}}
- Discord Mode: {{DISCORD_MODE_OR_NA}}
- Discord Status: {{DISCORD_STATUS_OR_NA}}

## Bootstrap checklist

- [ ] Agent registered in OpenClaw CLI
- [ ] Workspace path verified
- [ ] Standard OpenClaw workspace files present or intentionally skipped
- [ ] PROJECT_STATE.md created
- [ ] SESSION_START.txt created
- [ ] Discord binding prepared, applied, or explicitly not requested
- [ ] Validation checklist passed

## Current focus

{{PURPOSE}}

## Decisions

- Keep this project agent focused on: {{PURPOSE}}
- Treat Discord `prepare` and `apply` as different states.
- Do not run `openclaw setup --workspace` for this project agent unless explicitly requested.

## Next actions

- {{NEXT_ACTION_1_OR_NONE}}
- {{NEXT_ACTION_2_OR_NONE}}

## Notes

- Created by the OpenClaw project bootstrap workflow.
- `openclaw agents add` may already seed the standard workspace baseline; verify it before creating extra files.
- Update this file when scope, routing, blockers, or validation status changes.
