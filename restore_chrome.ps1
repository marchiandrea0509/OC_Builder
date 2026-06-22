Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class Win32Restore {
  [DllImport("user32.dll")] public static extern bool ShowWindowAsync(IntPtr hWnd, int nCmdShow);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
}
"@
$proc = Get-Process chrome | Where-Object { $_.Id -eq 5544 } | Select-Object -First 1
if (-not $proc) { throw 'Chrome window not found.' }
[Win32Restore]::ShowWindowAsync($proc.MainWindowHandle, 9) | Out-Null
Start-Sleep -Milliseconds 300
[Win32Restore]::SetForegroundWindow($proc.MainWindowHandle) | Out-Null
