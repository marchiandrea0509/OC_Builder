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

function Refresh-ChatGptThread {
    param([System.Diagnostics.Process]$Proc)

    # Refresh after navigating to the target conversation so ChatGPT loads the latest
    # thread state before any file or prompt paste. This avoids stale-page branching.
    $ws = New-Object -ComObject WScript.Shell
    $ws.AppActivate($Proc.Id) | Out-Null
    Start-Sleep -Milliseconds 400
    $ws.SendKeys('{F5}')
    Start-Sleep -Seconds 6
}

function Set-BridgeClipboard {
    param(
        [string]$Value,
        [string]$Path
    )

    $lastError = $null
    for ($i = 1; $i -le 8; $i++) {
        try {
            if ($PSBoundParameters.ContainsKey('Path')) {
                Set-Clipboard -Path $Path
            } else {
                Set-Clipboard -Value $Value
            }
            return
        } catch {
            $lastError = $_
            Start-Sleep -Milliseconds (250 * $i)
        }
    }
    throw $lastError
}

function Click-Composer {
    param([System.Diagnostics.Process]$Proc)

    $ws = New-Object -ComObject WScript.Shell
    $ws.AppActivate($Proc.Id) | Out-Null
    Start-Sleep -Milliseconds 350

    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing

    $screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
    $clickX = [int]($screen.Width * 0.50)
    $clickY = [int]($screen.Height * 0.86)
    [System.Windows.Forms.Cursor]::Position = New-Object System.Drawing.Point($clickX, $clickY)
    Start-Sleep -Milliseconds 100

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
    Start-Sleep -Milliseconds 250
}

function Invoke-FilePicker {
    param([System.Diagnostics.Process]$Proc, [string]$ResolvedZip)

    # Fast/reliable path: ChatGPT accepts a file object pasted directly into the composer.
    # This avoids the fragile javascript: URL + Windows file picker sequence, which was slow
    # and could silently leave only the prompt staged without the ZIP attached.
    $ws = New-Object -ComObject WScript.Shell
    Click-Composer -Proc $Proc
    Set-BridgeClipboard -Path $ResolvedZip
    Start-Sleep -Milliseconds 250
    $ws.AppActivate($Proc.Id) | Out-Null
    Start-Sleep -Milliseconds 150
    $ws.SendKeys('^v')

    # Give ChatGPT time to create the upload chip. Small MT5 ZIPs usually chip in a few seconds;
    # this remains conservative enough for Drive-backed paths without wasting the old 15s+ picker path.
    Start-Sleep -Seconds 6
}

function Paste-Prompt {
    param([System.Diagnostics.Process]$Proc, [string]$PromptText)
    $ws = New-Object -ComObject WScript.Shell
    $ws.AppActivate($Proc.Id) | Out-Null
    Start-Sleep -Milliseconds 700
    Set-BridgeClipboard -Value $PromptText
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
Start-Sleep -Seconds 8
Refresh-ChatGptThread -Proc $proc

Invoke-FilePicker -Proc $proc -ResolvedZip $resolvedZip
Paste-Prompt -Proc $proc -PromptText $promptText

if (-not $StageOnly) {
    Send-Message -Proc $proc
}

Save-State -Path $StateFile -Url $resolvedUrl -ResolvedZip $resolvedZip -ResolvedPrompt $PromptPath
