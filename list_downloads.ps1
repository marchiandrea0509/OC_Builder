$dl = Join-Path $env:USERPROFILE 'Downloads'
Get-ChildItem $dl -File -ErrorAction SilentlyContinue |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 20 FullName,Name,Length,LastWriteTime |
  Format-Table -AutoSize
