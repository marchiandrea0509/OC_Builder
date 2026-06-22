Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$ws = New-Object -ComObject WScript.Shell
$zipPath = 'H:\My Drive\MT5_results_archive\LTH_limited_results_FIX55B_CORE_RANDOM_EXIT_BENCHMARK_OPT_20260621_201238.zip'
Set-Clipboard -Value $zipPath
Start-Sleep -Milliseconds 300
[System.Windows.Forms.Cursor]::Position = New-Object System.Drawing.Point(420, 535)
Start-Sleep -Milliseconds 120
Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class MouseClick5 {
  [DllImport("user32.dll")] public static extern void mouse_event(uint dwFlags, uint dx, uint dy, uint dwData, UIntPtr dwExtraInfo);
}
"@
[MouseClick5]::mouse_event(0x0002, 0, 0, 0, [UIntPtr]::Zero)
Start-Sleep -Milliseconds 60
[MouseClick5]::mouse_event(0x0004, 0, 0, 0, [UIntPtr]::Zero)
Start-Sleep -Milliseconds 250
$ws.SendKeys('^v')
Start-Sleep -Milliseconds 300
$ws.SendKeys('{ENTER}')
Start-Sleep -Seconds 5
