Run the weekly workspace archive/cleanup pass and only report when attention is needed.

Do exactly this:
1. Run:
   `python -B C:\Users\anmar\.openclaw\workspace-ocbuilder\ops\maintenance\workspace_archive_cleanup.py --config C:\Users\anmar\.openclaw\workspace-ocbuilder\ops\git-sync\targets.json --policy C:\Users\anmar\.openclaw\workspace-ocbuilder\ops\maintenance\cleanup_policy.json --json`
2. Parse the JSON result.
3. If `needsAttention` is false, reply with `NO_REPLY` only.
4. If `needsAttention` is true, reply with a concise archive report in this shape:
   - `Workspace archive cleanup needs attention`
   - `Run: <yyyy-mm-dd HH:mm Berlin>`
   - one bullet per entry in `attention`
5. Do not add extra commentary.
6. If the script itself fails before producing JSON, reply with the first clear error line and keep it short.

Notes:
- The script archives only old untracked files from known disposable folders.
- Tracked files are skipped.
- The job should stay quiet on normal runs.
