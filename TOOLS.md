# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## What Goes Here

Things like:

- Camera names and locations
- SSH hosts and aliases
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Examples

```markdown
### Cameras

- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH

- home-server → 192.168.1.100, user: admin

### TTS

- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

Add whatever helps you do your job. This is your cheat sheet.

### OpenClaw gateway safety

- Never run `openclaw gateway restart` directly from a live Discord/Telegram/Control-UI conversation.
- Safe detached request path:
  - `powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\Users\anmar\.openclaw\workspace\scripts\request_safe_gateway_restart.ps1 -DelaySeconds 30 -Reason "<why>"`
- Dry-run check:
  - `powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\Users\anmar\.openclaw\workspace\scripts\request_safe_gateway_restart.ps1 -DryRun -Reason "test"`
- The detached runner writes state to `C:\Users\anmar\.openclaw\safe-gateway-restart-state.json` and logs to `C:\Users\anmar\.openclaw\logs\safe-gateway-restart.log`.
