param([Parameter(Mandatory=$true)][string]$DataDirectory)
$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
. (Join-Path $PSScriptRoot 'backend-process-ownership.ps1')
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
$dataPath = if ([IO.Path]::IsPathRooted($DataDirectory)) { [IO.Path]::GetFullPath($DataDirectory) } else { [IO.Path]::GetFullPath((Join-Path $projectRoot $DataDirectory)) }
# An explicit, existing directory is required; never silently choose another case database.
if (!(Test-Path -LiteralPath $dataPath -PathType Container)) { throw 'The chosen existing data directory was not found.' }
if (!(Test-Path -LiteralPath $pythonPath)) { throw 'Project Python environment was not found.' }
. (Join-Path $PSScriptRoot 'public-service-settings.ps1')
Import-PublicServiceSettings (Join-Path $projectRoot '.runtime/service-origins.json') $pythonPath | Out-Null
$connections = @(Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue)
$owners = @($connections.OwningProcess | Sort-Object -Unique)
if ($owners.Count -ne 1) { throw 'Expected one existing backend on port 8000. No process was changed.' }
if (@($connections | Where-Object LocalAddress -notin @('127.0.0.1','::1')).Count) { throw 'The existing listener is not loopback-only. No process was changed.' }
$processes = @(Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,ExecutablePath,CommandLine,CreationDate)
$owned = @(Get-OwnedBackendProcesses -Processes $processes -ListenerPid $owners[0] -ProjectRoot $projectRoot)
# Connect only to the already installed Ubuntu service. This does not start a model.
& (Join-Path $PSScriptRoot 'start-remote-ai.ps1')
$env:LABOURLAWYER_DATA_DIR = $dataPath
$env:PYTHONUTF8 = '1'
# Validate the whole captured chain before stopping any process (including PID reuse).
foreach ($item in $owned) {
    $current = Get-CimInstance Win32_Process -Filter "ProcessId=$($item.ProcessId)" -ErrorAction SilentlyContinue
    if (!$current -or $current.CreationDate -ne $item.CreationDate -or $current.CommandLine -ne $item.CommandLine -or $current.ExecutablePath -ne $item.ExecutablePath) {
        throw 'Backend process identity changed. No process was stopped.'
    }
}
Write-Host "Restarting only this project's backend on port 8000. Existing data: $dataPath"
foreach ($item in $owned) { Stop-Process -Id $item.ProcessId -ErrorAction SilentlyContinue }
for ($attempt=0; $attempt -lt 20; $attempt++) {
    if (!(Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue)) { break }
    Start-Sleep -Milliseconds 250
}
if (Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue) { throw 'Port 8000 is still occupied. No replacement server was started.' }
Push-Location (Join-Path $projectRoot 'backend')
try {
    Write-Host 'Keep this window open. Press Ctrl+C to stop the backend.'
    & $pythonPath -m uvicorn app:app --host 127.0.0.1 --port 8000
    if ($LASTEXITCODE -ne 0) { throw "Backend exited with code $LASTEXITCODE" }
} finally { Pop-Location }
