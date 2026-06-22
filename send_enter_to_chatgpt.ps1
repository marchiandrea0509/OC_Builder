$ws = New-Object -ComObject WScript.Shell
$p = Get-Process chrome | Where-Object { $_.MainWindowTitle -like '*V3_MT5 LTH Euro Night*' } | Select-Object -First 1
if (-not $p) {
  $p = Get-Process chrome | Where-Object { $_.MainWindowTitle -like '*ChatGPT*' } | Select-Object -First 1
}
if ($p) {
  $ws.AppActivate($p.Id) | Out-Null
  Start-Sleep -Milliseconds 600
  $ws.SendKeys('{ENTER}')
  Write-Output ("Sent Enter to PID $($p.Id)")
} else {
  Write-Output 'No target window found'
}
