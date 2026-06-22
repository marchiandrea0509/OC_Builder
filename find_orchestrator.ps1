$ws = New-Object -ComObject WScript.Shell
$p = Get-Process chrome | Where-Object { $_.MainWindowTitle -like '*V3_MT5 LTH Euro Night*' } | Select-Object -First 1
if (-not $p) { throw 'Chrome window not found.' }
$ws.AppActivate($p.Id) | Out-Null
Start-Sleep -Milliseconds 500
$ws.SendKeys('^f')
Start-Sleep -Milliseconds 250
$ws.SendKeys('orchestrator')
Start-Sleep -Milliseconds 250
$ws.SendKeys('{ENTER}')
Start-Sleep -Seconds 2
