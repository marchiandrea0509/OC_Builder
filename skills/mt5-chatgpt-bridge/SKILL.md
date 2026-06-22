---
name: mt5-chatgpt-bridge
description: Stage or send an MT5 LTH optimisation ZIP and prompt into an existing ChatGPT shared thread from the workspace browser. Use when the user wants to reuse the last GPT link or pass a new one, attach the latest ZIP, paste the analysis prompt, and optionally send immediately without a final confirmation.
---

# MT5 ChatGPT Bridge

Use this skill for the repeatable browser bridge that pushes an MT5 results ZIP into a specific ChatGPT thread.

## Default behavior

- Prefer the shared-thread URL passed in by the user.
- If no URL is provided, reuse the last URL stored in `ops/mt5-chatgpt-bridge/state.json`.
- If no ZIP path is provided, resolve it from the latest handoff file or the newest matching ZIP in the MT5 archive.
- Send immediately by default.
- Use `-StageOnly` only when the user explicitly wants the draft left unsent.

## Helper

Run `scripts/run_bridge.ps1`.

## Inputs

- `TargetUrl` — optional ChatGPT shared thread URL
- `ZipPath` — optional explicit ZIP path
- `ZipHandoffFile` — optional text file that contains the ZIP path
- `PromptPath` — optional prompt text file
- `StateFile` — optional override for the remembered last URL
- `-StageOnly` — attach and draft only; do not press Enter
- `-DryRun` — resolve inputs and print the plan without browser actions

## Workflow

1. Resolve the target URL.
2. Resolve the ZIP path.
3. Verify the ZIP exists.
4. Open or focus the target ChatGPT thread in Chrome.
5. Trigger the file picker and attach the ZIP.
6. Wait for the attachment chip to appear.
7. Paste the prompt.
8. Press Enter unless `-StageOnly` is set.
9. Save the URL and ZIP path to state.

## Safety

- Do not create a new ChatGPT chat unless the user explicitly provides a new thread URL.
- Do not wipe or replace existing conversation context.
- Stop if the target URL cannot be resolved.
- Stop if the ZIP cannot be found.
