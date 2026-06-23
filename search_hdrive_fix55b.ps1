$root='H:\'
Get-ChildItem $root -Recurse -File -ErrorAction SilentlyContinue |
  Where-Object { $_.Name -match 'FIX55B|fix55b|FIX56|fix56' -or $_.FullName -match 'FIX55B|fix55b|FIX56|fix56' } |
  Select-Object FullName,Length,LastWriteTime | Format-Table -AutoSize
