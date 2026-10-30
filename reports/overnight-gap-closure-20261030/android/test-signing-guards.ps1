$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
. (Join-Path $root 'scripts/build-signed-android.ps1') -FunctionsOnly
$checks=0
function Check([bool]$Passed,[string]$Message){if(-not $Passed){throw $Message};$script:checks++}
$previous=@{}; $temporary=$null
$names=@('LABOURLAWYER_ANDROID_KEYSTORE','LABOURLAWYER_ANDROID_KEY_ALIAS','LABOURLAWYER_ANDROID_STORE_PASSWORD','LABOURLAWYER_ANDROID_KEY_PASSWORD')
try{
 foreach($name in $names){$previous[$name]=[Environment]::GetEnvironmentVariable($name,'Process');[Environment]::SetEnvironmentVariable($name,$null,'Process')}
 $failed=$false
 try{Assert-SigningEnvironment}catch{$failed=$true;Check ($_.Exception.Message -notmatch 'PRIVATE_PASSWORD_SENTINEL') 'Missing-secret failure must not expose a value'}
 Check $failed 'Missing signing credentials must fail closed'
 $failed=$false
 try{Assert-PermanentSigningDirectory (Join-Path $root '.runtime/forbidden-signing') $root}catch{$failed=$true}
 Check $failed 'Signing keys must not be created within the checkout'
 $temporary=Join-Path ([IO.Path]::GetTempPath()) ('labourlawyer-signing-test-'+[Guid]::NewGuid().ToString('N'))
 New-Item -ItemType Directory -Path $temporary | Out-Null
 Set-PrivateSigningAcl $temporary
 [IO.File]::WriteAllText((Join-Path $temporary 'release-preview.p12'),'synthetic invalid partial keystore')
 Set-PrivateSigningAcl (Join-Path $temporary 'release-preview.p12')
 Check (Test-PrivateSigningAcl (Join-Path $temporary 'release-preview.p12')) 'Private file ACL must be protected without requesting audit privileges'
 Set-PrivateSigningAcl (Join-Path $temporary 'release-preview.p12')
 Check (Test-PrivateSigningAcl (Join-Path $temporary 'release-preview.p12')) 'Applying private ACLs twice must be safe and idempotent'
 $failed=$false
 try{Get-OrCreateSigningIdentity $temporary 'C:/Program Files/Microsoft/jdk-21.0.12.101-hotspot/bin/keytool.exe' (Join-Path $root '.runtime/overnight-android/test-keytool.log')}catch{$failed=$true}
 Check $failed 'A partial existing identity must be refused instead of silently replaced'
 Check ((Get-Content -LiteralPath (Join-Path $temporary 'release-preview.p12') -Raw) -eq 'synthetic invalid partial keystore') 'Existing key bytes must never be overwritten'
 Check (Test-PrivateSigningAcl $temporary) 'Private signing directory must allow only its owner and SYSTEM'
}finally{
 foreach($name in $names){[Environment]::SetEnvironmentVariable($name,$previous[$name],'Process')}
 if($temporary -and (Test-Path -LiteralPath $temporary)){
  $resolved=[IO.Path]::GetFullPath($temporary);$expected=[IO.Path]::GetFullPath([IO.Path]::GetTempPath())
  if(-not $resolved.StartsWith($expected,[StringComparison]::OrdinalIgnoreCase)){throw 'Test cleanup left the temporary directory boundary'}
  Remove-Item -LiteralPath $resolved -Recurse -Force
 }
}
Write-Output "PASS $checks signing guard/ACL checks; no real identity was created by this guard test"

