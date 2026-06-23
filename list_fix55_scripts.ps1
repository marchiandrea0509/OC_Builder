Get-ChildItem 'C:\MT5_scripts' -File | Where-Object { $_.Name -match 'FIX55' } | Select-Object Name,Length,LastWriteTime | Format-Table -AutoSize
