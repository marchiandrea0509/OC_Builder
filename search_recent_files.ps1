$since = (Get-Date).AddHours(-2)
Get-ChildItem (Join-Path $env:USERPROFILE 'Downloads') -File -ErrorAction SilentlyContinue |
  Where-Object { $_.LastWriteTime -ge $since -and ($_.Name -match 'FIX55B|MODULE|orchestrator|py') } |
  Sort-Object LastWriteTime -Descending |
  Select-Object FullName,Name,Length,LastWriteTime |
  Format-Table -AutoSize
