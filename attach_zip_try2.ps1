Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$zipPath = 'H:\My Drive\MT5_results_archive\LTH_limited_results_FIX55B_CORE_RANDOM_EXIT_BENCHMARK_OPT_20260621_201238.zip'
$ws = New-Object -ComObject WScript.Shell
$proc = Get-Process chrome | Where-Object { $_.Id -eq 5544 } | Select-Object -First 1
if (-not $proc) { throw 'Chrome window not found.' }
$ws.AppActivate($proc.Id) | Out-Null
Start-Sleep -Milliseconds 700
[System.Windows.Forms.Cursor]::Position = New-Object System.Drawing.Point(760, 1015)
Start-Sleep -Milliseconds 200
Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class MouseClick2 {
  [DllImport("user32.dll")] public static extern void mouse_event(uint dwFlags, uint dx, uint dy, uint dwData, UIntPtr dwExtraInfo);
}
"@
[MouseClick2]::mouse_event(0x0002, 0, 0, 0, [UIntPtr]::Zero)
Start-Sleep -Milliseconds 80
[MouseClick2]::mouse_event(0x0004, 0, 0, 0, [UIntPtr]::Zero)
Start-Sleep -Milliseconds 800
Set-Clipboard -Path $zipPath
Start-Sleep -Milliseconds 400
$ws.SendKeys('^v')
Start-Sleep -Seconds 12
