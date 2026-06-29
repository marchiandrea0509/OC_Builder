# Migration Guide

Use this document when moving OpenClaw workspace-ocbuilder to a new laptop.

## Goal

Preserve the workspace, restore the same working setup, and make sure the next OpenClaw or LLM can resume without guesswork.

## What to back up

Make sure these are included in GitHub:

- `AGENTS.md`
- `SOUL.md`
- `USER.md`
- `TOOLS.md`
- `PROJECT_STATE.md`
- `SESSION_START.txt`
- `HEARTBEAT.md`
- `RECOVERY.md`
- `MIGRATION_GUIDE.md`
- `memory/`
- `.openclaw/workspace-state.json`
- any workspace scripts in the repo

## Migration steps

1. Clone the GitHub repo on the new laptop.
2. Open the workspace folder.
3. Read these files first:
   - `AGENTS.md`
   - `SOUL.md`
   - `USER.md`
   - `PROJECT_STATE.md`
   - `SESSION_START.txt`
   - `TOOLS.md`
   - `RECOVERY.md`
4. Check `memory/` for the latest dated notes.
5. Run `git status`.
6. Run `openclaw status`.
7. Confirm the `origin` remote points to GitHub.
8. Restore any missing local tools, paths, or scripts listed in `TOOLS.md`.
9. Confirm the workspace files open correctly and the repo is clean.
10. If anything changed, update `PROJECT_STATE.md`, commit, and push.

## Emergency backup steps before shutdown

If the old machine is still alive:

- `git add -A`
- `git status --short`
- `git commit -m "backup: save migration docs"`
- `git push origin master`

If Git push fails, note the error in `memory/YYYY-MM-DD.md` and retry from a stable connection.

## Important operating rules

- Work only on this project unless explicitly redirected.
- Keep replies short unless detail is requested.
- Do not restart or stop the OpenClaw gateway from a live chat session that depends on it.
- Treat `memory/` as part of the continuity layer, not disposable scratch.

## After migration

- Verify the repo is synced with GitHub.
- Verify the next agent can read the docs in order.
- Verify `PROJECT_STATE.md` describes the current phase.
- Verify the workspace is usable without the old laptop.
