$ws = New-Object -ComObject WScript.Shell
Set-Clipboard -Value (Get-Content 'C:\Users\anmar\.openclaw\workspace-ocbuilder\hello-world.txt' -Raw)
if ($ws.AppActivate(5544)) {
    Start-Sleep -Milliseconds 800
    $ws.SendKeys('^v')
    Start-Sleep -Milliseconds 200
    $ws.SendKeys('{ENTER}')
} else {
    Write-Output 'AppActivate failed'
}
