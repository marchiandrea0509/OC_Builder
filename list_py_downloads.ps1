$dl = Join-Path $env:USERPROFILE 'Downloads'
Get-ChildItem $dl -File -Filter '*.py' -ErrorAction SilentlyContinue |
  Sort-Object LastWriteTime -Descending |
  Select-Object FullName,Name,Length,LastWriteTime |
  Format-Table -AutoSize
