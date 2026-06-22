$ws = New-Object -ComObject WScript.Shell
$p = Get-Process chrome | Where-Object { $_.MainWindowTitle -like '*Chrome*' } | Select-Object -First 1
if (-not $p) { throw 'Chrome window not found.' }
$ws.AppActivate($p.Id) | Out-Null
Start-Sleep -Milliseconds 500
$ws.SendKeys('^f')
Start-Sleep -Milliseconds 200
$ws.SendKeys('FIX55B')
Start-Sleep -Milliseconds 200
$ws.SendKeys('{ENTER}')
Start-Sleep -Seconds 2
