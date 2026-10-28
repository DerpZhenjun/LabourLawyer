param(
    [Parameter(Mandatory=$true)][string]$Action,
    [switch]$DryRun,
    [string]$Province,
    [string]$Question,
    [string]$Batch,
    [switch]$Plain
)
$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$actions = Get-Content (Join-Path $PSScriptRoot 'actions.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$selected = @($actions | Where-Object { $_.id -eq $Action })
if ($selected.Count -ne 1) { throw "未知入口：$Action" }
if ($DryRun) {
    Write-Host ("[仅查看] {0}: {1}" -f $selected[0].title, $selected[0].steps)
    Write-Host "项目目录：$root"
    exit 0
}
# All child processes inherit these D-drive cache and temporary directories.
if ([IO.Path]::GetPathRoot($root) -ine 'D:\') { throw '本启动中心要求项目在 D 盘，避免下载到 C 盘。' }
$runtime = Join-Path $root '.runtime\launch-center'
$cache = Join-Path $runtime 'cache'
$temp = Join-Path $runtime 'temp'
$logs = Join-Path $runtime 'logs'
foreach ($dir in @($cache,$temp,$logs)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
foreach ($name in @('TEMP','TMP','TMPDIR')) { [Environment]::SetEnvironmentVariable($name,$temp,'Process') }
$cacheNames = @{
    UV_CACHE_DIR='uv'; UV_PYTHON_INSTALL_DIR='uv-python'; UV_TOOL_DIR='uv-tools'; UV_TOOL_BIN_DIR='uv-bin'
    PIP_CACHE_DIR='pip'; NPM_CONFIG_CACHE='npm'; NODE_COMPILE_CACHE='node'; GRADLE_USER_HOME='gradle'
    ELECTRON_CACHE='electron'; ELECTRON_BUILDER_CACHE='electron-builder'; PLAYWRIGHT_BROWSERS_PATH='playwright'
    HF_HOME='huggingface'; HF_HUB_CACHE='huggingface\hub'; HF_XET_CACHE='huggingface\xet'; TORCH_HOME='torch'
}
foreach ($name in $cacheNames.Keys) { [Environment]::SetEnvironmentVariable($name,(Join-Path $cache $cacheNames[$name]),'Process') }
$env:PYTHONUNBUFFERED='1'; $env:PYTHONUTF8='1'; $env:PYTHONIOENCODING='utf-8'
$config = @{}
$configPath = Join-Path $PSScriptRoot 'settings.local.json'
if (Test-Path $configPath) {
    $json = Get-Content $configPath -Raw -Encoding UTF8 | ConvertFrom-Json
    foreach ($property in $json.PSObject.Properties) { $config[$property.Name]=$property.Value }
}
$python = Join-Path $root '.venv\Scripts\python.exe'
$authorPython = $python
if ($config['renderPython']) { $authorPython = $config['renderPython'] }
else {
    $bundled = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
    if (Test-Path $bundled) { $authorPython = $bundled }
}
if ($config['openclawCommand']) {
    if (!(Test-Path $config['openclawCommand'])) { throw 'openclawCommand 指定的程序不存在。' }
    $env:PATH=(Split-Path $config['openclawCommand'])+';'+$env:PATH
} elseif (Test-Path 'D:\OpenClaw\npm-global\openclaw.cmd') { $env:PATH='D:\OpenClaw\npm-global;'+$env:PATH }
if ($config['androidSerial']) { $env:ANDROID_SERIAL=$config['androidSerial'] }
if ($config['pdfToPpm']) { $env:LABOURLAWYER_PDFTOPPM=$config['pdfToPpm'] }
else {
    $poppler = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\native\poppler\Library\bin\pdftoppm.exe'
    if (Test-Path $poppler) { $env:LABOURLAWYER_PDFTOPPM=$poppler }
}
function Run([string]$Exe, [string[]]$Arguments) {
    Write-Host ("`n>>> {0} {1}" -f $Exe, ($Arguments -join ' ')) -ForegroundColor Cyan
    & $Exe @Arguments
    if ($LASTEXITCODE -ne 0) { throw "执行失败（退出码 $LASTEXITCODE）：$Exe；详见本次日志。" }
}
function Python([string]$Script, [string[]]$Arguments=@()) {
    if (!(Test-Path $python)) { throw '缺少项目 .venv。请在项目根目录运行 start.bat web 初始化依赖。' }
    Work $python $Script $Arguments
}
function RenderPython([string]$Script, [string[]]$Arguments=@()) {
    if (!(Test-Path $authorPython)) { throw '缺少渲染 Python。请在 settings.local.json 配置已有的 Python（需要 Pillow 和 python-docx）。' }
    Work $authorPython $Script $Arguments
}
function Work([string]$WorkerPython,[string]$Script,[string[]]$Arguments=@()) {
    $visual=@('scripts\acquire_templates.py','scripts\acquire_province_catalog.py','scripts\audit_official_portals.py',
        'scripts\refresh-province-experiences.py','scripts\openclaw-acquire-guides.py','scripts\review-province-reports.py',
        'scripts\validate_acquired_templates.py','scripts\audit_generated_documents.py','scripts\launch_center_support.py')
    if ($Script -in $visual) {
        $displayPython=if (Test-Path $python) { $python } else { $WorkerPython }
        $displayArgs=@((Join-Path $root 'scripts\terminal-dashboard.py'),'--title',$selected[0].label)
        if ($Plain) { $displayArgs+='--plain' }
        Run $displayPython ($displayArgs+@('--',$WorkerPython,(Join-Path $root $Script))+$Arguments)
    } else { Run $WorkerPython (@((Join-Path $root $Script))+$Arguments) }
}
function StartWeb([switch]$Browser, [switch]$Digital) {
    $argsList=@('-NoProfile','-ExecutionPolicy','Bypass','-File',(Join-Path $root 'scripts\start-web.ps1'))
    if (!$Browser) { $argsList+='-NoBrowser' }
    if ($Digital) { $argsList+='-WithDigitalHuman' } else { $argsList+='-WithoutDigitalHuman' }
    Run 'powershell.exe' $argsList
}
function CheckVision {
    Python 'scripts\launch_center_support.py' @('model-check')
}
function CheckAndroid {
    $adb = Get-Command adb.exe -ErrorAction SilentlyContinue
    if (!$adb) { throw '找不到 adb。请把已有 Android SDK platform-tools 加入 PATH；启动中心不会自动下载 SDK。' }
    $devices = @(& $adb.Source devices | Where-Object { $_ -match '^\S+\s+device$' })
    if ($env:ANDROID_SERIAL) {
        if (!($devices | Where-Object { $_ -match ('^'+[regex]::Escape($env:ANDROID_SERIAL)+'\s') })) { throw '指定 Android 设备未连接或未授权 USB 调试。' }
    } elseif ($devices.Count -ne 1) { throw '请连接且授权一台 Android 设备；多台设备时在 settings.local.json 填 androidSerial。' }
}
$logFile = Join-Path $logs ((Get-Date -Format 'yyyyMMdd-HHmmss-fff')+"-$Action.log")
Start-Transcript -Path $logFile | Out-Null
$exitCode=0
Push-Location $root
try {
    Write-Host $selected[0].title -ForegroundColor Green
    Write-Host "日志：$logFile"
    Write-Host '首次安装依赖可能下载；项目管理的缓存、临时文件和输出均设置在 D 盘。'
    switch ($Action) {
        'health' { Python 'scripts\launch_center_support.py' @('health') }
        'web' { StartWeb -Browser -Digital }
        'stop' { Run 'powershell.exe' @('-NoProfile','-ExecutionPolicy','Bypass','-File',(Join-Path $root 'scripts\stop-web.ps1')) }
        'android-open' {
            CheckAndroid; StartWeb -Digital
            Run 'adb.exe' @('reverse','tcp:8000','tcp:8000')
            Run 'adb.exe' @('reverse','tcp:3000','tcp:3000')
            Run 'adb.exe' @('shell','monkey','-p','cn.labourlawyer.mobile','-c','android.intent.category.LAUNCHER','1')
        }
        'mini' {
            StartWeb
            Write-Host '在微信开发者工具选择“导入项目”，目录为：'
            Write-Host (Join-Path $root 'miniprogram')
            Write-Host '当前是本地测试配置。小程序支持地区指南、AI 对话、申请书和证据清单填写与生成。'
            if ($config['wechatDevtoolsExe']) {
                if (!(Test-Path $config['wechatDevtoolsExe'])) { throw 'wechatDevtoolsExe 配置的程序不存在。' }
                Start-Process -FilePath $config['wechatDevtoolsExe']
            }
            Start-Process explorer.exe -ArgumentList @((Join-Path $root 'miniprogram'))
        }
        'desktop' {
            StartWeb -Digital; Push-Location (Join-Path $root 'desktop')
            try { if (!(Test-Path 'node_modules')) { Run 'npm.cmd' @('install') }; Run 'npm.cmd' @('run','dev') } finally { Pop-Location }
        }
        'digital-human' { StartWeb -Browser -Digital }
        { $_ -in @('refresh','check-updates') } {
            $argsAdapter=@('--no-vision'); $argsCatalog=@()
            if ($Action -eq 'check-updates') { $argsAdapter+='--check-only'; $argsCatalog+='--check-only' }
            # Independent sources still run if one fails. The overall action remains failed.
            $failures=@()
            try { Python 'scripts\acquire_templates.py' $argsAdapter } catch { $failures+=$_.Exception.Message; Write-Warning $_ }
            try { Python 'scripts\acquire_province_catalog.py' $argsCatalog } catch { $failures+=$_.Exception.Message; Write-Warning $_ }
            if ($Action -eq 'refresh') {
                Python 'scripts\build_template_acquisition_ledger.py'
                RenderPython 'scripts\build_official_template_report.py'
            }
            if ($failures.Count) { throw ($failures -join "`n") }
        }
        'official-render' { RenderPython 'scripts\validate_acquired_templates.py' @('--render-only','--per-sheet','1') }
        'official-vision' {
            CheckVision
            if (!(Test-Path 'templates\_acquisition\document-visual-validation\report.json')) { throw '先运行 start.bat official-render（QUALITY / RENDER）。' }
            RenderPython 'scripts\validate_acquired_templates.py' @('--reuse-rendered','--per-sheet','1')
        }
        'examples' {
            Run 'node.exe' @((Join-Path $root 'scripts\export_document_examples.mjs'))
            RenderPython 'scripts\audit_generated_documents.py' @('--render')
            Python 'scripts\launch_center_support.py' @('audit-result')
        }
        'example-vision' {
            CheckVision
            if (!(Test-Path 'templates\_validation\generated-documents\manifest.json')) { throw '先运行 start.bat examples（QUALITY / EXAMPLES）。' }
            $argsReview=@('--existing','--vision')
            $argsCheck=@('audit-inputs'); $argsResult=@('audit-result')
            if ($Province) { $argsReview+=@('--province',$Province) }
            if ($Province) { $argsCheck+=@('--province',$Province); $argsResult+=@('--province',$Province) }
            Python 'scripts\launch_center_support.py' $argsCheck
            Python 'scripts\audit_generated_documents.py' $argsReview
            Python 'scripts\launch_center_support.py' $argsResult
        }
        'web-flow' {
            Run 'npm.cmd' @('run','build','--prefix',(Join-Path $root 'frontend'))
            if (Get-NetTCPConnection -LocalPort 4187 -State Listen -ErrorAction SilentlyContinue) { throw '4187 已被占用。请关闭该预览后重试；不会终止其他进程。' }
            $vite=Join-Path $root 'frontend\node_modules\vite\bin\vite.js'
            $preview=Start-Process node.exe -ArgumentList @(('"'+$vite+'"'),'preview','--host','127.0.0.1','--port','4187','--strictPort') -WorkingDirectory (Join-Path $root 'frontend') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $logs 'preview.stdout.log') -RedirectStandardError (Join-Path $logs 'preview.stderr.log')
            try {
                $ready=$false
                for ($i=0; $i -lt 30; $i++) {
                    if ($preview.HasExited) { throw '前端预览启动失败；查看 preview.stderr.log。' }
                    try { Invoke-WebRequest 'http://127.0.0.1:4187' -UseBasicParsing -TimeoutSec 1 | Out-Null; $ready=$true; break } catch { Start-Sleep -Milliseconds 500 }
                }
                if (!$ready) { throw '前端预览启动超时。' }
                Python 'scripts\verify_document_web_flow.py'
            } finally { if (!$preview.HasExited) { Stop-Process -Id $preview.Id -ErrorAction SilentlyContinue } }
        }
        { $_ -in @('portal-report','portal-vision') } {
            $argsPortal=@()
            if ($Action -eq 'portal-vision') { Python 'scripts\launch_center_support.py' @('model-check','--model','qwen3.8:27b'); $argsPortal+='--vision' }
            if ($Province) { $argsPortal+=@('--provinces',$Province) }
            Write-Host '终端将显示实时采集进度；原始记录仍保存在本批次 status.json。'
            Python 'scripts\audit_official_portals.py' $argsPortal
        }
        'source-report' { Python 'scripts\build_template_acquisition_ledger.py'; RenderPython 'scripts\build_official_template_report.py' }
        'guides-refresh' {
            CheckVision
            Write-Host '指南采集使用无头浏览器，实时进度在终端显示。模型仅使用 Ubuntu。'
            Python 'scripts\refresh-province-experiences.py'
        }
        'openclaw-acquire' {
            CheckVision
            $taskArgs=@()
            if ($Province) { $taskArgs+=@('--provinces',$Province) }
            Python 'scripts\openclaw-acquire-guides.py' $taskArgs
        }
        'openclaw-smoke' { CheckVision; Python 'scripts\launch_center_support.py' @('vision-smoke') }
        { $_ -in @('monitor','summary') } {
            $viewArgs=@('--watch'); if ($Action -eq 'summary') { $viewArgs=@('--summary') }
            if ($Batch) { $viewArgs+=@('--batch',$Batch) }
            if ($Plain) { $viewArgs+='--plain' }
            Python 'scripts\terminal-dashboard.py' $viewArgs
        }
        'report-check' {
            $reportBatch=$Batch
            if (!$reportBatch) {
                $latest=Get-Content (Join-Path $root 'templates\_reports\province-experiences\latest.json') -Raw -Encoding UTF8 | ConvertFrom-Json
                $reportBatch=Join-Path $root ('templates\_reports\province-experiences\'+$latest.id)
            }
            RenderPython 'scripts\review-province-reports.py' @($reportBatch,'--timeout','300')
        }
        'results' {
            Start-Process explorer.exe -ArgumentList @((Join-Path $root 'templates'))
            Start-Process explorer.exe -ArgumentList @($logs)
        }
        { $_ -in @('train-prepare','train','evaluate','ask') } {
            $trainRoot=Join-Path $root 'ModelFinetune'; $trainCache=Join-Path $trainRoot '.cache'
            $env:MODELFINETUNE_CACHE=$trainCache
            $env:HF_HOME=Join-Path $trainCache 'huggingface'; $env:HF_HUB_CACHE=Join-Path $env:HF_HOME 'hub'; $env:HF_XET_CACHE=Join-Path $env:HF_HOME 'xet'
            Push-Location $trainRoot
            try {
                Run 'uv.exe' @('sync','--locked')
                if ($Action -eq 'train-prepare') { Run 'uv.exe' @('run','python','train.py','--prepare-only') }
                elseif ($Action -eq 'train') { Run 'uv.exe' @('run','python','train.py') }
                elseif ($Action -eq 'evaluate') { Run 'uv.exe' @('run','python','evaluate.py') }
                else {
                    if (!$Question) { $Question=Read-Host '请输入法律问题' }
                    if (!$Question.Trim()) { throw '问题不能为空。' }
                    Run 'uv.exe' @('run','python','ask.py',$Question)
                }
            } finally { Pop-Location }
        }
    }
    Write-Host "`n操作已结束。请查看输出和日志；模型响应不等于文书审核通过。" -ForegroundColor Green
} catch { Write-Host $_.Exception.Message -ForegroundColor Red; $exitCode=1 }
finally { Pop-Location; Stop-Transcript | Out-Null }
exit $exitCode
