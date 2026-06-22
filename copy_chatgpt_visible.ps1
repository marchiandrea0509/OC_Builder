$ws = New-Object -ComObject WScript.Shell
$p = Get-Process chrome | Where-Object { $_.MainWindowTitle -like '*V3_MT5 LTH Euro Night*' } | Select-Object -First 1
if (-not $p) { throw 'Chrome window not found.' }
$ws.AppActivate($p.Id) | Out-Null
Start-Sleep -Milliseconds 500
$ws.SendKeys('^a')
Start-Sleep -Milliseconds 200
$ws.SendKeys('^c')
Start-Sleep -Milliseconds 700
$text = Get-Clipboard -Raw
$path = 'C:\Users\anmar\.openclaw\workspace-ocbuilder\clipboard_dump.txt'
Set-Content -Path $path -Value $text -Encoding UTF8
$text | Select-String -Pattern 'FIX56|orchestrator|\.py' -AllMatches | ForEach-Object { $_.Line }
