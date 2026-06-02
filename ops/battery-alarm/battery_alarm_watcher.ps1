param(
  [int]$CheckIntervalMinutes = 10,
  [int]$BatteryThresholdSeconds = 120,
  [int]$AlarmDurationSeconds = 120,
  [int]$AlarmBeepIntervalSeconds = 5,
  [string]$StateFile = "$env:LOCALAPPDATA\OpenClaw\battery-alarm\state.json"
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms | Out-Null

$stateDir = Split-Path -Parent $StateFile
if (-not (Test-Path $stateDir)) { New-Item -ItemType Directory -Path $stateDir -Force | Out-Null }

function Get-PowerLineStatus {
  try {
    return [System.Windows.Forms.SystemInformation]::PowerStatus.PowerLineStatus.ToString()
  } catch {
    return 'Unknown'
  }
}

function Load-State {
  if (Test-Path $StateFile) {
    try {
      return (Get-Content $StateFile -Raw | ConvertFrom-Json)
    } catch {
      return [pscustomobject]@{}
    }
  }
  return [pscustomobject]@{}
}

function Save-State([object]$State) {
  $State | ConvertTo-Json -Depth 5 | Set-Content -Path $StateFile -Encoding UTF8
}

function Clear-State {
  if (Test-Path $StateFile) { Remove-Item $StateFile -Force }
}

function Try-Unmute {
  $nircmd = Get-Command nircmd.exe -ErrorAction SilentlyContinue
  if ($nircmd) {
    try { & $nircmd.Source mutesysvolume 0 | Out-Null } catch {}
    return
  }

  # Best-effort fallback: no-op if a helper isn't installed.
  # You can install AudioDeviceCmdlets later if you want a stricter unmute path.
}

function Start-Alarm {
  Try-Unmute
  $end = (Get-Date).AddSeconds($AlarmDurationSeconds)
  while ((Get-Date) -lt $end) {
    try { [console]::Beep(1200, 450) } catch {}
    try { [System.Media.SystemSounds]::Exclamation.Play() } catch {}
    Start-Sleep -Seconds $AlarmBeepIntervalSeconds
  }
}

while ($true) {
  $now = Get-Date
  $status = Get-PowerLineStatus
  $state = Load-State

  if ($status -eq 'Offline') {
    if (-not $state.batterySinceUtc) {
      $state | Add-Member -NotePropertyName batterySinceUtc -NotePropertyValue ($now.ToUniversalTime().ToString('o')) -Force
      $state | Add-Member -NotePropertyName alarmSent -NotePropertyValue $false -Force
      Save-State $state
    }

    try {
      $batterySince = [DateTimeOffset]::Parse($state.batterySinceUtc).UtcDateTime
      $elapsedSeconds = ($now.ToUniversalTime() - $batterySince).TotalSeconds
      if (-not $state.alarmSent -and $elapsedSeconds -ge $BatteryThresholdSeconds) {
        Start-Alarm
        $state.alarmSent = $true
        $state.lastAlarmUtc = $now.ToUniversalTime().ToString('o')
        Save-State $state
      }
    } catch {
      # If the state is malformed, reset and continue.
      Clear-State
    }
  } elseif ($status -eq 'Online') {
    if (Test-Path $StateFile) { Clear-State }
  }

  Start-Sleep -Seconds ($CheckIntervalMinutes * 60)
}