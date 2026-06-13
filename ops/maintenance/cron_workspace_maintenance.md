Run the periodic maintenance sweep across all active workspaces and only report when attention is needed.

Do exactly this:
1. Run:
   `python -B C:\Users\anmar\.openclaw\workspace-ocbuilder\ops\maintenance\workspace_maintenance.py --config C:\Users\anmar\.openclaw\workspace-ocbuilder\ops\git-sync\targets.json --policy C:\Users\anmar\.openclaw\workspace-ocbuilder\ops\maintenance\maintenance_policy.json --json`
2. Parse the JSON result.
3. If `needsAttention` is false, reply with `NO_REPLY` only.
4. If `needsAttention` is true, reply with a concise maintenance report in this shape:
   - `Workspace maintenance needs attention`
   - `Run: <yyyy-mm-dd HH:mm Berlin>`
   - one bullet per entry in `attention`
5. Do not add extra commentary.
6. If the script itself fails before producing JSON, reply with the first clear error line and keep it short.

Notes:
- The script checks every active workspace listed in the shared targets file.
- The script always refreshes the workspace index artifacts.
- Compaction only runs when the configured disk-usage threshold is reached.
- The job should stay quiet on normal runs.
