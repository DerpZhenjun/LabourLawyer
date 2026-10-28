from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
OPENCLAW_BRIDGE_PATH = PROJECT_ROOT / "backend" / "template_acquisition" / "openclaw_bridge.py"
BRIDGE_SPEC = importlib.util.spec_from_file_location("template_openclaw_bridge", OPENCLAW_BRIDGE_PATH)
if BRIDGE_SPEC is None or BRIDGE_SPEC.loader is None:
    raise RuntimeError(f"无法加载 {OPENCLAW_BRIDGE_PATH}")
BRIDGE_MODULE = importlib.util.module_from_spec(BRIDGE_SPEC)
BRIDGE_SPEC.loader.exec_module(BRIDGE_MODULE)
DOCUMENT_VISION_PROMPT = BRIDGE_MODULE.DOCUMENT_VISION_PROMPT
describe_image = BRIDGE_MODULE.describe_image


TEMPLATE_ROOT = PROJECT_ROOT / "templates"
DOCX_ROOT = TEMPLATE_ROOT / "_docx"
ORIGINAL_ROOT = TEMPLATE_ROOT / "_original"
OUTPUT_ROOT = TEMPLATE_ROOT / "_acquisition" / "document-visual-validation"
OPENCLAW_ROOT = TEMPLATE_ROOT / "_acquisition" / "openclaw-document-review"
POPPLER_DIR = Path(
    r"C:\Users\DerpZhenjun\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\poppler\Library\bin"
)
PDFTOPPM = Path(os.environ.get('LABOURLAWYER_PDFTOPPM', str(POPPLER_DIR / 'pdftoppm.exe')))
FONT_PATH = Path(r"C:\Windows\Fonts\msyh.ttc")
OVERVIEW_PROMPT = (
    'Four official document thumbnails are shown in reading order. '
    'Return JSON only: {"broken":[false,false,false,false]}. '
    'Use true only for obvious page clipping, overlap, or corruption.'
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_stem(path: Path) -> str:
    return "".join(char if char not in '<>:"/\\|?*' else "_" for char in path.stem)


def collect_documents() -> list[dict]:
    documents: list[dict] = []
    for path in sorted(DOCX_ROOT.rglob("*.docx")):
        documents.append(
            {
                "source": str(path.resolve()),
                "relative_source": str(path.relative_to(PROJECT_ROOT)),
                "province_folder": path.parent.name,
                "label": f"{path.parent.name}/{path.stem}",
                "format": "docx",
            }
        )
    for path in sorted(ORIGINAL_ROOT.rglob("*")):
        if not path.is_file() or path.suffix.casefold() not in {".pdf", ".xlsx"}:
            continue
        documents.append(
            {
                "source": str(path.resolve()),
                "relative_source": str(path.relative_to(PROJECT_ROOT)),
                "province_folder": path.parent.name,
                "label": f"{path.parent.name}/{path.stem}",
                "format": path.suffix.casefold().lstrip("."),
            }
        )
    return documents


def convert_office_files(documents: list[dict]) -> None:
    conversion_manifest = OUTPUT_ROOT / "conversion-input.json"
    conversion_manifest.parent.mkdir(parents=True, exist_ok=True)
    tasks: list[dict] = []
    for item in documents:
        output_dir = OUTPUT_ROOT / item["province_folder"] / safe_stem(Path(item["source"]))
        output_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = output_dir / "document.pdf"
        item["pdf"] = str(pdf_path.resolve())
        if item["format"] == "pdf":
            if Path(item["source"]).resolve() != pdf_path.resolve():
                shutil.copy2(item["source"], pdf_path)
            item["conversion"] = "copied_pdf"
        else:
            pdf_path.unlink(missing_ok=True)
            tasks.append(
                {
                    "source": item["source"],
                    "pdf": str(pdf_path.resolve()),
                    "format": item["format"],
                }
            )
    conversion_manifest.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")
    if not tasks:
        return

    powershell_script = OUTPUT_ROOT / "convert-office-files.ps1"
    powershell_script.write_text(
        r'''param([Parameter(Mandatory=$true)][string]$Manifest)
$ErrorActionPreference = "Stop"
$tasks = Get-Content -LiteralPath $Manifest -Raw -Encoding UTF8 | ConvertFrom-Json
$word = $null
$excel = $null
try {
    $docxTasks = @($tasks | Where-Object { $_.format -eq "docx" })
    if ($docxTasks.Count -gt 0) {
        $word = New-Object -ComObject Word.Application
        $word.Visible = $false
        $word.DisplayAlerts = 0
        $word.AutomationSecurity = 3
        foreach ($item in $docxTasks) {
            $document = $null
            try {
                try {
                    $document = $word.Documents.Open($item.source, $false, $true, $false)
                } catch {
                    # Some official DOCX files contain recoverable Word XML defects.
                    # OpenAndRepair is used only for the PDF visual review; the template file is not rewritten.
                    $document = $word.Documents.Open($item.source, $false, $true, $false, '', '', $false, '', '', 0, 0, $false, $true)
                }
                $document.ExportAsFixedFormat($item.pdf, 17)
            } catch {
                Write-Output ("DOCX_ERROR`t" + $item.source + "`t" + $_.Exception.Message)
            } finally {
                if ($null -ne $document) { $document.Close($false) }
            }
        }
    }
    $xlsxTasks = @($tasks | Where-Object { $_.format -eq "xlsx" })
    if ($xlsxTasks.Count -gt 0) {
        $excel = New-Object -ComObject Excel.Application
        $excel.Visible = $false
        $excel.DisplayAlerts = $false
        $excel.AutomationSecurity = 3
        foreach ($item in $xlsxTasks) {
            $workbook = $null
            try {
                $workbook = $excel.Workbooks.Open($item.source, 0, $true)
                $workbook.ExportAsFixedFormat(0, $item.pdf)
            } catch {
                Write-Output ("XLSX_ERROR`t" + $item.source + "`t" + $_.Exception.Message)
            } finally {
                if ($null -ne $workbook) { $workbook.Close($false) }
            }
        }
    }
} finally {
    if ($null -ne $word) { $word.Quit() }
    if ($null -ne $excel) { $excel.Quit() }
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}
''',
        encoding="utf-8-sig",
    )
    completed = subprocess.run(
        [
            "powershell.exe",
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(powershell_script),
            "-Manifest",
            str(conversion_manifest),
        ],
        capture_output=True,
        text=True,
        timeout=900,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"Office 隐藏模式转换失败: {completed.stderr.strip() or completed.stdout.strip()}")
    for item in documents:
        if item["format"] != "pdf":
            if Path(item["pdf"]).is_file():
                item["conversion"] = "office_export_to_pdf"
            else:
                item["conversion"] = "failed"
                item["conversion_error"] = "Office could not export this file; see conversion stdout"
    conversion_log = OUTPUT_ROOT / "conversion-errors.log"
    if completed.stdout.strip():
        conversion_log.write_text(completed.stdout, encoding="utf-8")
    else:
        conversion_log.unlink(missing_ok=True)


def render_first_pages(documents: list[dict]) -> None:
    if not PDFTOPPM.is_file():
        raise FileNotFoundError(f"未找到 pdftoppm: {PDFTOPPM}")
    for index, item in enumerate(documents, start=1):
        pdf = Path(item["pdf"])
        if not pdf.is_file():
            item["render_status"] = "skipped_conversion_failed"
            print(f"[{index}/{len(documents)}] 跳过转换失败文件 {item['label']}", flush=True)
            continue
        output_prefix = pdf.parent / "page-1"
        completed = subprocess.run(
            [
                str(PDFTOPPM),
                "-png",
                "-f",
                "1",
                "-singlefile",
                "-r",
                "130",
                str(pdf),
                str(output_prefix),
            ],
            capture_output=True,
            text=True,
            timeout=120,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        png = output_prefix.with_suffix(".png")
        if completed.returncode != 0 or not png.is_file():
            item["render_status"] = "failed"
            item["render_error"] = completed.stderr.strip()
            print(f"[{index}/{len(documents)}] 渲染失败 {item['label']}", flush=True)
            continue
        item["first_page_png"] = str(png.resolve())
        item["render_status"] = "success"
        print(f"[{index}/{len(documents)}] 已渲染 {item['label']}", flush=True)


def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    if FONT_PATH.is_file():
        return ImageFont.truetype(str(FONT_PATH), size)
    return ImageFont.load_default()


def create_contact_sheets(documents: list[dict], per_sheet: int = 4) -> list[dict]:
    documents = [item for item in documents if item.get("render_status") == "success"]
    sheets_dir = OUTPUT_ROOT / "sheets"
    sheets_dir.mkdir(parents=True, exist_ok=True)
    cell_width, cell_height, label_height = 1050, 1450, 72
    columns = 1 if per_sheet == 1 else 2
    rows = math.ceil(per_sheet / columns)
    font = load_font(25)
    sheets: list[dict] = []
    for batch_start in range(0, len(documents), per_sheet):
        batch = documents[batch_start : batch_start + per_sheet]
        sheet_no = batch_start // per_sheet + 1
        canvas = Image.new("RGB", (columns * cell_width, rows * cell_height), "#d8d8d8")
        draw = ImageDraw.Draw(canvas)
        for local_index, item in enumerate(batch):
            col, row = local_index % columns, local_index // columns
            x, y = col * cell_width, row * cell_height
            label = f"[{batch_start + local_index + 1:02d}] {item['label']}"
            draw.rectangle((x, y, x + cell_width - 2, y + cell_height - 2), outline="#555555", width=2)
            draw.text((x + 18, y + 18), label, font=font, fill="#111111")
            with Image.open(item["first_page_png"]) as page:
                page = page.convert("RGB")
                page.thumbnail((cell_width - 36, cell_height - label_height - 24), Image.Resampling.LANCZOS)
                px = x + (cell_width - page.width) // 2
                py = y + label_height + (cell_height - label_height - page.height) // 2
                canvas.paste(page, (px, py))
        sheet_path = sheets_dir / f"sheet-{sheet_no:02d}.jpg"
        canvas.save(sheet_path, quality=92, optimize=True)
        vision_canvas = canvas.copy()
        vision_canvas.thumbnail((1000, 1400), Image.Resampling.LANCZOS)
        vision_path = sheets_dir / f"sheet-{sheet_no:02d}.vision.jpg"
        vision_canvas.save(vision_path, quality=82, optimize=True)
        sheets.append(
            {
                "sheet": str(sheet_path.resolve()),
                "vision_sheet": str(vision_path.resolve()),
                "documents": [item["relative_source"] for item in batch],
                "labels": [item["label"] for item in batch],
            }
        )
    return sheets


def run_openclaw_reviews(sheets: list[dict], limit: int | None = None, start: int = 1) -> None:
    for index, sheet in enumerate(sheets, start=1):
        report = Path(sheet["sheet"]).with_suffix(".openclaw.json")
        if index < start:
            sheet["review_status"] = "success_existing_report" if report.is_file() else "skipped_before_start"
            if report.is_file():
                sheet["review_report"] = str(report.resolve())
            continue
        if limit is not None and index > limit:
            sheet["review_status"] = "skipped_by_limit"
            continue
        print(f"[{index}/{len(sheets)}] OpenClaw + qwen3.8:27b 核验 {Path(sheet['sheet']).name}", flush=True)
        try:
            describe_image(
                Path(sheet["vision_sheet"]),
                report,
                OPENCLAW_ROOT,
                timeout_seconds=240,
                prompt=DOCUMENT_VISION_PROMPT,
                role="official_document_first_page_visual_review",
            )
            sheet["review_status"] = "success"
            sheet["review_report"] = str(report.resolve())
        except Exception as exc:
            sheet["review_status"] = "failed"
            sheet["review_report"] = str(report.resolve())
            sheet["review_error"] = str(exc)
            print(f"  核验失败: {exc}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="渲染并用 OpenClaw + Qwen 视觉复核已取得的官方文书")
    parser.add_argument("--render-only", action="store_true", help="只渲染，不运行 OpenClaw")
    parser.add_argument("--review-limit", type=int, help="只核验前 N 张联系表，用于冒烟测试")
    parser.add_argument("--review-start", type=int, default=1, help="从第 N 张联系表开始核验，之前的批次复用现有报告")
    parser.add_argument("--per-sheet", type=int, default=4, help="每张联系表包含的文书数")
    parser.add_argument("--reuse-rendered", action="store_true", help="复用上次渲染结果，只重建联系表并核验")
    args = parser.parse_args()
    if args.per_sheet < 1:
        parser.error('--per-sheet 必须大于 0')

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    previous_report = OUTPUT_ROOT / "report.json"
    if args.reuse_rendered and not previous_report.is_file():
        parser.error('没有已有渲染记录，请先运行 --render-only')
    if args.reuse_rendered and previous_report.is_file():
        documents = json.loads(previous_report.read_text(encoding="utf-8"))["documents"]
    else:
        documents = collect_documents()
    if not documents:
        raise SystemExit("没有找到可核验的文书")
    for item in documents:
        path = Path(item['source'])
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if args.reuse_rendered and item.get('source_sha256') != digest:
            raise SystemExit(f"渲染记录过旧或模板已变化，请先重新 --render-only：{path}")
        item['source_sha256'] = digest
    started = utc_now()
    if not args.reuse_rendered:
        convert_office_files(documents)
        render_first_pages(documents)
    sheets = create_contact_sheets(documents, args.per_sheet)
    if not args.render_only:
        run_openclaw_reviews(sheets, args.review_limit, args.review_start)
    report = {
        "schema_version": 1,
        "started_at": started,
        "finished_at": utc_now(),
        "engine": None if args.render_only else "OpenClaw",
        "model": None if args.render_only else "ollama/qwen3.8:27b",
        "review_scope": "first page of every acquired DOCX/PDF/XLSX rendered in hidden Office mode",
        "document_count": len(documents),
        "sheet_count": len(sheets),
        "documents": documents,
        "sheets": sheets,
    }
    report_path = OUTPUT_ROOT / "report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"documents": len(documents), "sheets": len(sheets), "report": str(report_path)}, ensure_ascii=False), flush=True)
    return 1 if (any(item.get("review_status") == "failed" for item in sheets)
                 or any(item.get('render_status') != 'success' for item in documents)) else 0


if __name__ == "__main__":
    raise SystemExit(main())
