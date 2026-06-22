Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$root = [System.Windows.Automation.AutomationElement]::RootElement
$cond = New-Object System.Windows.Automation.AndCondition(
  (New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty, [System.Windows.Automation.ControlType]::Window)),
  (New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::NameProperty, 'Open'))
)
$wins = $root.FindAll([System.Windows.Automation.TreeScope]::Children, $cond)
Write-Output ("Windows: {0}" -f $wins.Count)
for ($i=0; $i -lt $wins.Count; $i++) {
  $w = $wins.Item($i)
  Write-Output ("Window[{0}] {1}" -f $i, $w.Current.Name)
  $editCond = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty, [System.Windows.Automation.ControlType]::Edit)
  $edits = $w.FindAll([System.Windows.Automation.TreeScope]::Descendants, $editCond)
  Write-Output ("Edits: {0}" -f $edits.Count)
  for ($j=0; $j -lt [Math]::Min($edits.Count,10); $j++) {
    $e = $edits.Item($j)
    Write-Output (" - Edit[{0}] Name='{1}' Value='{2}'" -f $j, $e.Current.Name, ($e.GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern).Current.Value))
  }
}
