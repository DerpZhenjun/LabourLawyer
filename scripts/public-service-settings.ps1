# Read public service addresses only. Validation reuses the API's pure parser;
# this helper never probes an address or starts an application/model service.
function Import-PublicServiceSettings([string]$SettingsPath,[string]$PythonExecutable=(Join-Path $PSScriptRoot '../.venv/Scripts/python.exe')) {
    $raw=$env:LABOURLAWYER_DIGITAL_URL
    if([string]::IsNullOrWhiteSpace($raw) -and (Test-Path -LiteralPath $SettingsPath)) {
        try {$settings=Get-Content -LiteralPath $SettingsPath -Raw -Encoding UTF8 | ConvertFrom-Json}
        catch {throw 'Public service settings are invalid; no service was started.'}
        if($settings.digital -isnot [string]){throw 'The public digital service address must be a string.'}
        $raw=$settings.digital
    }
    if([string]::IsNullOrWhiteSpace($raw)){return $null}
    if($raw -match '[\r\n]' -or $raw.Length -gt 300){throw 'Public service origin is invalid; no service was started.'}
    if(-not (Test-Path -LiteralPath $PythonExecutable)){throw 'Project Python is required to validate public service settings.'}
    $backend=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../backend'))
    $validated=$raw | & $PythonExecutable -c 'import sys; sys.path.insert(0,sys.argv[1]); from service_capabilities import service_origin; print(service_origin(sys.stdin.read().strip()))' $backend 2>$null
    if($LASTEXITCODE -ne 0 -or -not $validated){throw 'Public service origin is invalid; no service was started.'}
    $env:LABOURLAWYER_DIGITAL_URL=[string]$validated
    return [string]$validated
}
