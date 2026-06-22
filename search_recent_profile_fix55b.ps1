$since = (Get-Date).AddHours(-3)
$roots = @('C:\Users\anmar','C:\Users\ASMLUST','C:\MT5_scripts')
$patterns = @('run_lth','FIX55B','FIX56','orchestrator','.py')
Get-ChildItem $roots -Recurse -File -ErrorAction SilentlyContinue |
  Where-Object { $_.LastWriteTime -ge $since } |
  Where-Object {
    $n = $_.Name
    $p = $_.FullName
    ($patterns | Where-Object { $n -match [regex]::Escape($_) -or $p -match [regex]::Escape($_) }).Count -gt 0
  } |
  Sort-Object LastWriteTime -Descending |
  Select-Object FullName,Name,Length,LastWriteTime |
  Format-Table -AutoSize
