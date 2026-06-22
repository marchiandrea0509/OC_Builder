$ws = New-Object -ComObject WScript.Shell
$url = 'https://chatgpt.com/g/g-p-686cb8060c819197588a7482ed9710/c/6a38d3cd-8fec-83ed-96de-8bd39cdf8805'
$p = Get-Process chrome | Where-Object { $_.MainWindowTitle -like '*Chrome*' } | Select-Object -First 1
if (-not $p) { throw 'Chrome window not found.' }
$ws.AppActivate($p.Id) | Out-Null
Start-Sleep -Milliseconds 500
$ws.SendKeys('^l')
Start-Sleep -Milliseconds 150
$ws.SendKeys($url)
Start-Sleep -Milliseconds 150
$ws.SendKeys('{ENTER}')
Start-Sleep -Seconds 8
