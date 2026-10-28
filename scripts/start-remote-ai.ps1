param([string]$SshAlias,[int]$LocalPort=0)
$ErrorActionPreference='Stop'
$projectRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$runtime=Join-Path $projectRoot '.runtime\remote-ai'
New-Item -ItemType Directory -Force -Path $runtime | Out-Null
$settings=Join-Path $runtime 'settings.json'
if (Test-Path -LiteralPath $settings) {
    $config=Get-Content -LiteralPath $settings -Raw -Encoding UTF8 | ConvertFrom-Json
    if (-not $SshAlias) { $SshAlias=$config.sshAlias }
    if (-not $LocalPort) { $LocalPort=$config.localPort }
}
if (-not $SshAlias) { throw 'Configure .runtime/remote-ai/settings.json or pass -SshAlias. No local model was started.' }
if ($SshAlias -notmatch '^[A-Za-z0-9][A-Za-z0-9_.-]{0,100}$') { throw 'Use a saved SSH alias; shell expressions are not accepted.' }
if (-not $LocalPort) { $LocalPort=11435 }
if ($LocalPort -lt 1024 -or $LocalPort -gt 65535 -or $LocalPort -eq 11434) { throw 'Choose a separate SSH forwarding port; Windows Ollama port 11434 is forbidden.' }
$ssh=(Get-Command ssh.exe -ErrorAction Stop).Source
$connectionFile=Join-Path $runtime 'connection.json'
$forward="127.0.0.1:${LocalPort}:127.0.0.1:11434"
$current=$null
if (Test-Path -LiteralPath $connectionFile) { try { $current=Get-Content -LiteralPath $connectionFile -Raw | ConvertFrom-Json } catch {} }
$listeners=@(Get-NetTCPConnection -LocalPort $LocalPort -State Listen -ErrorAction SilentlyContinue)
$reuse=$false
if ($listeners.Count) {
    if ($current -and $current.ssh_alias -eq $SshAlias -and $current.local_port -eq $LocalPort) {
        $process=Get-CimInstance Win32_Process -Filter "ProcessId=$([int]$current.ssh_pid)" -ErrorAction SilentlyContinue
        $reuse=$process.Name -eq 'ssh.exe' -and $process.CommandLine.Contains($forward) -and @($listeners.OwningProcess) -contains $current.ssh_pid
    }
    if (-not $reuse) { throw "Port $LocalPort belongs to another process; no process was stopped." }
}
# This SSH request verifies the actual Ubuntu executable, stored model and
# loopback listener. It starts neither server nor inference, and sends no case data.
$probe=@'
import json,os,subprocess
from pathlib import Path
from urllib.request import urlopen
b=Path.home()/'SJL/Ollama'
pid=int((b/'serve.pid').read_text())
assert Path(os.readlink('/proc/'+str(pid)+'/exe'))==b/'bin/ollama','Unexpected server executable'
assert Path('/etc/os-release').read_text().find('ID=ubuntu')>=0,'Expected Ubuntu host'
def get(path):
 with urlopen('http://127.0.0.1:11434/api/'+path,timeout=10) as r:return json.load(r)
version=get('version')['version']
model=next(m for m in get('tags')['models'] if m['name']=='qwen3.8:27b')
assert model['details']['parameter_size'].startswith('27') and model['details']['quantization_level']=='Q4_K_M','Unexpected model'
record=json.loads((b/'logs/verification.json').read_text())
assert record['checks_passed'] is True and record['digest']==model['digest'] and record['root']==str(b),'Missing matching verified install'
listener=subprocess.check_output(['ss','-ltnpH','sport = :11434'],text=True)
assert '127.0.0.1:11434' in listener and ('pid='+str(pid)+',') in listener,'Listener does not belong to verified server'
print(json.dumps({'root':str(b),'version':version,'model':model['name'],'digest':model['digest']}))
'@
$verified=$probe | & $ssh -o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=10 $SshAlias 'python3 -'
if ($LASTEXITCODE -ne 0) { throw 'Ubuntu identity/model verification failed. No fallback to a Windows model.' }
$remote=$verified | ConvertFrom-Json
$started=$null
try {
    if (-not $reuse) {
        $arguments=@('-N','-T','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=10','-o','ExitOnForwardFailure=yes','-o','ServerAliveInterval=15','-o','ServerAliveCountMax=3','-L',$forward,$SshAlias)
        $started=Start-Process -FilePath $ssh -ArgumentList $arguments -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $runtime 'ssh.log') -RedirectStandardError (Join-Path $runtime 'ssh-error.log')
        $sshPid=$started.Id
    } else { $sshPid=[int]$current.ssh_pid }
    $endpoint="http://127.0.0.1:$LocalPort"
    $ready=$false
    for ($attempt=0;$attempt -lt 20;$attempt++) {
        if ($started -and $started.HasExited) { throw 'SSH forwarding exited. Read .runtime/remote-ai/ssh-error.log.' }
        try { $v=Invoke-RestMethod -Uri "$endpoint/api/version" -TimeoutSec 2; if ($v.version -eq $remote.version) { $ready=$true;break } } catch {}
        Start-Sleep -Milliseconds 250
    }
    if (-not $ready) { throw 'SSH tunnel did not become ready; no local model fallback.' }
    $record=[ordered]@{transport='ssh';endpoint=$endpoint;local_port=$LocalPort;ssh_pid=$sshPid;ssh_alias=$SshAlias;model='ollama/qwen3.8:27b';verified_remote=$true;remote=$remote;checked_at=(Get-Date).ToUniversalTime().ToString('o')}
    $record | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $connectionFile -Encoding UTF8
    $env:OLLAMA_API_BASE=$endpoint;$env:LABOURLAWYER_AI_TRANSPORT='ssh';$env:LABOURLAWYER_LLM_MODEL='ollama/qwen3.8:27b'
    Write-Host '[OK] Ubuntu remote AI connected through SSH. Windows model was not started.' -ForegroundColor Green
} catch {
    if ($started -and -not $started.HasExited) { Stop-Process -Id $started.Id -ErrorAction SilentlyContinue }
    throw
}
