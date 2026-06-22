Add-Type @"
using System;
using System.Text;
using System.Runtime.InteropServices;
public static class WinEnum {
  public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);
  [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);
  [DllImport("user32.dll")] public static extern int GetClassName(IntPtr hWnd, StringBuilder lpString, int nMaxCount);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr hWnd);
}
"@
$results = @()
[WinEnum]::EnumWindows({ param($hWnd, $lParam)
    if ([WinEnum]::IsWindowVisible($hWnd)) {
      $sb1 = New-Object System.Text.StringBuilder 512
      $sb2 = New-Object System.Text.StringBuilder 512
      [WinEnum]::GetWindowText($hWnd, $sb1, $sb1.Capacity) | Out-Null
      [WinEnum]::GetClassName($hWnd, $sb2, $sb2.Capacity) | Out-Null
      $title = $sb1.ToString()
      $class = $sb2.ToString()
      if ($title) { Write-Output ("{0} | {1}" -f $class, $title) }
    }
    return $true
  }, [IntPtr]::Zero) | Out-Null
