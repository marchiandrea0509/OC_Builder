$ws = New-Object -ComObject WScript.Shell
$zipPath = 'H:\My Drive\MT5_results_archive\LTH_limited_results_FIX55B_CORE_RANDOM_EXIT_BENCHMARK_OPT_20260621_201238.zip'
Set-Clipboard -Value $zipPath
Start-Sleep -Milliseconds 300
$ws.SendKeys('{TAB}')
Start-Sleep -Milliseconds 300
$ws.SendKeys('^v')
Start-Sleep -Milliseconds 300
$ws.SendKeys('{ENTER}')
Start-Sleep -Seconds 4
