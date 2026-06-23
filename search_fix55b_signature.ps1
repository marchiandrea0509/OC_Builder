$roots = @('C:\Users\anmar\.openclaw\workspace-tvflow','C:\Users\anmar\.openclaw\workspace-ocbuilder','C:\MT5_scripts')
$term = 'FIX55B_CORE_RANDOM_EXIT'
foreach ($root in $roots) {
  if (-not (Test-Path $root)) { continue }
  Get-ChildItem $root -Recurse -File -ErrorAction SilentlyContinue |
    Select-String -Pattern $term -SimpleMatch |
    ForEach-Object { "{0}:{1}: {2}" -f $_.Path, $_.LineNumber, $_.Line.Trim() }
}
