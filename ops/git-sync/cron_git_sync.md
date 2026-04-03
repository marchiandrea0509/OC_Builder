Run the periodic workspace Git sync and only post to the dedicated Discord watchdog thread if attention is needed.

Do exactly this:
1. Run:
   `python -B C:\Users\anmar\.openclaw\workspace-ocbuilder\skills\openclaw-project-bootstrap\scripts\git_sync_workspaces.py --config C:\Users\anmar\.openclaw\workspace-ocbuilder\ops\git-sync\targets.json --json`
2. Parse the JSON result.
3. If `needsAttention` is false, reply with `NO_REPLY` only.
4. If `needsAttention` is true, build a concise failure report in this shape:
   - `Workspace Git sync needs attention`
   - `Run: <yyyy-mm-dd HH:mm Berlin>`
   - one bullet per entry in `attention`
5. Send that report to the existing Discord thread using the message tool:
   - action: `thread-reply`
   - channel: `discord`
   - threadId: `1489664601028034843`
6. After sending successfully, reply with `NO_REPLY` only.

Rules:
- Do not send success messages.
- Do not add extra commentary.
- If the script itself fails before producing JSON, send the first clear error line to the same thread and then reply `NO_REPLY`.
