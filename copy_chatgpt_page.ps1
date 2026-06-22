$ws = New-Object -ComObject WScript.Shell
$p = Get-Process chrome | Where-Object { $_.Id -eq 5544 } | Select-Object -First 1
if (-not $p) { throw 'Chrome window not found.' }
$ws.AppActivate($p.Id) | Out-Null
Start-Sleep -Milliseconds 500
$ws.SendKeys('^a')
Start-Sleep -Milliseconds 200
$ws.SendKeys('^c')
Start-Sleep -Milliseconds 800
$text = Get-Clipboard -Raw
if (-not $text) { Write-Output 'CLIPBOARD_EMPTY'; exit 0 }
$path = 'C:\Users\anmar\.openclaw\workspace-ocbuilder\clipboard_dump.txt'
Set-Content -Path $path -Value $text -Encoding UTF8
$matches = $text | Select-String -Pattern 'FIX56|orchestrator|\.py' -AllMatches
if ($matches) { $matches | ForEach-Object { $_.Line } } else { Write-Output 'NO_MATCH' }
