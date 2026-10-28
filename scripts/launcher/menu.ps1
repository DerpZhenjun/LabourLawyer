$ErrorActionPreference='Stop'
$actions=Get-Content (Join-Path $PSScriptRoot 'actions.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$groups=@(
    @{ Key='clients'; Label='CLIENTS'; Icon='[+]'; Title='手机、小程序与数字人' },
    @{ Key='templates'; Label='TEMPLATES'; Icon='[=]'; Title='官方模板获取与更新' },
    @{ Key='quality'; Label='QUALITY'; Icon='[v]'; Title='文书验证与 OpenClaw' },
    @{ Key='reports'; Label='REPORTS'; Icon='[#]'; Title='官网观察与来源报告' },
    @{ Key='models'; Label='MODELS'; Icon='[*]'; Title='法律模型训练与评测' },
    @{ Key='tools'; Label='TOOLS'; Icon='[/]'; Title='环境、结果与服务管理' }
)
function Show-Brand([string]$Page) {
    if (![Console]::IsOutputRedirected) { Clear-Host }
    Write-Host ''
    Write-Host '    __       ___         LabourLawyer' -ForegroundColor Cyan
    Write-Host '   / /      / _ |        LEGAL WORKSPACE' -ForegroundColor Cyan
    Write-Host '  / /__    / __ |        ------------------------------' -ForegroundColor Cyan
    Write-Host ' /____/   /_/ |_|        Official templates. Clear steps.' -ForegroundColor DarkCyan
    Write-Host ''
    Write-Host ('  {0}' -f $Page) -ForegroundColor White
    Write-Host '  ----------------------------------------------------' -ForegroundColor DarkGray
}
function Show-Entry([int]$Number,[string]$Icon,[string]$Label,[string]$Title) {
    Write-Host ('  {0,2}  {1}  {2,-14}' -f $Number,$Icon,$Label) -ForegroundColor Cyan -NoNewline
    Write-Host $Title -ForegroundColor Gray
}
function Invoke-Entry($Entry) {
    Write-Host ("`n  >> {0}" -f $Entry.title) -ForegroundColor Green
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'run.ps1') -Action $Entry.id
    if ($LASTEXITCODE -ne 0) { Write-Host '  [!] 操作失败，请查看上面的原因和日志。' -ForegroundColor Yellow }
    Read-Host '  按回车返回' | Out-Null
}
$currentGroup=$null
while ($true) {
    if (!$currentGroup) {
        Show-Brand 'HOME / 首页'
        Show-Entry 1 '[>]' 'WEB' '启动网页端'
        Show-Entry 2 '[>]' 'DESKTOP' '启动 Windows 桌面端'
        Show-Entry 3 '[x]' 'STOP' '停止项目网页服务'
        Write-Host ''
        for ($i=0;$i -lt $groups.Count;$i++) { $g=$groups[$i]; Show-Entry ($i+4) $g.Icon $g.Label $g.Title }
        Write-Host ''
        Show-Entry 0 '[x]' 'EXIT' '退出菜单，后台服务继续运行'
        $inputValue=Read-Host '  SELECT'
        if ($inputValue -eq '0') { break }
        if ($inputValue -in @('1','2','3')) {
            $id=@{'1'='web';'2'='desktop';'3'='stop'}[$inputValue]
            Invoke-Entry ($actions | Where-Object { $_.id -eq $id }); continue
        }
        $number=0
        if ([int]::TryParse($inputValue,[ref]$number) -and $number -ge 4 -and $number -le 9) { $currentGroup=$groups[$number-4] }
        else { Write-Host '  [!] 请输入 0–9。' -ForegroundColor Yellow }
    } else {
        Show-Brand ("HOME / {0} / {1}" -f $currentGroup.Label,$currentGroup.Title)
        $entries=@($actions | Where-Object { $_.group -eq $currentGroup.Key })
        for ($i=0;$i -lt $entries.Count;$i++) { Show-Entry ($i+1) $entries[$i].icon $entries[$i].label $entries[$i].title }
        Write-Host ''
        Show-Entry 0 '[<]' 'BACK' '返回首页'
        $inputValue=Read-Host '  SELECT'
        if ($inputValue -eq '0') { $currentGroup=$null; continue }
        $number=0
        if ([int]::TryParse($inputValue,[ref]$number) -and $number -ge 1 -and $number -le $entries.Count) { Invoke-Entry $entries[$number-1] }
        else { Write-Host '  [!] 编号无效。' -ForegroundColor Yellow }
    }
}
