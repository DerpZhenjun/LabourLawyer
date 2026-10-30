param([Parameter(Mandatory=$true)][ValidateSet('api','web')][string]$Service,[switch]$Restart)
$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$data=Join-Path $root '.runtime/production-readiness/site-data'
$python=Join-Path $root '.venv/Scripts/python.exe'
if (!(Test-Path -LiteralPath $python)) { throw 'Configure the project Python environment first.' }
$port=if ($Service -eq 'api') {8002} else {5175}
$connections=@(Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)
if ($connections.Count) {
 if ($Service -ne 'api' -or !$Restart) { throw "Port $port is already in use; no process was changed." }
 if (@($connections | Where-Object LocalAddress -notin @('127.0.0.1','::1')).Count) { throw 'Review listener is not loopback-only.' }
 $owners=@($connections.OwningProcess | Sort-Object -Unique)
 if ($owners.Count -ne 1) { throw 'Expected one review API listener.' }
 . (Join-Path $PSScriptRoot 'backend-process-ownership.ps1')
 $processes=@(Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,ExecutablePath,CommandLine,CreationDate)
 $owned=@(Get-OwnedBackendProcesses -Processes $processes -ListenerPid $owners[0] -ProjectRoot $root -Port 8002)
 foreach ($item in $owned) {
  $current=Get-CimInstance Win32_Process -Filter "ProcessId=$($item.ProcessId)" -ErrorAction SilentlyContinue
  if (!$current -or $current.CreationDate -ne $item.CreationDate -or $current.CommandLine -ne $item.CommandLine -or $current.ExecutablePath -ne $item.ExecutablePath) { throw 'Review process identity changed; no process was stopped.' }
 }
 foreach ($item in $owned) { Stop-Process -Id $item.ProcessId -ErrorAction SilentlyContinue }
 for ($attempt=0;$attempt -lt 20;$attempt++) { if (!(Get-NetTCPConnection -LocalPort 8002 -State Listen -ErrorAction SilentlyContinue)) { break }; Start-Sleep -Milliseconds 200 }
 if (Get-NetTCPConnection -LocalPort 8002 -State Listen -ErrorAction SilentlyContinue) { throw 'Review port is still in use; replacement not started.' }
}
$env:PYTHONUTF8='1'
Push-Location $root
try {
 if ($Service -eq 'api') {
  New-Item -ItemType Directory -Force -Path $data | Out-Null
  $env:LABOURLAWYER_DATA_DIR=$data
  $env:LABOURLAWYER_AUTH_DB=Join-Path $data 'auth.sqlite3'
  $env:LABOURLAWYER_REGIONAL_DB=Join-Path $data 'regional-guides.sqlite'
  $env:LABOURLAWYER_DIRECTORY_DB=Join-Path $data 'regional-directory.sqlite'
  $env:LABOURLAWYER_CORS_ORIGINS='http://127.0.0.1:5175'
  @'
from pathlib import Path
from contextlib import closing
import sqlite3,secrets,json,sys,os
root=Path.cwd();out=Path(os.environ['LABOURLAWYER_DATA_DIR'])
for name in ['regional-guides.sqlite','regional-directory.sqlite']:
 source=root/'backend/data'/name;destination=out/name
 if source.is_file() and not destination.exists():
  with closing(sqlite3.connect(source.as_uri()+'?mode=ro',uri=True)) as s,closing(sqlite3.connect(destination)) as d:s.backup(d)
sys.path.insert(0,str(root/'backend'))
from auth_store import AuthStore
store=AuthStore()
if not store.list_users():
 password=secrets.token_urlsafe(24);store.create_user('preview-admin',password,'admin')
 (out/'test-login.json').write_bytes(json.dumps({'username':'preview-admin','password':password}).encode())
print('Isolated test account ready; credentials saved privately in .runtime/production-readiness/site-data/test-login.json')
'@ | & $python -
  if ($LASTEXITCODE -ne 0) { throw 'Test data preparation failed.' }
  Push-Location (Join-Path $root 'backend')
  try { & $python -m uvicorn app:app --host 127.0.0.1 --port 8002 } finally { Pop-Location }
 } else {
  $env:VITE_API_BASE_URL='http://127.0.0.1:8002'
  Push-Location (Join-Path $root 'frontend')
  try { node node_modules/vite/bin/vite.js --host 127.0.0.1 --port 5175 --strictPort } finally { Pop-Location }
 }
 if ($LASTEXITCODE -ne 0) { throw 'Review service exited with an error.' }
} finally { Pop-Location }
