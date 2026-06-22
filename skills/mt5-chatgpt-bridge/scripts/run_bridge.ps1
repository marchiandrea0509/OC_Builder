param(
    [string]$TargetUrl,
    [string]$ZipPath,
    [string]$ZipHandoffFile = 'H:\My Drive\MT5_results_archive\_handoff\latest_completed_lth_zip.txt',
    [string]$PromptPath = 'C:\Users\anmar\.openclaw\workspace-ocbuilder\mt5_lth_analysis_prompt.txt',
    [string]$StateFile = 'C:\Users\anmar\.openclaw\workspace-ocbuilder\ops\mt5-chatgpt-bridge\state.json',
    [switch]$StageOnly,
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'

function Read-StateUrl {
    param([string]$Path)
    if (Test-Path $Path) {
        try {
            $obj = Get-Content $Path -Raw | ConvertFrom-Json
            if ($obj.lastTargetUrl) { return [string]$obj.lastTargetUrl }
        } catch { }
    }
    return $null
}

function Save-State {
    param(
        [string]$Path,
        [string]$Url,
        [string]$ResolvedZip,
        [string]$ResolvedPrompt
    )
    $dir = Split-Path $Path -Parent
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    [pscustomobject]@{
        lastTargetUrl = $Url
        lastZipPath   = $ResolvedZip
        lastPrompt    = $ResolvedPrompt
        updatedAtUtc  = (Get-Date).ToUniversalTime().ToString('o')
    } | ConvertTo-Json -Depth 3 | Set-Content -Path $Path -Encoding UTF8
}

function Resolve-Zip {
    param(
        [string]$ExplicitZip,
        [string]$HandoffFile
    )

    if ($ExplicitZip) { return $ExplicitZip }

    if (Test-Path $HandoffFile) {
        $candidate = (Get-Content $HandoffFile -Raw).Trim()
        if ($candidate) { return $candidate }
    }

    $root = 'H:\My Drive\MT5_results_archive'
    if (Test-Path $root) {
        $match = Get-ChildItem -Path $root -Recurse -File -Filter '*.zip' |
            Where-Object { $_.Name -like 'LTH_limited_results_*.zip' } |
            Sort-Object LastWriteTime -Descending |
            Select-Object -First 1
        if ($match) { return $match.FullName }
    }

    throw 'Could not resolve a ZIP path.'
}

function Get-ChromeProcess {
    $proc = Get-Process chrome -ErrorAction SilentlyContinue |
        Where-Object { $_.MainWindowHandle -ne 0 -and ($_.MainWindowTitle -like '*ChatGPT*' -or $_.MainWindowTitle -like '*Google Chrome*') } |
        Sort-Object CPU -Descending |
        Select-Object -First 1
    return $proc
}

function Focus-Chrome {
    param([System.Diagnostics.Process]$Proc)
    Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class WinFocus {
  [DllImport("user32.dll")] public static extern bool ShowWindowAsync(IntPtr hWnd, int nCmdShow);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
}
"@
    [WinFocus]::ShowWindowAsync($Proc.MainWindowHandle, 9) | Out-Null
    Start-Sleep -Milliseconds 300
    [WinFocus]::SetForegroundWindow($Proc.MainWindowHandle) | Out-Null
}

function Invoke-FilePicker {
    param([System.Diagnostics.Process]$Proc, [string]$ResolvedZip)

    $ws = New-Object -ComObject WScript.Shell
    $ws.AppActivate($Proc.Id) | Out-Null
    Start-Sleep -Milliseconds 700

    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing

    [System.Windows.Forms.Cursor]::Position = New-Object System.Drawing.Point(900, 1008)
    Start-Sleep -Milliseconds 150

    Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class MouseClickBridge {
  [DllImport("user32.dll")] public static extern void mouse_event(uint dwFlags, uint dx, uint dy, uint dwData, UIntPtr dwExtraInfo);
}
"@
    [MouseClickBridge]::mouse_event(0x0002, 0, 0, 0, [UIntPtr]::Zero)
    Start-Sleep -Milliseconds 80
    [MouseClickBridge]::mouse_event(0x0004, 0, 0, 0, [UIntPtr]::Zero)
    Start-Sleep -Milliseconds 900

    Set-Clipboard -Value ('script:document.querySelector("input[type=file]")?.click()')
    Start-Sleep -Milliseconds 150
    $ws.SendKeys('java')
    Start-Sleep -Milliseconds 100
    $ws.SendKeys('^v')
    Start-Sleep -Milliseconds 150
    $ws.SendKeys('{ENTER}')
    Start-Sleep -Seconds 5

    Set-Clipboard -Path $ResolvedZip
    Start-Sleep -Milliseconds 300
    $ws.SendKeys('%n')
    Start-Sleep -Milliseconds 300
    $ws.SendKeys('^v')
    Start-Sleep -Milliseconds 300
    $ws.SendKeys('{ENTER}')
    Start-Sleep -Seconds 10
}

function Paste-Prompt {
    param([System.Diagnostics.Process]$Proc, [string]$PromptText)
    $ws = New-Object -ComObject WScript.Shell
    $ws.AppActivate($Proc.Id) | Out-Null
    Start-Sleep -Milliseconds 700
    Set-Clipboard -Value $PromptText
    Start-Sleep -Milliseconds 250
    $ws.SendKeys('^v')
    Start-Sleep -Milliseconds 500
}

function Send-Message {
    param([System.Diagnostics.Process]$Proc)
    $ws = New-Object -ComObject WScript.Shell
    $ws.AppActivate($Proc.Id) | Out-Null
    Start-Sleep -Milliseconds 500
    $ws.SendKeys('{ENTER}')
    Start-Sleep -Seconds 3
}

$resolvedUrl = if ($TargetUrl) { $TargetUrl } else { Read-StateUrl -Path $StateFile }
if (-not $resolvedUrl) { throw 'TargetUrl was not provided and no previous URL was stored.' }

$resolvedZip = Resolve-Zip -ExplicitZip $ZipPath -HandoffFile $ZipHandoffFile
if (-not (Test-Path $resolvedZip)) { throw "ZIP missing: $resolvedZip" }
if (-not (Test-Path $PromptPath)) { throw "Prompt missing: $PromptPath" }
$promptText = Get-Content $PromptPath -Raw

if ($DryRun) {
    [pscustomobject]@{
        targetUrl   = $resolvedUrl
        zipPath     = $resolvedZip
        promptPath  = $PromptPath
        stageOnly   = [bool]$StageOnly
        stateFile   = $StateFile
    } | Format-List
    exit 0
}

$proc = Get-ChromeProcess
if (-not $proc) {
    Start-Process 'C:\Program Files\Google\Chrome\Application\chrome.exe' -ArgumentList $resolvedUrl | Out-Null
    Start-Sleep -Seconds 8
    $proc = Get-ChromeProcess
}
if (-not $proc) { throw 'Could not find or start a Chrome window.' }

Focus-Chrome -Proc $proc
$ws = New-Object -ComObject WScript.Shell
$ws.AppActivate($proc.Id) | Out-Null
Start-Sleep -Milliseconds 500
$ws.SendKeys('^l')
Start-Sleep -Milliseconds 200
$ws.SendKeys($resolvedUrl)
Start-Sleep -Milliseconds 200
$ws.SendKeys('{ENTER}')
Start-Sleep -Seconds 10

Invoke-FilePicker -Proc $proc -ResolvedZip $resolvedZip
Paste-Prompt -Proc $proc -PromptText $promptText

if (-not $StageOnly) {
    Send-Message -Proc $proc
}

Save-State -Path $StateFile -Url $resolvedUrl -ResolvedZip $resolvedZip -ResolvedPrompt $PromptPath
