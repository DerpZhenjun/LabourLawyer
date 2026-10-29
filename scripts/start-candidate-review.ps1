param([Parameter(Mandatory=$true)][ValidateSet('api','web')][string]$Service)
# A deployment operator runs this script manually in two terminals. Do not invoke
# it as an automatic workaround for an execution-review rejection.
$ErrorActionPreference='Stop'
$projectRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$dataPath=Join-Path $projectRoot '.runtime\candidate-review-20261029-a'
$pythonPath=Join-Path $projectRoot '.venv\Scripts\python.exe'
$port=if($Service -eq 'api'){8001}else{5174}
if (!(Test-Path -LiteralPath $pythonPath)) { throw 'Project Python environment is missing.' }
if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) { throw "Port $port is occupied. No process was stopped." }
& $pythonPath (Join-Path $PSScriptRoot 'prepare-candidate-review.py')
if ($LASTEXITCODE -ne 0) { throw 'Candidate data verification failed. Existing data was not overwritten.' }
$values=@{
 LABOURLAWYER_DATA_DIR=$dataPath
 LABOURLAWYER_REGIONAL_DB=(Join-Path $dataPath 'regional-guides.sqlite')
 LABOURLAWYER_DIRECTORY_DB=(Join-Path $dataPath 'regional-directory.sqlite')
 LABOURLAWYER_CORS_ORIGINS='http://127.0.0.1:5174,http://localhost:5174'
 LABOURLAWYER_LLM_MODEL='disabled-for-candidate-review'
 VITE_API_BASE_URL='http://127.0.0.1:8001'
 PYTHONUTF8='1'
}
$previous=@{}
foreach($name in $values.Keys){$previous[$name]=[Environment]::GetEnvironmentVariable($name,'Process');[Environment]::SetEnvironmentVariable($name,$values[$name],'Process')}
Push-Location $projectRoot
try {
 Write-Host '[CANDIDATE] Isolated public test data only. Main services and models are not started or stopped.'
 Write-Host 'Keep this terminal open. Ctrl+C stops this candidate service.'
 if($Service -eq 'api'){
  & $pythonPath -m uvicorn app:app --app-dir (Join-Path $projectRoot 'backend') --host 127.0.0.1 --port 8001 --reload --reload-dir (Join-Path $projectRoot 'backend')
 }else{
  $nodePath=(Get-Command node -ErrorAction Stop).Source
  & $nodePath (Join-Path $projectRoot 'frontend\node_modules\vite\bin\vite.js') (Join-Path $projectRoot 'frontend') --host 127.0.0.1 --port 5174 --strictPort
 }
 if($LASTEXITCODE -ne 0){throw "Candidate service exited with code $LASTEXITCODE"}
}finally{
 Pop-Location
 foreach($name in $values.Keys){[Environment]::SetEnvironmentVariable($name,$previous[$name],'Process')}
}
