Run the monthly workspace deep health audit and only report when attention is needed.

Do exactly this:
1. Run:
   `python -B C:\Users\anmar\.openclaw\workspace-ocbuilder\ops\maintenance\workspace_monthly_health.py --config C:\Users\anmar\.openclaw\workspace-ocbuilder\ops\git-sync\targets.json --policy C:\Users\anmar\.openclaw\workspace-ocbuilder\ops\maintenance\health_policy.json --json`
2. Parse the JSON result.
3. If `needsAttention` is false, reply with `NO_REPLY` only.
4. If `needsAttention` is true, reply with a concise health report in this shape:
   - `Workspace monthly health needs attention`
   - `Run: <yyyy-mm-dd HH:mm Berlin>`
   - one bullet per entry in `attention`
5. Do not add extra commentary.
6. If the script itself fails before producing JSON, reply with the first clear error line and keep it short.

Notes:
- This is a read-only audit; it does not modify repositories.
- It checks branch tracking, divergence, dirty working trees, and Git operation state.
- The job should stay quiet on normal runs.
