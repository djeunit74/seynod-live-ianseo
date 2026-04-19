$ErrorActionPreference = "Stop"

param(
    [string]$TaskName = "Seynod-Live-Updater",
    [string]$RunAt = "07:00"
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$starter = Join-Path $scriptDir "start-live-updater.ps1"

if (-not (Test-Path $starter)) {
    throw "Script introuvable: $starter"
}

$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$starter`""

$trigger = New-ScheduledTaskTrigger -Daily -At $RunAt
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "Mise a jour IANSEO toutes les 30s pour le site Seynod" `
    -Force | Out-Null

Write-Host "Tache creee/mise a jour: $TaskName (demarrage quotidien a $RunAt)."
