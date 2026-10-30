param([Parameter(Mandatory=$true)][string]$Root)
$ErrorActionPreference = 'Stop'
$before = @(Get-Process WINWORD -ErrorAction SilentlyContinue | ForEach-Object { $_.Id })
$office = $null
$own = $false
$tasks = @()
try {
    $office = New-Object -ComObject Word.Application
    $created = @(Get-Process WINWORD -ErrorAction SilentlyContinue | Where-Object { $before -notcontains $_.Id })
    if ($created.Count -ne 1 -or $office.Documents.Count -ne 0) {
        throw 'Word instance ownership could not be isolated; existing user Word left untouched.'
    }
    $own = $true
    $office.Visible = $false
    $office.DisplayAlerts = 0
    $office.AutomationSecurity = 3
    $relativeInputs = @(
        'reports/production-readiness-20261030/localities/chunan/browser-generation/application.docx',
        'reports/production-readiness-20261030/localities/chunan/browser-generation/evidence.docx'
    )
    foreach ($relative in $relativeInputs) {
        $document = $null
        $source = Join-Path $Root $relative
        $stem = [IO.Path]::GetFileNameWithoutExtension($source)
        $targetRelative = 'reports/production-readiness-20261030/localities/chunan/browser-generation/word/' + $stem + '.pdf'
        $target = Join-Path $Root $targetRelative
        New-Item -ItemType Directory -Force ([IO.Path]::GetDirectoryName($target)) | Out-Null
        $hashBefore = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLower()
        try {
            $document = $office.Documents.Open($source, $false, $true, $false)
            $document.ExportAsFixedFormat($target, 17)
            $tasks += @{ source=$relative; pdf=$targetRelative; source_sha256=$hashBefore; pages=$document.ComputeStatistics(2) }
        } finally {
            if ($null -ne $document) { $document.Close($false) }
        }
        if ((Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLower() -ne $hashBefore) { throw 'Source changed during read-only export' }
    }
    @{engine='Microsoft Word isolated process, hidden read-only export'; own_instance_verified=$own; originals_unchanged=$true; tasks=$tasks} |
        ConvertTo-Json -Depth 8 | Set-Content -Encoding UTF8 (Join-Path $Root 'reports/production-readiness-20261030/localities/chunan/browser-generation/word/RENDER.json')
} finally {
    if ($own -and $null -ne $office) { $office.Quit($false) }
    if ($null -ne $office) { [void][Runtime.InteropServices.Marshal]::ReleaseComObject($office) }
}
