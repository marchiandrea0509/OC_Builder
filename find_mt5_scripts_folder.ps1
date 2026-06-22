$roots = @('C:\Users\anmar','C:\Users','C:\')
foreach ($root in $roots) {
  if (-not (Test-Path $root)) { continue }
  Get-ChildItem $root -Directory -Recurse -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -eq 'MT5_scripts' } |
    Select-Object FullName
}
