$ErrorActionPreference = 'Stop'
$zipPath = 'H:\My Drive\MT5_results_archive\LTH_limited_results_FIX55B_CORE_RANDOM_EXIT_BENCHMARK_OPT_20260621_201238.zip'
$promptPath = 'C:\Users\anmar\.openclaw\workspace-ocbuilder\mt5_lth_analysis_prompt.txt'
$url = 'https://chatgpt.com/share/6a3933a1-fe14-83ed-ab1e-12a83023a110'

if (-not (Test-Path $zipPath)) { throw "ZIP missing: $zipPath" }
if (-not (Test-Path $promptPath)) { throw "Prompt missing: $promptPath" }

$ws = New-Object -ComObject WScript.Shell
$proc = Get-Process chrome | Where-Object { $_.Id -eq 5544 -or $_.MainWindowTitle -like '*MT5 LTH Optimization Analysis*' } | Select-Object -First 1
if (-not $proc) { throw 'Could not find the target Chrome window.' }

$ws.AppActivate($proc.Id) | Out-Null
Start-Sleep -Milliseconds 700
$ws.SendKeys('^l')
Start-Sleep -Milliseconds 200
$ws.SendKeys($url)
Start-Sleep -Milliseconds 200
$ws.SendKeys('{ENTER}')
Start-Sleep -Seconds 10

Set-Clipboard -Path $zipPath
Start-Sleep -Milliseconds 300
$ws.SendKeys('^v')
Start-Sleep -Seconds 12

Set-Clipboard -Value (Get-Content $promptPath -Raw)
Start-Sleep -Milliseconds 300
$ws.SendKeys('^v')
Start-Sleep -Milliseconds 500
$ws.SendKeys('{ENTER}')
