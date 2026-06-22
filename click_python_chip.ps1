Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$ws = New-Object -ComObject WScript.Shell
$p = Get-Process chrome | Where-Object { $_.MainWindowTitle -like '*V3_MT5 LTH Euro Night*' } | Select-Object -First 1
if (-not $p) { throw 'Chrome window not found.' }
$ws.AppActivate($p.Id) | Out-Null
Start-Sleep -Milliseconds 500
[System.Windows.Forms.Cursor]::Position = New-Object System.Drawing.Point(700, 230)
Start-Sleep -Milliseconds 150
Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class MouseClick6 {
  [DllImport("user32.dll")] public static extern void mouse_event(uint dwFlags, uint dx, uint dy, uint dwData, UIntPtr dwExtraInfo);
}
"@
[MouseClick6]::mouse_event(0x0002, 0, 0, 0, [UIntPtr]::Zero)
Start-Sleep -Milliseconds 80
[MouseClick6]::mouse_event(0x0004, 0, 0, 0, [UIntPtr]::Zero)
Start-Sleep -Seconds 3
