Add-Type -AssemblyName System.Windows.Forms
$b = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
Write-Output ("{0}x{1}" -f $b.Width, $b.Height)
