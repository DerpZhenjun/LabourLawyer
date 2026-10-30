$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'public-service-settings.ps1')
$folder=Join-Path ([IO.Path]::GetTempPath()) ('ll-service-'+[Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $folder | Out-Null
$setting=Join-Path $folder 'service-origins.json'
$original=$env:LABOURLAWYER_DIGITAL_URL
try {
    $env:LABOURLAWYER_DIGITAL_URL=$null
    if(Import-PublicServiceSettings $setting){throw 'Missing configuration must not guess a service'}
    [IO.File]::WriteAllText($setting,'{"digital":"http://192.168.110.81:8089/"}')
    if((Import-PublicServiceSettings $setting) -ne 'http://192.168.110.81:8089'){throw 'Configured LAN service was not loaded'}
    $env:LABOURLAWYER_DIGITAL_URL='https://digital.example.com'
    if((Import-PublicServiceSettings $setting) -ne 'https://digital.example.com'){throw 'Explicit environment must take precedence'}
    foreach($bad in @('http://@example.com','https://user:secret@example.com','http://public.example.com','http://127.1','http://127.0.0.1:0','http://127.0.0.1:65536','https://example.com/path','https://example.com?key=secret','https://example.com#fragment',"https://example.com`r`n")){
        $env:LABOURLAWYER_DIGITAL_URL=$bad;$rejected=$false
        try{Import-PublicServiceSettings $setting | Out-Null}catch{$rejected=$true}
        if(-not $rejected){throw 'Unsafe configured origin accepted'}
    }
    $env:LABOURLAWYER_DIGITAL_URL=$null
    [IO.File]::WriteAllText($setting,'{"digital":42}')
    $rejected=$false;try{Import-PublicServiceSettings $setting | Out-Null}catch{$rejected=$true}
    if(-not $rejected){throw 'Non-string settings accepted'}
    Write-Host 'PASS public service settings: absence, persistence, environment precedence and 11 invalid origins/shapes; no service or network operation'
}finally{
    $env:LABOURLAWYER_DIGITAL_URL=$original
    if(Test-Path -LiteralPath $setting){Remove-Item -LiteralPath $setting}
    Remove-Item -LiteralPath $folder
}
