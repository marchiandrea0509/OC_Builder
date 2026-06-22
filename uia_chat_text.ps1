Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$proc = Get-Process chrome | Where-Object { $_.MainWindowTitle -like '*V3_MT5 LTH Euro Night*' } | Select-Object -First 1
if (-not $proc) { throw 'Chrome window not found.' }
$root = [System.Windows.Automation.AutomationElement]::FromHandle($proc.MainWindowHandle)
$conds = @(
  (New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty, [System.Windows.Automation.ControlType]::Text)),
  (New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty, [System.Windows.Automation.ControlType]::Document)),
  (New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty, [System.Windows.Automation.ControlType]::Group)),
  (New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty, [System.Windows.Automation.ControlType]::Custom))
)
$or = New-Object System.Windows.Automation.OrCondition $conds
$els = $root.FindAll([System.Windows.Automation.TreeScope]::Descendants, $or)
$hits = @()
for ($i=0; $i -lt $els.Count; $i++) {
  $e = $els.Item($i)
  $n = $e.Current.Name
  if ($n -and ($n -match 'FIX55B|FIX56|orchestrator|\.py|Python')) {
    $hits += [pscustomobject]@{Type=$e.Current.ControlType.ProgrammaticName; Name=$n}
  }
}
$hits | Sort-Object Name -Unique | Format-Table -AutoSize
