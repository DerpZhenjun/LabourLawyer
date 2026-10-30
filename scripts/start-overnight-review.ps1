param([Parameter(Mandatory=$true)][ValidateSet('api','web')][string]$Service,[switch]$Restart)
$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$port=if($Service -eq 'api'){8003}else{5176}
$listeners=@(Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)
if($listeners.Count){
 if($Service -ne 'api' -or !$Restart){throw "Port $port is occupied; no process changed."}
 if(@($listeners|Where-Object LocalAddress -notin @('127.0.0.1','::1')).Count){throw 'Review listener is not loopback-only.'}
 $owners=@($listeners.OwningProcess|Sort-Object -Unique)
 if($owners.Count -ne 1){throw 'Expected one owned review API.'}
 . (Join-Path $PSScriptRoot 'backend-process-ownership.ps1')
 $processes=@(Get-CimInstance Win32_Process|Select-Object ProcessId,ParentProcessId,ExecutablePath,CommandLine,CreationDate)
 $owned=@(Get-OwnedBackendProcesses -Processes $processes -ListenerPid $owners[0] -ProjectRoot $root -Port 8003)
 foreach($item in $owned){
  $current=Get-CimInstance Win32_Process -Filter "ProcessId=$($item.ProcessId)"
  if(!$current -or $current.CreationDate -ne $item.CreationDate -or $current.CommandLine -ne $item.CommandLine -or $current.ExecutablePath -ne $item.ExecutablePath){throw 'Review process identity changed; no process stopped.'}
 }
 foreach($item in $owned){Stop-Process -Id $item.ProcessId -ErrorAction SilentlyContinue}
 for($attempt=0;$attempt -lt 20;$attempt++){if(!(Get-NetTCPConnection -LocalPort 8003 -State Listen -ErrorAction SilentlyContinue)){break};Start-Sleep -Milliseconds 200}
 if(Get-NetTCPConnection -LocalPort 8003 -State Listen -ErrorAction SilentlyContinue){throw 'Review port is still occupied.'}
}
$env:PYTHONUTF8='1'
$env:LABOURLAWYER_DATA_DIR=Join-Path $root '.runtime/overnight-gap-closure-20261030/review/private'
$env:LABOURLAWYER_AUTH_DB=Join-Path $env:LABOURLAWYER_DATA_DIR 'auth.sqlite3'
$env:LABOURLAWYER_REGIONAL_DB=Join-Path $root '.runtime/overnight-gap-closure-20261030/review/F-guides.sqlite'
$env:LABOURLAWYER_DIRECTORY_DB=Join-Path $root '.runtime/overnight-gap-closure-20261030/review/public/regional-directory.sqlite'
$env:LABOURLAWYER_CORS_ORIGINS='http://127.0.0.1:5176'
$env:LABOURLAWYER_LLM_MODEL='disabled-for-candidate-review'
$env:LABOURLAWYER_DIGITAL_URL='http://192.168.110.81:8089'
$collectorPointer=Join-Path $root '.runtime/overnight-gap-closure-20261030/review/collector-config-reference.json'
if(Test-Path -LiteralPath $collectorPointer){$env:LABOURLAWYER_COLLECTOR_CONFIG=(Get-Content -LiteralPath $collectorPointer -Raw|ConvertFrom-Json).path}
$env:VITE_API_BASE_URL='http://127.0.0.1:8003'
$env:VITE_DIGITAL_LAWYER_URL='http://192.168.110.81:8089'
$python=Join-Path $root '.venv/Scripts/python.exe'
Push-Location $root
try{
 if($Service -eq 'api'){
  @'
import os,sys,json,secrets,sqlite3
from pathlib import Path
from contextlib import closing
root=Path.cwd();sys.path.insert(0,str(root/'backend'))
from public_seed import bootstrap_public_data
out=root/'.runtime/overnight-gap-closure-20261030/review';out.mkdir(parents=True,exist_ok=True)
bootstrap_public_data(root,data_dir=out/'public')
source=root/'reports/overnight-gap-closure-20261030/localities/jiangsu-f/candidate-v2/guides.sqlite'
destination=Path(os.environ['LABOURLAWYER_REGIONAL_DB'])
if not source.is_file():raise RuntimeError('Verified F candidate database missing')
if not destination.exists():
 with closing(sqlite3.connect(source.as_uri()+'?mode=ro',uri=True)) as a,closing(sqlite3.connect(destination)) as b:a.backup(b)
from auth_store import AuthStore
store=AuthStore()
if not store.list_users():
 password=secrets.token_urlsafe(24);store.create_user('preview-admin',password,'admin')
 (out/'private/test-login.json').write_text(json.dumps({'username':'preview-admin','password':password}),encoding='utf8')
print('Isolated candidate ready; credentials remain in private runtime file.')
'@ | & $python -
  if($LASTEXITCODE -ne 0){throw 'Candidate preparation failed.'}
  $credential=Join-Path $env:LABOURLAWYER_DATA_DIR 'test-login.json'
  if(Test-Path -LiteralPath $credential){
   $sid=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
   & icacls.exe $credential /inheritance:r /grant:r "*$($sid):(F)" '*S-1-5-18:(F)' | Out-Null
   if($LASTEXITCODE -ne 0){throw 'Private credential ACL failed.'}
  }
  & $python -m uvicorn app:app --app-dir (Join-Path $root 'backend') --host 127.0.0.1 --port 8003
 }else{
  Push-Location (Join-Path $root 'frontend')
  try{node node_modules/vite/bin/vite.js --host 127.0.0.1 --port 5176 --strictPort}finally{Pop-Location}
 }
 if($LASTEXITCODE -ne 0){throw 'Isolated review service exited with an error.'}
}finally{Pop-Location}
