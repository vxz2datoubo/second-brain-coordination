$ErrorActionPreference = "Stop"

$desktop = [Environment]::GetFolderPath("Desktop")
$shell = New-Object -ComObject WScript.Shell

$items = @(
    @{
        Name = "Switch to DeepSeek V4 Pro.lnk"
        Script = "F:\aidanao\codex_siliconflow_proxy\Enable-Codex-DeepSeekV4Pro.ps1"
    },
    @{
        Name = "Switch to Default Model.lnk"
        Script = "F:\aidanao\codex_siliconflow_proxy\Disable-Codex-DeepSeekV4Pro.ps1"
    },
    @{
        Name = "Start DeepSeek Proxy.lnk"
        Script = "F:\aidanao\codex_siliconflow_proxy\Start-CodexSiliconFlowProxy.ps1"
    },
    @{
        Name = "Stop DeepSeek Proxy.lnk"
        Script = "F:\aidanao\codex_siliconflow_proxy\Stop-CodexSiliconFlowProxy.ps1"
    }
)

foreach ($item in $items) {
    $shortcutPath = Join-Path $desktop $item.Name
    $shortcut = $shell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
    $shortcut.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$($item.Script)`""
    $shortcut.WorkingDirectory = "F:\aidanao\codex_siliconflow_proxy"
    $shortcut.IconLocation = "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe,0"
    $shortcut.Save()
}

Write-Output "Desktop shortcuts created."
