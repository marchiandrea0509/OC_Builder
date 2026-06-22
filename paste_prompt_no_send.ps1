$ws = New-Object -ComObject WScript.Shell
$promptPath = 'C:\Users\anmar\.openclaw\workspace-ocbuilder\mt5_lth_analysis_prompt.txt'
$proc = Get-Process chrome | Where-Object { $_.Id -eq 5544 } | Select-Object -First 1
if (-not $proc) { throw 'Chrome window not found.' }
$ws.AppActivate($proc.Id) | Out-Null
Start-Sleep -Milliseconds 700
Set-Clipboard -Value (Get-Content $promptPath -Raw)
Start-Sleep -Milliseconds 300
$ws.SendKeys('^v')
Start-Sleep -Seconds 3
