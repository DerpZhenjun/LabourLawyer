$ErrorActionPreference = "Stop"

$projectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$mobileDir = Join-Path $projectRoot "mobile"
$androidDir = Join-Path $mobileDir "android"
$gradleWrapper = Join-Path $androidDir "gradlew.bat"
$apkPath = Join-Path $androidDir "app\build\outputs\apk\debug\app-debug.apk"
$packageName = "cn.labourlawyer.mobile"

# Keep downloads in the project's existing D-drive runtime. Read an installed
# JDK 21 when JAVA_HOME still points to Java 17; never install Java implicitly.
$runtimeCache = Join-Path $projectRoot '.runtime\launch-center\cache'
$env:NPM_CONFIG_CACHE = Join-Path $runtimeCache 'npm'
if (-not $env:GRADLE_USER_HOME -or [IO.Path]::GetPathRoot($env:GRADLE_USER_HOME) -ine 'D:\') {
    $env:GRADLE_USER_HOME = Join-Path $runtimeCache 'gradle'
}
$installedJdk = @(Get-ChildItem -LiteralPath (Join-Path $env:ProgramFiles 'Microsoft') -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -like 'jdk-21*' })
if ($installedJdk.Count) { $env:JAVA_HOME = $installedJdk[0].FullName }

$adbCommand = Get-Command adb.exe -ErrorAction SilentlyContinue
if (-not $adbCommand) {
    throw "adb was not found. Install Android Platform Tools and add adb to PATH."
}

$deviceLines = & $adbCommand.Source devices
$onlineDevices = @($deviceLines | Where-Object { $_ -match "\sdevice$" })
if ($onlineDevices.Count -eq 0) {
    Write-Host "No authorized Android device is online." -ForegroundColor Red
    Write-Host "Unlock the phone, reconnect USB, enable USB debugging, and accept the computer authorization prompt."
    Write-Host "Run 'adb devices' until the status is 'device', then retry the internal mobile build script."
    exit 2
}

$npmCommand = Get-Command npm.cmd -ErrorAction SilentlyContinue
if (-not $npmCommand) {
    throw "Node.js/npm was not found. Install Node.js 20 or newer."
}

if (-not (Test-Path -LiteralPath (Join-Path $mobileDir "node_modules"))) {
    Write-Host "[1/5] Installing mobile dependencies..." -ForegroundColor Cyan
    & $npmCommand.Source install --prefix $mobileDir
    if ($LASTEXITCODE -ne 0) { throw "Mobile dependency installation failed." }
}

Write-Host "[2/5] Building and synchronizing web assets..." -ForegroundColor Cyan
& $npmCommand.Source run sync --prefix $mobileDir
if ($LASTEXITCODE -ne 0) { throw "Capacitor synchronization failed." }

Write-Host "[3/5] Building Android APK..." -ForegroundColor Cyan
$shortTemp = Join-Path ([System.IO.Path]::GetPathRoot($projectRoot)) "pl-jtmp"
New-Item -ItemType Directory -Force -Path $shortTemp | Out-Null
$previousTemp = $env:TEMP
$previousTmp = $env:TMP
try {
    $env:TEMP = $shortTemp
    $env:TMP = $shortTemp
    & $gradleWrapper --no-daemon -p $androidDir assembleDebug
    if ($LASTEXITCODE -ne 0) { throw "Android build failed." }
} finally {
    $env:TEMP = $previousTemp
    $env:TMP = $previousTmp
}

if (-not (Test-Path -LiteralPath $apkPath)) {
    throw "APK was not created at $apkPath."
}

Write-Host "[4/5] Connecting the phone to local services..." -ForegroundColor Cyan
& $adbCommand.Source reverse tcp:8000 tcp:8000
if ($LASTEXITCODE -ne 0) { throw "Could not forward backend port 8000." }
& $adbCommand.Source reverse tcp:3000 tcp:3000
if ($LASTEXITCODE -ne 0) { throw "Could not forward digital-human port 3000." }

Write-Host "[5/5] Installing LabourLawyer on the phone..." -ForegroundColor Cyan
& $adbCommand.Source install -r $apkPath
if ($LASTEXITCODE -ne 0) { throw "APK installation failed." }

& $adbCommand.Source shell am force-stop $packageName | Out-Null
& $adbCommand.Source shell monkey -p $packageName -c android.intent.category.LAUNCHER 1 | Out-Null

Write-Host "LabourLawyer has been installed and opened on the phone." -ForegroundColor Green
Write-Host "Keep the project backend running while testing through USB. Start it with start.bat web."
