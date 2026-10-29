param([Parameter(Mandatory=$true)][string]$Manifest)
$ErrorActionPreference='Stop'
Add-Type @'
using System;
using System.Runtime.InteropServices;
public static class JiangsuTaskWord {
  [StructLayout(LayoutKind.Sequential)] struct MultiQI { public IntPtr iid; public IntPtr instance; public int result; }
  [DllImport("ole32.dll",ExactSpelling=true)] static extern int CoCreateInstanceEx(ref Guid clsid,IntPtr outer,uint context,IntPtr server,uint count,[In,Out] MultiQI[] queries);
  [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr hwnd,out uint process);
  public static object DispatchEx() {
    Guid clsid=new Guid("000209FF-0000-0000-C000-000000000046");
    Guid iid=new Guid("00020400-0000-0000-C000-000000000046");
    IntPtr ptr=Marshal.AllocCoTaskMem(16); MultiQI[] q=new MultiQI[1];
    try {
      Marshal.StructureToPtr(iid,ptr,false);q[0].iid=ptr;
      Marshal.ThrowExceptionForHR(CoCreateInstanceEx(ref clsid,IntPtr.Zero,4,IntPtr.Zero,1,q));
      Marshal.ThrowExceptionForHR(q[0].result);
      return Marshal.GetObjectForIUnknown(q[0].instance);
    } finally {
      if(q[0].instance!=IntPtr.Zero)Marshal.Release(q[0].instance);
      Marshal.FreeCoTaskMem(ptr);
    }
  }
  public static object Process(int hwnd) { uint process; GetWindowThreadProcessId(new IntPtr(hwnd),out process);return (int)process; }
}
'@
$before=@(Get-Process WINWORD -ErrorAction SilentlyContinue | ForEach-Object { $_.Id })
$tasks=Get-Content -LiteralPath $Manifest -Raw -Encoding UTF8 | ConvertFrom-Json
$taskWord=$null;$distinct=$false;$taskWordId=0;$during=@();$completed=0;$windowChecks=@();$savedUpdateLinks=$null;$linkUpdatesDisabled=$false
try {
    $creationStarted=Get-Date
    $taskWord=[JiangsuTaskWord]::DispatchEx()
    $during=@(Get-Process WINWORD -ErrorAction SilentlyContinue | ForEach-Object { $_.Id })
    $newIds=@($during | Where-Object { $before -notcontains $_ })
    if ($newIds.Count -ne 1) {
        throw 'New Word object has no independently distinguishable new PID; no property changes, document opens or Quit permitted.'
    }
    $taskWordId=[int]$newIds[0]
    $newProcess=Get-Process -Id $taskWordId
    $newIdentity=Get-CimInstance Win32_Process -Filter "ProcessId=$taskWordId"
    if ($newProcess.StartTime -lt $creationStarted.AddSeconds(-2) -or -not $newIdentity.ExecutablePath.EndsWith('\WINWORD.EXE',[StringComparison]::OrdinalIgnoreCase) -or [int]$taskWord.Documents.Count -ne 0) {
        throw 'New empty instance creation evidence does not match; no document open or Quit permitted.'
    }
    $distinct=$true
    $taskWord.Visible=$false;$taskWord.DisplayAlerts=0;$taskWord.AutomationSecurity=3
    $savedUpdateLinks=$taskWord.Options.UpdateLinksAtOpen
    $taskWord.Options.UpdateLinksAtOpen=$false
    $linkUpdatesDisabled=-not [bool]$taskWord.Options.UpdateLinksAtOpen
    if (-not $linkUpdatesDisabled) { throw 'Link updates were not disabled; no document open permitted.' }
    foreach ($item in $tasks) {
        $taskDocument=$null
        try {
            $taskDocument=$taskWord.Documents.Open($item.source,$false,$true,$false)
            $documentWindow=[int]$taskDocument.Windows.Item(1).Hwnd
            $documentProcess=[int]([JiangsuTaskWord]::Process($documentWindow))
            if ($documentProcess -ne $taskWordId -or $before -contains $documentProcess) {
                $distinct=$false
                throw 'Own read-only document Window.Hwnd does not belong to the proved new PID; no export or application Quit.'
            }
            $windowChecks+=@{document=$item.source;window_pid=$documentProcess;matches_new_instance=$true}
            $taskDocument.ExportAsFixedFormat($item.pdf,17)
            $completed++
        } finally {
            if ($null -ne $taskDocument) { $taskDocument.Close($false);[void][Runtime.InteropServices.Marshal]::ReleaseComObject($taskDocument) }
        }
    }
} finally {
    if ($null -ne $taskWord) {
        if ($distinct) {
            if ($null -ne $savedUpdateLinks) { $taskWord.Options.UpdateLinksAtOpen=$savedUpdateLinks }
            $taskWord.Quit($false)
        }
        [void][Runtime.InteropServices.Marshal]::ReleaseComObject($taskWord)
    }
    [GC]::Collect();[GC]::WaitForPendingFinalizers()
    $after=@(Get-Process WINWORD -ErrorAction SilentlyContinue | ForEach-Object { $_.Id })
    $originalsRemain=@($before | Where-Object { $after -notcontains $_ }).Count -eq 0
    $result=[ordered]@{method='CoCreateInstanceEx/IID_IDispatch (DispatchEx semantics)';before=$before;during=$during;new_instance_pid=$taskWordId;new_pid_verified=$distinct;document_window_pid_checks=$windowChecks;macro_security=3;link_updates_disabled=$linkUpdatesDisabled;option_restored_before_own_quit=$distinct;completed=$completed;after=$after;original_pids_still_alive=$originalsRemain;quit_called_only_on_distinct_new_object=$distinct}
    $result | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path (Split-Path -Parent $Manifest) 'word-instance-isolation.json') -Encoding UTF8
    if (-not $originalsRemain) { throw 'A preexisting Word PID is no longer alive; inspect evidence; no other process was stopped by this task.' }
}
