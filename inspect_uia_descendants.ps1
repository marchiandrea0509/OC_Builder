Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$proc = Get-Process chrome | Where-Object { $_.Id -eq 5544 } | Select-Object -First 1
if (-not $proc) { throw 'Chrome window not found.' }
$root = [System.Windows.Automation.AutomationElement]::FromHandle($proc.MainWindowHandle)
$cond = New-Object System.Windows.Automation.OrCondition(
    (New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty, [System.Windows.Automation.ControlType]::Button)),
    (New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty, [System.Windows.Automation.ControlType]::Edit)),
    (New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty, [System.Windows.Automation.ControlType]::MenuItem))
)
$all = $root.FindAll([System.Windows.Automation.TreeScope]::Descendants, $cond)
for ($i=0; $i -lt [Math]::Min(200, $all.Count); $i++) {
    $e = $all.Item($i)
    $name = $e.Current.Name
    $ctype = $e.Current.ControlType.ProgrammaticName
    if ($name -or $ctype) { Write-Output ("{0} | {1}" -f $ctype, $name) }
}
