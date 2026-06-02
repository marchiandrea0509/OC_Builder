param(
  [string]$TaskName = 'Battery Alarm Watcher',
  [int]$CheckIntervalMinutes = 10
)

$ErrorActionPreference = 'Stop'
$base = Split-Path -Parent $MyInvocation.MyCommand.Path
$watcher = Join-Path $base 'battery_alarm_watcher.ps1'

if (-not (Test-Path $watcher)) {
  throw "Watcher script not found: $watcher"
}

$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$watcher`" -CheckIntervalMinutes $CheckIntervalMinutes"
$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -MultipleInstances IgnoreNew

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Description 'Battery-mode alert watcher (beeps if laptop stays on battery too long).' -Force | Out-Null
Write-Host "Installed scheduled task: $TaskName"