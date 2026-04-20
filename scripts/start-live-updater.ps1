$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir
$pythonExe = "python"
$updater = Join-Path $scriptDir "run_live_updater.py"
$logDir = Join-Path $repoRoot "logs"
$logFile = Join-Path $logDir "live-updater.log"

if (-not (Test-Path $updater)) {
    throw "Script introuvable: $updater"
}

if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
}

$args = @(
    "-u",
    $updater,
    "--interval", "30",
    "--repo-root", $repoRoot,
    "--sources-file", "data/competition_sources.json",
    "--club-keywords", "Seynod,0174246"
)

Push-Location $repoRoot
try {
    & $pythonExe @args *>> $logFile
}
finally {
    Pop-Location
}
