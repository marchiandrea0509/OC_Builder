Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$proc = Get-Process chrome | Where-Object { $_.Id -eq 5544 } | Select-Object -First 1
if (-not $proc) { throw 'Chrome window not found.' }
$root = [System.Windows.Automation.AutomationElement]::FromHandle($proc.MainWindowHandle)
$walker = [System.Windows.Automation.TreeWalker]::ControlViewWalker
$child = $walker.GetFirstChild($root)
$i = 0
while ($child -and $i -lt 60) {
    $name = $child.Current.Name
    $ctype = $child.Current.ControlType.ProgrammaticName
    if ($name -or $ctype) { Write-Output ("{0} | {1}" -f $ctype, $name) }
    $child = $walker.GetNextSibling($child)
    $i++
}
