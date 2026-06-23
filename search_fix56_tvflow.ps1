$root='C:\Users\anmar\.openclaw\workspace-tvflow'
Get-ChildItem $root -Recurse -File -ErrorAction SilentlyContinue |
  Where-Object { $_.Name -match 'FIX56|fix56' -or $_.FullName -match 'FIX56|fix56' } |
  Select-Object FullName,Length,LastWriteTime | Format-Table -AutoSize
