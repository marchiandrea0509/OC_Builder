---
name: openclaw-project-bootstrap
description: Bootstrap a new OpenClaw project agent with a dedicated workspace, continuity files, optional Discord room routing, and a clear validation report. Use when asked to create a reusable project setup workflow, spin up a new project-specific agent, verify agent registration and workspace paths, prepare or apply Discord channel binding for an existing room, or report PASS/WARN/FAIL bootstrap status.
---

# OpenClaw Project Bootstrap

Use this skill to create or verify a practical v2 OpenClaw project setup. Prefer standard OpenClaw mechanisms, keep automation light, and stop on ambiguous or conflicting state.

Use `scripts/bootstrap_project.py` for the mechanical parts when you want more deterministic execution. The script handles agent create/verify, continuity-file seeding, validation, and Discord **prepare/apply** handling. `apply` is explicit and guarded because it writes config and restarts the Gateway.

## Required inputs

Collect these before making changes:

- `projectName` — human-readable project name
- `purpose` — what the project agent is for

Optional inputs:

- `agentId` — override the derived id
- `workspacePath` — override the default workspace path
- `model` — only if the user explicitly wants one
- `discordGuildId` — required for Discord room setup
- `discordChannelId` — required for Discord room setup
- `discordAccountId` — default to `default`
- `discordMode` — `prepare` or `apply` (default to `prepare` unless the user explicitly wants config changed)
- `yes` / explicit confirmation flag — required for `apply` because it writes config and restarts the Gateway

## Operating rules

- Work inside the current workspace when creating this skill or related reusable assets.
- Use local OpenClaw docs first when command or config behavior is uncertain.
- Prefer `openclaw agents add ... --non-interactive` for agent creation.
- Do **not** use `openclaw setup --workspace <dir>` for project agents. That command updates `agents.defaults.workspace`, which is not appropriate for a per-project bootstrap flow.
- Use `gateway config.schema.lookup` on the relevant dot paths before config edits.
- Use `gateway config.patch` rather than full config replacement.
- Do not overwrite existing project continuity files unless the user asked.
- If a Discord room is already routed to a different agent, stop and ask.

## Workflow

### 1. Normalize the target

Derive a stable `agentId` from `projectName` when the user does not provide one.

Rules:

- lowercase
- letters, digits, hyphens only
- keep it short and stable
- avoid consecutive hyphens

Default workspace path:

- `~/.openclaw/workspace-<agentId>` unless `workspacePath` is provided

### 2. Inspect existing state

Run lightweight checks before writing anything:

- `openclaw agents list --json`
- filesystem check for the expected workspace path
- if Discord is requested, inspect current routing/config state before proposing changes

If the agent already exists:

- verify the configured workspace path matches the expected path
- if it mismatches, report `FAIL` and stop
- if it matches, switch to verify/seed mode instead of recreate mode

### 3. Create or verify the agent

For a more mechanical execution path, prefer `scripts/bootstrap_project.py` with the project inputs. It is the default helper for v2 bootstrap runs when local script execution is available.

If the agent does not exist, create it with the CLI:

```bash
openclaw agents add <agentId> --workspace <workspacePath> --non-interactive --json
```

Add `--model <id>` only when the user explicitly requested a model.

After creation, verify registration with:

```bash
openclaw agents list --json
```

Required outcome:

- the agent id appears in the list
- the listed workspace path equals the expected path

### 4. Create or verify continuity files

Create these files in the target workspace when missing:

- `PROJECT_STATE.md` from `assets/PROJECT_STATE.md`
- `SESSION_START.txt` from `assets/SESSION_START.txt`

Substitute placeholders with the current project values.

Behavior:

- if the file is missing, create it
- if the file exists, preserve it and validate its presence
- if the file exists but is clearly invalid or empty, report `WARN` unless the user asked for a rewrite

Optional note for the final report:

- mention whether standard OpenClaw workspace files such as `AGENTS.md`, `SOUL.md`, `USER.md`, `TOOLS.md`, and `IDENTITY.md` are present or missing
- note that `openclaw agents add` may already seed the standard workspace baseline; verify before creating replacements
- do not block v1 success on those files unless the user explicitly required full workspace seeding

### 5. Prepare or apply Discord room binding

Read `references/discord-room-binding.md` when Discord is in scope.

For a **specific Discord room**, prefer:

1. a Discord allowlist entry for the guild/channel
2. a top-level route binding matching that Discord channel id

Do **not** rely on `openclaw agents bind` for room-specific routing. That command is suitable for channel/account-level bindings, not for a single Discord room.

Behavior by mode:

- `prepare`: compute the exact patch and report it without writing config
- `apply`: merge the new route/allowlist into live config, patch it with `baseHash`, restart, and verify after restart

The companion script supports both `prepare` and `apply`. For `apply`, require explicit confirmation (`--yes`) because it patches config and restarts the Gateway.

When applying:

- preserve existing guild/channel config
- preserve unrelated bindings
- deduplicate identical bindings
- if the same Discord peer is already bound to another agent, stop and ask
- fetch current config first so array fields such as `bindings` are merged safely in memory before patching
- pass a human-readable `note` with `gateway config.patch`
- remember that `gateway config.patch` triggers a restart automatically
- verify the route and allowlist after the restart

### 6. Validate

Read `references/validation-checklist.md` before the final report.

Minimum validation checks:

- agent exists in `openclaw agents list --json`
- agent workspace path matches the expected path
- workspace directory exists on disk
- `PROJECT_STATE.md` exists
- `SESSION_START.txt` exists
- if Discord mode is `prepare`, the proposed patch is internally consistent
- if Discord mode is `apply`, the relevant config entries exist after patching

### 7. Report clearly

Use this exact structure in the final user-visible report:

- `Overall: PASS` when all required checks pass
- `Overall: WARN` when the core bootstrap works but non-blocking gaps remain
- `Overall: FAIL` when agent registration, workspace verification, or requested Discord routing fails

Then list:

- `Agent:` `<agentId>`
- `Workspace:` `<workspacePath>`
- `Discord:` `not requested | prepared | applied | failed`
- `Checks:` bullet list with `PASS`, `WARN`, or `FAIL` per item
- `Next:` only the minimum next action(s), if any

## Decision points

### Use this as v2

Prefer this skill when the user wants a practical, robust bootstrap for a project agent and the Discord room already exists.

### Escalate or stop when

Stop and ask when:

- the requested `agentId` already exists with a different workspace
- the requested workspace already belongs to another agent
- Discord room ids are missing for a requested room binding
- a Discord room is already routed to a different agent
- the user asks for deeper automation than the current workflow safely supports

## Resources

- `scripts/bootstrap_project.py` — mechanical helper for agent create/verify, continuity-file seeding, validation, and Discord prepare/apply handling
- `references/discord-room-binding.md` — exact v1 Discord room routing pattern
- `references/validation-checklist.md` — canonical PASS/WARN/FAIL checklist
- `assets/PROJECT_STATE.md` — continuity template
- `assets/SESSION_START.txt` — startup template
