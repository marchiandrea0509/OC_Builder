# Battery Alarm Watcher

What it does:
- checks whether the laptop is on battery
- waits until it has been on battery for > 2 minutes
- plays a 2-minute repeating alarm
- tries to unmute first if `nircmd.exe` is available

Install:
1. Open PowerShell as your user
2. Run:
   `powershell -NoProfile -ExecutionPolicy Bypass -File C:\Users\anmar\.openclaw\workspace-ocbuilder\ops\battery-alarm\install_battery_alarm_task.ps1`

Notes:
- The scheduled task starts at logon and runs hidden.
- Check interval defaults to 10 minutes.
- Mute override is best-effort, not guaranteed on every Windows setup.
