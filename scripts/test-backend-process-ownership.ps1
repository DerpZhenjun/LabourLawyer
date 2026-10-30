$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'backend-process-ownership.ps1')
$rootPath = 'D:\example\LabourLawyer'
$command = '"D:\example\LabourLawyer\.venv\Scripts\python.exe" -m uvicorn app:app --host 127.0.0.1 --port 8000'
$parent = [pscustomobject]@{ProcessId=100;ParentProcessId=50;ExecutablePath="$rootPath\.venv\Scripts\python.exe";CommandLine=$command}
$child = [pscustomobject]@{ProcessId=101;ParentProcessId=100;ExecutablePath='C:\Python311\python.exe';CommandLine=$command}
function Assert-Rejected($Items, $Target, $Name) {
    $rejected = $false
    try { Get-OwnedBackendProcesses -Processes $Items -ListenerPid $Target -ProjectRoot $rootPath | Out-Null } catch { $rejected = $true }
    if (!$rejected) { throw "FAIL $Name" }
    Write-Host "PASS $Name"
}
$owned = @(Get-OwnedBackendProcesses -Processes @($parent,$child) -ListenerPid 101 -ProjectRoot $rootPath)
if ($owned.Count -ne 2 -or $owned[0].ProcessId -ne 101 -or $owned[1].ProcessId -ne 100) { throw 'FAIL exact virtualenv child ancestry' }
Write-Host 'PASS exact virtualenv child ancestry'
Assert-Rejected @($child) 101 'unrelated Python listener'
$foreign = [pscustomobject]@{ProcessId=100;ParentProcessId=50;ExecutablePath='D:\example\LabourLawyer-other\.venv\Scripts\python.exe';CommandLine=$command}
Assert-Rejected @($foreign,$child) 101 'similar directory is not ownership'
$wrong = [pscustomobject]@{ProcessId=101;ParentProcessId=100;ExecutablePath='C:\Python311\python.exe';CommandLine=$command.Replace('8000','8001')}
Assert-Rejected @($parent,$wrong) 101 'different service port'
$wrong.CommandLine = $command.Replace('app:app','another:app')
Assert-Rejected @($parent,$wrong) 101 'different application'
$wrong.CommandLine = $command; $wrong.ParentProcessId = 101
Assert-Rejected @($parent,$wrong) 101 'cyclic ancestry'

$reviewParent = [pscustomobject]@{ProcessId=200;ParentProcessId=50;ExecutablePath="$rootPath\.venv\Scripts\python.exe";CommandLine=$command.Replace('8000','8002')}
$reviewChild = [pscustomobject]@{ProcessId=201;ParentProcessId=200;ExecutablePath='C:\Python311\python.exe';CommandLine=$command.Replace('8000','8002')}
$reviewOwned = @(Get-OwnedBackendProcesses -Processes @($reviewParent,$reviewChild) -ListenerPid 201 -ProjectRoot $rootPath -Port 8002)
if ($reviewOwned.Count -ne 2) { throw 'FAIL explicit review port ancestry' }
Write-Host 'PASS explicit review port ancestry'
