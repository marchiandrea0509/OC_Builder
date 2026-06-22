$ws = New-Object -ComObject WScript.Shell
$proc = Get-Process chrome | Where-Object { $_.Id -eq 5544 } | Select-Object -First 1
if (-not $proc) { throw 'Chrome window not found.' }
$ws.AppActivate($proc.Id) | Out-Null
Start-Sleep -Milliseconds 700
$ws.SendKeys('^+{TAB}')
Start-Sleep -Seconds 2
