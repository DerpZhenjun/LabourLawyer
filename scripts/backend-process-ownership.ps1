# Pure ownership check used before a user-requested backend restart. No process changes here.
function Get-OwnedBackendProcesses {
    param([object[]]$Processes, [int]$ListenerPid, [string]$ProjectRoot, [ValidateRange(1024,65535)][int]$Port = 8000)
    $expected = [IO.Path]::GetFullPath((Join-Path $ProjectRoot '.venv\Scripts\python.exe'))
    $byId = @{}
    foreach ($item in $Processes) { $byId[[int]$item.ProcessId] = $item }
    $chain = [Collections.Generic.List[object]]::new()
    $seen = [Collections.Generic.HashSet[int]]::new()
    $nextId = $ListenerPid
    for ($depth = 0; $depth -lt 4; $depth++) {
        if (!$byId.ContainsKey($nextId) -or !$seen.Add($nextId)) { break }
        $item = $byId[$nextId]
        # The virtualenv launcher and its Python child share this exact uvicorn command.
        if ([string]$item.CommandLine -notmatch '(?i)(?:^|\s)-m\s+uvicorn\s+app:app(?:\s|$)') { break }
        if ([string]$item.CommandLine -notmatch "(?:^|\s)--port\s+$Port(?:\s|$)") { break }
        $chain.Add($item)
        if ([string]$item.ExecutablePath -ieq $expected) { return $chain.ToArray() }
        $nextId = [int]$item.ParentProcessId
    }
    throw "Port $Port could not be tied to this project virtualenv. No process was stopped."
}
