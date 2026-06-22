$ErrorActionPreference = 'Stop'
$chromeTitle = 'ChatGPT - V3_MT5 LTH Euro Night - Google Chrome'
$zipPath = 'H:\My Drive\MT5_results_archive\LTH_limited_results_FIX55B_CORE_RANDOM_EXIT_BENCHMARK_OPT_20260621_201238.zip'
$promptPath = 'C:\Users\anmar\.openclaw\workspace-ocbuilder\mt5_lth_analysis_prompt.txt'

if (-not (Test-Path $zipPath)) { throw "ZIP missing: $zipPath" }
if (-not (Test-Path $promptPath)) { throw "Prompt missing: $promptPath" }

Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public static class Win32 {
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
  [DllImport("user32.dll")] public static extern bool ShowWindowAsync(IntPtr hWnd, int nCmdShow);
}
"@

$proc = Get-Process chrome | Where-Object { $_.MainWindowTitle -like '*V3_MT5 LTH Euro Night*' } | Select-Object -First 1
if (-not $proc) { throw 'Could not find the target Chrome window.' }
[Win32]::ShowWindowAsync($proc.MainWindowHandle, 9) | Out-Null
Start-Sleep -Milliseconds 300
[Win32]::SetForegroundWindow($proc.MainWindowHandle) | Out-Null
Start-Sleep -Seconds 1

$ws = New-Object -ComObject WScript.Shell
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$clickX = [int]($screen.Width * 0.5)
$clickY = [int]($screen.Height * 0.90)
[System.Windows.Forms.Cursor]::Position = New-Object System.Drawing.Point($clickX, $clickY)
Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class Mouse {
  [DllImport("user32.dll")] public static extern void mouse_event(uint dwFlags, uint dx, uint dy, uint dwData, UIntPtr dwExtraInfo);
}
"@
[Mouse]::mouse_event(0x0002, 0, 0, 0, [UIntPtr]::Zero)
Start-Sleep -Milliseconds 120
[Mouse]::mouse_event(0x0004, 0, 0, 0, [UIntPtr]::Zero)
Start-Sleep -Milliseconds 800

Set-Clipboard -Path $zipPath
Start-Sleep -Milliseconds 300
$ws.SendKeys('^v')
Start-Sleep -Seconds 12

Set-Clipboard -Value (Get-Content $promptPath -Raw)
Start-Sleep -Milliseconds 300
$ws.SendKeys('^v')
Start-Sleep -Milliseconds 500
