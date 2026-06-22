$ws = New-Object -ComObject WScript.Shell
$proc = Get-Process chrome | Where-Object { $_.Id -eq 5544 } | Select-Object -First 1
if (-not $proc) { throw 'Chrome window not found.' }
$ws.AppActivate($proc.Id) | Out-Null
Start-Sleep -Milliseconds 700
Set-Clipboard -Value 'javascript:document.querySelector("input[type=file]")?.click()'
Start-Sleep -Milliseconds 200
$ws.SendKeys('^l')
Start-Sleep -Milliseconds 200
$ws.SendKeys('^v')
Start-Sleep -Milliseconds 200
$ws.SendKeys('{ENTER}')
Start-Sleep -Seconds 5
