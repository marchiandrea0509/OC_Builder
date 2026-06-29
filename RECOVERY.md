# Recovery / New Laptop Setup

If you are the next OpenClaw or LLM reading this on a fresh machine, do this in order:

1. Clone this repo and open `C:\Users\anmar\.openclaw\workspace-ocbuilder`.
2. Read, in order:
   - `AGENTS.md`
   - `SOUL.md`
   - `USER.md`
   - `PROJECT_STATE.md`
   - `SESSION_START.txt`
   - `TOOLS.md`
   - `HEARTBEAT.md`
   - `memory/SHARED_FROM_MAIN.md`
   - the latest `memory/YYYY-MM-DD.md` files
3. Verify the workspace with `git status` and `openclaw status`.
4. Restore any missing local tools or paths noted in `TOOLS.md`.
5. Treat `memory/` and `.openclaw/workspace-state.json` as part of the backup set.
6. Work only on this project unless explicitly redirected.
7. Do **not** restart/stop the OpenClaw gateway from a live chat session that depends on it.
8. After meaningful changes, update `PROJECT_STATE.md` and commit.

## Backup checklist

- `git add -A`
- `git status --short`
- `git commit -m "backup: update workspace recovery docs"`
- `git push origin master`

## What matters most here

- Project: OpenClaw tool building
- Goal: robust multi-step project workflow across dashboard and Telegram
- Safe default: keep replies short, keep docs current, preserve continuity
