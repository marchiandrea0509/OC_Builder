$roots = @('C:\Users\anmar\.openclaw','C:\MT5_scripts','C:\MT5_OPT_RUNTIME')
$patterns = @('FIX56','fix56','results folder','results_folder','results')
foreach ($root in $roots) {
  if (-not (Test-Path $root)) { continue }
  Get-ChildItem $root -Recurse -File -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -match 'FIX56|fix56' -or $_.Name -match 'FIX56|fix56' } |
    Select-Object FullName,Length,LastWriteTime
}
