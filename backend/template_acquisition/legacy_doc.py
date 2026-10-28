from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


POWERSHELL_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
$word = $null
$document = $null
try {
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0
    $word.AutomationSecurity = 3
    $document = $word.Documents.Open($env:PARTLAWYER_DOC_INPUT, $false, $true)
    $document.SaveAs2($env:PARTLAWYER_DOC_OUTPUT, 16)
} finally {
    if ($null -ne $document) { $document.Close($false) }
    if ($null -ne $word) { $word.Quit() }
    if ($null -ne $document) { [void][Runtime.InteropServices.Marshal]::ReleaseComObject($document) }
    if ($null -ne $word) { [void][Runtime.InteropServices.Marshal]::ReleaseComObject($word) }
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}
"""


def convert_doc_to_docx(input_path: Path, output_path: Path, temp_dir: Path) -> None:
    powershell = shutil.which("powershell") or shutil.which("powershell.exe")
    if not powershell:
        raise FileNotFoundError("Windows PowerShell is required for hidden Word conversion")
    temp_dir.mkdir(parents=True, exist_ok=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update(
        {
            "PARTLAWYER_DOC_INPUT": str(input_path.resolve()),
            "PARTLAWYER_DOC_OUTPUT": str(output_path.resolve()),
            "TEMP": str(temp_dir.resolve()),
            "TMP": str(temp_dir.resolve()),
        }
    )
    creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    completed = subprocess.run(
        [powershell, "-NoProfile", "-NonInteractive", "-Command", POWERSHELL_SCRIPT],
        env=env,
        capture_output=True,
        timeout=120,
        creationflags=creation_flags,
    )
    if completed.returncode != 0 or not output_path.is_file():
        stderr = completed.stderr.decode("gb18030", errors="replace")
        raise RuntimeError(f"Hidden Microsoft Word conversion failed: {stderr}")
