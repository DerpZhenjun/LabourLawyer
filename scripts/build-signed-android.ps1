[CmdletBinding()]
param(
    [switch]$FunctionsOnly,
    [switch]$PrepareKeyOnly,
    [string]$SigningDirectory = (Join-Path $env:USERPROFILE '.labourlawyer/signing'),
    [string]$OutputDirectory,
    [string]$JavaHome = 'C:/Program Files/Microsoft/jdk-21.0.12.101-hotspot',
    [string]$AndroidSdk = 'D:/DevTools/Platforms/Android/Sdk',
    [string]$GradleHome = 'D:/DevTools/Caches/Gradle',
    [string]$TemporaryDirectory = 'D:/pl-jtmp',
    [string]$ExportBackupDirectory,
    [Security.SecureString]$BackupPassword
)
$ErrorActionPreference='Stop'
$projectRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$signingNames=@('LABOURLAWYER_ANDROID_KEYSTORE','LABOURLAWYER_ANDROID_KEY_ALIAS','LABOURLAWYER_ANDROID_STORE_PASSWORD','LABOURLAWYER_ANDROID_KEY_PASSWORD')
$expectedDebugCertificate='f3cc31f69511fcf58afe95c3e091aead2e8215497a39c9a32ad5c5242d7ef853'

function Assert-SigningEnvironment {
    $missing=@($signingNames | Where-Object { [string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable($_,'Process')) })
    if($missing.Count){throw ('Release signing environment is incomplete: '+($missing -join ', '))}
}
function Assert-PermanentSigningDirectory([string]$Directory,[string]$Checkout){
    $full=[IO.Path]::GetFullPath($Directory).TrimEnd('\','/')
    $workspace=[IO.Path]::GetFullPath($Checkout).TrimEnd('\','/')
    if(-not [IO.Path]::IsPathRooted($Directory) -or $full -ieq $workspace -or $full.StartsWith($workspace+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){
        throw 'The permanent signing identity must be outside the checkout'
    }
    if((Test-Path -LiteralPath $full) -and ((Get-Item -LiteralPath $full).Attributes -band [IO.FileAttributes]::ReparsePoint)){throw 'Signing directories must not be symlinks or junctions'}
}
function Set-PrivateSigningAcl([string]$Path){
    $currentOwner=(Get-Acl -LiteralPath $Path).GetOwner([Security.Principal.SecurityIdentifier]).Value
    if($currentOwner -ne [Security.Principal.WindowsIdentity]::GetCurrent().User.Value){throw 'Signing files must already belong to this user; existing ownership was not changed'}
    if(Test-PrivateSigningAcl $Path){return}
    $user=[Security.Principal.WindowsIdentity]::GetCurrent().User
    $system=[Security.Principal.SecurityIdentifier]::new('S-1-5-18')
    $isDirectory=(Get-Item -LiteralPath $Path).PSIsContainer
    $acl=if($isDirectory){[Security.AccessControl.DirectorySecurity]::new()}else{[Security.AccessControl.FileSecurity]::new()}
    $acl.SetOwner($user);$acl.SetAccessRuleProtection($true,$false)
    $inherit=if($isDirectory){[Security.AccessControl.InheritanceFlags]'ContainerInherit,ObjectInherit'}else{[Security.AccessControl.InheritanceFlags]::None}
    foreach($sid in @($user,$system)){
        $rule=[Security.AccessControl.FileSystemAccessRule]::new($sid,[Security.AccessControl.FileSystemRights]::FullControl,$inherit,[Security.AccessControl.PropagationFlags]::None,[Security.AccessControl.AccessControlType]::Allow)
        $acl.AddAccessRule($rule)
    }
    Set-Acl -LiteralPath $Path -AclObject $acl
}
function Test-PrivateSigningAcl([string]$Path){
    $user=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
    $acl=Get-Acl -LiteralPath $Path
    if(-not $acl.AreAccessRulesProtected -or $acl.GetOwner([Security.Principal.SecurityIdentifier]).Value -ne $user){return $false}
    $required=@{$user=$false;'S-1-5-18'=$false}
    foreach($rule in $acl.Access){
        $sid=$rule.IdentityReference.Translate([Security.Principal.SecurityIdentifier]).Value
        if($rule.AccessControlType -eq 'Allow' -and $sid -notin @($user,'S-1-5-18')){return $false}
        if($rule.AccessControlType -eq 'Allow' -and (($rule.FileSystemRights -band [Security.AccessControl.FileSystemRights]::FullControl) -eq [Security.AccessControl.FileSystemRights]::FullControl)){$required[$sid]=$true}
    }
    return ($required[$user] -and $required['S-1-5-18'])
}
function Get-PlainSigningPassword([string]$CredentialPath){
    try{$secure=ConvertTo-SecureString (Get-Content -LiteralPath $CredentialPath -Raw).Trim()}catch{throw 'Unable to unlock current-user signing credentials; existing identity was not replaced'}
    $pointer=[Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try{return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)}finally{[Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)}
}
function Invoke-SigningKeytool([string]$Keytool,[string[]]$Arguments,[string]$Log){
    & $Keytool @Arguments *>> $Log
    if($LASTEXITCODE -ne 0){throw 'Signing keytool operation failed; private log retained without printing credentials'}
}
function Get-CertificateSha256([string]$CertificateFile){
    $cert=[Security.Cryptography.X509Certificates.X509Certificate2]::new([IO.File]::ReadAllBytes($CertificateFile))
    try{$hash=[Security.Cryptography.SHA256]::Create();try{return ([BitConverter]::ToString($hash.ComputeHash($cert.RawData))).Replace('-','').ToLowerInvariant()}finally{$hash.Dispose()}}finally{$cert.Dispose()}
}
function Get-OrCreateSigningIdentity([string]$Directory,[string]$Keytool,[string]$Log){
    $store=Join-Path $Directory 'release-preview.p12';$credential=Join-Path $Directory 'release-preview.password.dpapi';$metadataFile=Join-Path $Directory 'release-preview.identity.json';$certificate=Join-Path $Directory 'release-preview.cer';$pending=Join-Path $Directory 'release-preview.pending.p12'
    $required=@($store,$credential,$metadataFile,$certificate)
    $present=@($required | Where-Object {Test-Path -LiteralPath $_})
    if(($present.Count -gt 0 -and $present.Count -ne $required.Count) -or (Test-Path -LiteralPath $pending)){throw 'Incomplete existing signing identity requires owner recovery; no key was replaced'}
    if(-not (Test-Path -LiteralPath $Directory)){New-Item -ItemType Directory -Path $Directory -Force | Out-Null}
    Set-PrivateSigningAcl $Directory
    $saved=@{};foreach($name in $signingNames){$saved[$name]=[Environment]::GetEnvironmentVariable($name,'Process')}
    $created=$present.Count -eq 0
    try{
        if($created){
            $backup=Join-Path $Directory 'backup-initial'
            if(Test-Path -LiteralPath $backup){throw 'Existing signing backup requires owner review; no identity was generated'}
            $bytes=[byte[]]::new(48);$random=[Security.Cryptography.RandomNumberGenerator]::Create();try{$random.GetBytes($bytes)}finally{$random.Dispose()}
            $plain=[Convert]::ToBase64String($bytes);[Array]::Clear($bytes,0,$bytes.Length)
            $secure=ConvertTo-SecureString $plain -AsPlainText -Force
            [IO.File]::WriteAllText($credential,(ConvertFrom-SecureString $secure),[Text.Encoding]::ASCII);Set-PrivateSigningAcl $credential
        }else{
            foreach($file in $required){if((Get-Item -LiteralPath $file).Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Signing identity files cannot be symlinks or junctions'};Set-PrivateSigningAcl $file}
            $metadata=Get-Content -LiteralPath $metadataFile -Raw | ConvertFrom-Json
            if($metadata.applicationId -ne 'cn.labourlawyer.mobile.release' -or $metadata.alias -ne 'labourlawyer-release-preview'){throw 'Existing identity metadata does not match this independent application'}
            if((Get-FileHash -LiteralPath $store -Algorithm SHA256).Hash.ToLowerInvariant() -ne $metadata.keystoreSha256 -or (Get-CertificateSha256 $certificate) -ne $metadata.certificateSha256){throw 'Existing signing identity hash mismatch; no key was rotated'}
            $plain=Get-PlainSigningPassword $credential
        }
        $env:LABOURLAWYER_ANDROID_STORE_PASSWORD=$plain;$env:LABOURLAWYER_ANDROID_KEY_PASSWORD=$plain
        if($created){
            Invoke-SigningKeytool $Keytool @('-genkeypair','-alias','labourlawyer-release-preview','-keyalg','RSA','-keysize','3072','-sigalg','SHA256withRSA','-validity','10000','-dname','CN=LabourLawyer Independent Release Preview','-storetype','PKCS12','-keystore',$pending,'-storepass:env','LABOURLAWYER_ANDROID_STORE_PASSWORD','-keypass:env','LABOURLAWYER_ANDROID_KEY_PASSWORD','-noprompt') $Log
            Invoke-SigningKeytool $Keytool @('-exportcert','-alias','labourlawyer-release-preview','-keystore',$pending,'-storetype','PKCS12','-storepass:env','LABOURLAWYER_ANDROID_STORE_PASSWORD','-file',$certificate) $Log
            $fingerprint=Get-CertificateSha256 $certificate
            if($fingerprint -eq $expectedDebugCertificate){throw 'Release identity must differ from the preserved debug identity'}
            Move-Item -LiteralPath $pending -Destination $store
            $metadata=[ordered]@{schemaVersion=1;applicationId='cn.labourlawyer.mobile.release';alias='labourlawyer-release-preview';createdAtUtc=[DateTime]::UtcNow.ToString('o');certificateSha256=$fingerprint;keystoreSha256=(Get-FileHash -LiteralPath $store -Algorithm SHA256).Hash.ToLowerInvariant();keyAlgorithm='RSA';keyBits=3072;keystoreType='PKCS12';credentialProtection='Windows DPAPI CurrentUser';debugCertificateDifferent=$true}
            [IO.File]::WriteAllText($metadataFile,($metadata|ConvertTo-Json),[Text.UTF8Encoding]::new($false))
            foreach($file in $required){Set-PrivateSigningAcl $file}
            New-Item -ItemType Directory -Path $backup | Out-Null;Set-PrivateSigningAcl $backup
            foreach($file in $required){$copy=Join-Path $backup ([IO.Path]::GetFileName($file));Copy-Item -LiteralPath $file -Destination $copy;Set-PrivateSigningAcl $copy}
        }else{
            $check=Join-Path ([IO.Path]::GetTempPath()) ('ll-public-cert-'+[Guid]::NewGuid().ToString('N')+'.cer')
            try{Invoke-SigningKeytool $Keytool @('-exportcert','-alias',$metadata.alias,'-keystore',$store,'-storetype','PKCS12','-storepass:env','LABOURLAWYER_ANDROID_STORE_PASSWORD','-file',$check) $Log;if((Get-CertificateSha256 $check) -ne $metadata.certificateSha256){throw 'Actual keystore certificate does not match permanent identity metadata'}}finally{if(Test-Path -LiteralPath $check){Remove-Item -LiteralPath $check}}
        }
        $backupDirectory=Join-Path $Directory 'backup-initial'
        if(-not (Test-Path -LiteralPath $backupDirectory)){
            New-Item -ItemType Directory -Path $backupDirectory | Out-Null;Set-PrivateSigningAcl $backupDirectory
            foreach($file in $required){$copy=Join-Path $backupDirectory ([IO.Path]::GetFileName($file));Copy-Item -LiteralPath $file -Destination $copy;Set-PrivateSigningAcl $copy}
        }
        $backupStore=Join-Path $Directory 'backup-initial/release-preview.p12' 
        if(-not (Test-Path -LiteralPath $backupStore) -or (Get-FileHash -LiteralPath $backupStore -Algorithm SHA256).Hash.ToLowerInvariant() -ne $metadata.keystoreSha256){throw 'Initial encrypted key backup is missing or changed; owner recovery is required'}
        return @{Metadata=$metadata;Created=$created;Store=$store;Credential=$credential}
    }finally{$plain=$null;foreach($name in $signingNames){[Environment]::SetEnvironmentVariable($name,$saved[$name],'Process')}}
}

if($FunctionsOnly){return}
if($env:OS -ne 'Windows_NT'){throw 'This signing workflow requires Windows CurrentUser DPAPI and NTFS ACLs'}
Assert-PermanentSigningDirectory $SigningDirectory $projectRoot
$keytool=Join-Path $JavaHome 'bin/keytool.exe'
if(-not (Test-Path -LiteralPath $keytool)){throw 'The explicitly configured JDK keytool is unavailable'}
if(-not $OutputDirectory){$OutputDirectory=Join-Path $projectRoot ('.runtime/signed-android/'+[DateTime]::UtcNow.ToString('yyyyMMddTHHmmss')+'-'+[Guid]::NewGuid().ToString('N').Substring(0,8))}
$OutputDirectory=[IO.Path]::GetFullPath($OutputDirectory)
if(Test-Path -LiteralPath $OutputDirectory){throw 'Use a new output directory; previous build evidence is not overwritten'}
New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
$identity=Get-OrCreateSigningIdentity $SigningDirectory $keytool (Join-Path $OutputDirectory 'keytool-private.log')
$summary=[ordered]@{applicationId=$identity.Metadata.applicationId;certificateSha256=$identity.Metadata.certificateSha256;keystoreSha256=$identity.Metadata.keystoreSha256;identityCreated=[bool]$identity.Created;credentialProtection='Windows DPAPI CurrentUser';initialEncryptedBackupVerified=$true;privateAclRestricted=(Test-PrivateSigningAcl $SigningDirectory);storePublished=$false}
if($ExportBackupDirectory){
    if(-not $BackupPassword){throw 'An owner-supplied SecureString backup password is required for portable export'}
    if(Test-Path -LiteralPath $ExportBackupDirectory){throw 'Portable backup destination must be new; no existing backup is overwritten'}
    Assert-PermanentSigningDirectory $ExportBackupDirectory $projectRoot
    New-Item -ItemType Directory -Path $ExportBackupDirectory -Force | Out-Null;Set-PrivateSigningAcl $ExportBackupDirectory
    $savedSource=[Environment]::GetEnvironmentVariable('LABOURLAWYER_ANDROID_STORE_PASSWORD','Process');$savedExport=[Environment]::GetEnvironmentVariable('LABOURLAWYER_ANDROID_EXPORT_PASSWORD','Process')
    try{
        $env:LABOURLAWYER_ANDROID_STORE_PASSWORD=Get-PlainSigningPassword $identity.Credential
        $pointer=[Runtime.InteropServices.Marshal]::SecureStringToBSTR($BackupPassword);try{$env:LABOURLAWYER_ANDROID_EXPORT_PASSWORD=[Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)}finally{[Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)}
        if($env:LABOURLAWYER_ANDROID_EXPORT_PASSWORD.Length -lt 16){throw 'Portable backup password must contain at least16characters'}
        $export=Join-Path $ExportBackupDirectory 'release-preview-portable.p12'
        Invoke-SigningKeytool $keytool @('-importkeystore','-srckeystore',$identity.Store,'-srcstoretype','PKCS12','-srcalias',$identity.Metadata.alias,'-srcstorepass:env','LABOURLAWYER_ANDROID_STORE_PASSWORD','-destkeystore',$export,'-deststoretype','PKCS12','-destalias',$identity.Metadata.alias,'-deststorepass:env','LABOURLAWYER_ANDROID_EXPORT_PASSWORD','-destkeypass:env','LABOURLAWYER_ANDROID_EXPORT_PASSWORD','-noprompt') (Join-Path $OutputDirectory 'keytool-private.log')
        Set-PrivateSigningAcl $export
        [IO.File]::WriteAllText((Join-Path $ExportBackupDirectory 'identity-public.json'),($identity.Metadata|ConvertTo-Json),[Text.UTF8Encoding]::new($false));Set-PrivateSigningAcl (Join-Path $ExportBackupDirectory 'identity-public.json')
        $summary['portableBackupExported']=$true
    }finally{[Environment]::SetEnvironmentVariable('LABOURLAWYER_ANDROID_STORE_PASSWORD',$savedSource,'Process');[Environment]::SetEnvironmentVariable('LABOURLAWYER_ANDROID_EXPORT_PASSWORD',$savedExport,'Process')}
    $summary|ConvertTo-Json
    return
}
if($PrepareKeyOnly){$summary|ConvertTo-Json;return}
$android=Join-Path $projectRoot 'mobile/android';$web=Join-Path $android 'app/src/main/assets/public/index.html'
if(-not (Test-Path -LiteralPath $web)){throw 'Synchronized Android web assets are required; run the reviewed client sync before this signing-only build'}
$names=@($signingNames)+@('JAVA_HOME','ANDROID_HOME','ANDROID_SDK_ROOT','GRADLE_USER_HOME','GRADLE_OPTS','TEMP','TMP')
$saved=@{};foreach($name in $names){$saved[$name]=[Environment]::GetEnvironmentVariable($name,'Process')}
$debugApk=Join-Path $android 'app/build/outputs/apk/debug/app-debug.apk';$debugBefore=if(Test-Path -LiteralPath $debugApk){(Get-FileHash -LiteralPath $debugApk -Algorithm SHA256).Hash}else{$null}
try{
    $env:LABOURLAWYER_ANDROID_KEYSTORE=$identity.Store;$env:LABOURLAWYER_ANDROID_KEY_ALIAS=$identity.Metadata.alias;$env:LABOURLAWYER_ANDROID_STORE_PASSWORD=Get-PlainSigningPassword $identity.Credential;$env:LABOURLAWYER_ANDROID_KEY_PASSWORD=$env:LABOURLAWYER_ANDROID_STORE_PASSWORD
    Assert-SigningEnvironment
    $env:JAVA_HOME=$JavaHome;$env:ANDROID_HOME=$AndroidSdk;$env:ANDROID_SDK_ROOT=$AndroidSdk;$env:GRADLE_USER_HOME=$GradleHome;$env:GRADLE_OPTS='-Xmx512m -Dorg.gradle.daemon=false -Dorg.gradle.workers.max=1';$env:TEMP=$TemporaryDirectory;$env:TMP=$TemporaryDirectory
    New-Item -ItemType Directory -Path $TemporaryDirectory -Force | Out-Null
    Push-Location $android
    try{& './gradlew.bat' '--no-daemon' '--no-configuration-cache' '--no-build-cache' '--max-workers=1' '-Pkotlin.compiler.execution.strategy=in-process' '-Dorg.gradle.jvmargs=-Xmx512m' ('-Djava.io.tmpdir='+$TemporaryDirectory) ':app:assembleRelease' *>> (Join-Path $OutputDirectory 'gradle-private.log');if($LASTEXITCODE -ne 0){throw 'Signed release build failed; see private Gradle log'}}finally{Pop-Location}
    $apk=Join-Path $android 'app/build/outputs/apk/release/app-release.apk'
    if(-not (Test-Path -LiteralPath $apk)){throw 'Gradle did not produce the expected signed release APK'}
    $tools=Join-Path $AndroidSdk 'build-tools/36.0.0'
    $signer=(& (Join-Path $tools 'apksigner.bat') verify --verbose --print-certs $apk 2>&1) -join "`n";if($LASTEXITCODE -ne 0){throw 'apksigner rejected the release APK'}
    $badging=(& (Join-Path $tools 'aapt.exe') dump badging $apk 2>&1) -join "`n";if($LASTEXITCODE -ne 0){throw 'aapt could not inspect the release APK'}
    if($badging -notmatch "package: name='cn\.labourlawyer\.mobile\.release'" -or $badging -match 'application-debuggable'){throw 'Release APK application identity/debuggable validation failed'}
    if($signer -notmatch ('certificate SHA-256 digest: '+[regex]::Escape($identity.Metadata.certificateSha256))){throw 'Release APK certificate does not match the permanent signing identity'}
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $zip=[IO.Compression.ZipFile]::OpenRead($apk)
    $webRoot=Join-Path $android 'app/src/main/assets/public'
    $webLines=[Collections.Generic.List[string]]::new()
    try{
        $configuration=$zip.GetEntry('assets/capacitor.config.json')
        if(-not $configuration){throw 'Signed APK is missing its native web configuration'}
        $reader=[IO.StreamReader]::new($configuration.Open());try{$nativeConfiguration=$reader.ReadToEnd()|ConvertFrom-Json}finally{$reader.Dispose()}
        if($nativeConfiguration.appId -ne 'cn.labourlawyer.mobile.release' -or $nativeConfiguration.android.webContentsDebuggingEnabled -ne $false){throw 'Signed variant must have its own app identity and disabled WebView debugging'}
        foreach($source in @(Get-ChildItem -LiteralPath $webRoot -Recurse -File | Sort-Object FullName)){
            $relative=[IO.Path]::GetRelativePath($webRoot,$source.FullName).Replace('\','/')
            $entry=$zip.GetEntry('assets/public/'+$relative)
            if(-not $entry){throw 'Signed APK is missing synchronized web assets'}
            $stream=$entry.Open();$hash=[Security.Cryptography.SHA256]::Create()
            try{$actual=([BitConverter]::ToString($hash.ComputeHash($stream))).Replace('-','').ToLowerInvariant()}finally{$hash.Dispose();$stream.Dispose()}
            if($actual -ne (Get-FileHash -LiteralPath $source.FullName -Algorithm SHA256).Hash.ToLowerInvariant()){throw 'Signed APK web bytes differ from synchronized build input'}
            $webLines.Add($relative+':'+$actual)
        }
        foreach($entry in $zip.Entries){
            if($entry.FullName -match '(?i)\.(p12|jks|keystore|dpapi)$'){throw 'Signing material must never be packaged into the APK'}
            if($entry.Length -gt 0){$reader=[IO.StreamReader]::new($entry.Open(),[Text.Encoding]::UTF8,$true);try{if($reader.ReadToEnd().Contains($env:LABOURLAWYER_ANDROID_STORE_PASSWORD)){throw 'A signing credential was found in packaged bytes'}}finally{$reader.Dispose()}}
        }
    }finally{$zip.Dispose()}
    $hash=[Security.Cryptography.SHA256]::Create();try{$webFingerprint=([BitConverter]::ToString($hash.ComputeHash([Text.Encoding]::UTF8.GetBytes(($webLines -join "`n"))))).Replace('-','').ToLowerInvariant()}finally{$hash.Dispose()}
    $summary['webContentsDebuggingEnabled']=$false;$summary['synchronizedWebFilesVerified']=$webLines.Count;$summary['webInputFingerprintSha256']=$webFingerprint;$summary['signingMaterialPackaged']=$false
    if($badging -match "versionCode='(\d+)' versionName='([^']+)'"){$summary['androidVersionCode']=[int]$matches[1];$summary['versionName']=$matches[2]}
    $debugAfter=if(Test-Path -LiteralPath $debugApk){(Get-FileHash -LiteralPath $debugApk -Algorithm SHA256).Hash}else{$null}
    if($debugBefore -ne $debugAfter){throw 'The preexisting debug APK changed during release build'}
    Copy-Item -LiteralPath $apk -Destination (Join-Path $OutputDirectory 'labourlawyer-independent-release-preview.apk')
    $summary['apkSha256']=(Get-FileHash -LiteralPath $apk -Algorithm SHA256).Hash.ToLowerInvariant();$summary['apkBytes']=(Get-Item -LiteralPath $apk).Length;$summary['releaseDebuggable']=$false;$summary['existingDebugApkUnchanged']=$true;$summary['validationOnly']=$true
    $summary|ConvertTo-Json | Set-Content -Encoding utf8 (Join-Path $OutputDirectory 'signed-apk-receipt.json')
    $summary|ConvertTo-Json
}finally{foreach($name in $names){[Environment]::SetEnvironmentVariable($name,$saved[$name],'Process')}}
