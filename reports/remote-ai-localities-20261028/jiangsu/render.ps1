param([Parameter(Mandatory=$true)][string]$Manifest)
$ErrorActionPreference='Stop'
if (Get-Process WINWORD -ErrorAction SilentlyContinue) { throw 'An existing Word process is present; do not attach or interfere.' }
$tasks=Get-Content -LiteralPath $Manifest -Raw -Encoding UTF8 | ConvertFrom-Json
$taskWord=$null
try {
    $taskWord=New-Object -ComObject Word.Application
    $taskWord.Visible=$false
    $taskWord.DisplayAlerts=0
    $taskWord.AutomationSecurity=3
    foreach ($item in $tasks) {
        $taskDocument=$null
        try {
            $taskDocument=$taskWord.Documents.Open($item.source,$false,$true,$false)
            $taskDocument.ExportAsFixedFormat($item.pdf,17)
        } finally {
            if ($null -ne $taskDocument) { $taskDocument.Close($false); [void][Runtime.InteropServices.Marshal]::ReleaseComObject($taskDocument) }
        }
    }
} finally {
    if ($null -ne $taskWord) { $taskWord.Quit(); [void][Runtime.InteropServices.Marshal]::ReleaseComObject($taskWord) }
    [GC]::Collect();[GC]::WaitForPendingFinalizers()
}
