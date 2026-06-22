$ws = New-Object -ComObject WScript.Shell
$p = Get-Process chrome | Where-Object { $_.Id -eq 5544 } | Select-Object -First 1
if (-not $p) { throw 'Chrome window not found.' }
$ws.AppActivate($p.Id) | Out-Null
Start-Sleep -Milliseconds 600
$ws.SendKeys('{F5}')
Start-Sleep -Seconds 8
