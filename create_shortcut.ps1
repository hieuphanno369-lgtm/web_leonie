# Creates a desktop shortcut — double-click to launch Leonie in one terminal
$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$Desktop     = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = "$Desktop\Leonie.lnk"

$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)

$Shortcut.TargetPath       = "cmd.exe"
$Shortcut.Arguments        = "/k `"cd /d `"$ProjectDir`" && python run.py`""
$Shortcut.WorkingDirectory = $ProjectDir
$Shortcut.WindowStyle      = 1   # Normal window
$Shortcut.Description      = "Start Leonie (frontend + backend)"

# Use Edge icon so it looks distinct on desktop
$EdgePath = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
if (Test-Path $EdgePath) {
    $Shortcut.IconLocation = "$EdgePath,0"
}

$Shortcut.Save()
Write-Host "Shortcut created: $ShortcutPath" -ForegroundColor Green
Write-Host "Double-click 'Leonie' on your desktop to start everything." -ForegroundColor Cyan
