from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_ROOT = PROJECT_ROOT / "templates"
CATALOG_PATH = PROJECT_ROOT / "config" / "province_official_template_catalog.json"
VALIDATION_REPORT = TEMPLATE_ROOT / "_acquisition" / "document-visual-validation" / "report.json"
SOURCE_ROOT = TEMPLATE_ROOT / "_acquisition" / "sources"
LEDGER_PATH = TEMPLATE_ROOT / "官方文书采集台账.md"


STATUS_LABELS = {
    "official_archive_templates": "已取得官方压缩包中的模板",
    "official_doc_templates": "已取得官方 Word 模板",
    "official_service_portal_no_public_blank_found": "已核对官方服务门户，未发现公开空白模板",
    "official_template_page_temporarily_unavailable": "官方模板页面当前不可访问",
    "official_download_endpoint_returned_empty_file": "官方模板端点存在，但当前返回空文件",
    "acquired_by_primary_adapter": "已由省级官方接口适配器取得",
    "official_guide_no_public_blank_found": "已核对官方办事指南，未发现公开空白模板",
    "official_online_service_no_public_blank_found": "已核对官方在线服务，未发现公开空白模板",
    "official_pdf_templates": "已取得官方 PDF 模板",
    "official_guide_text_only": "官方页面仅公开文字样式，未提供模板文件",
    "official_application_only": "仅取得官方仲裁申请书",
    "official_combined_doc": "已取得包含申请书和证据目录的官方合并文书",
    "official_combined_docx": "已取得包含申请书和证据清单的官方合并文书",
    "official_guide_pdf_no_separate_blank_found": "已取得官方办事指南 PDF，未发现独立空白模板",
    "official_application_and_evidence_directory": "已取得官方申请书和证据目录",
}


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(PROJECT_ROOT.resolve())).replace("\\", "/")


def parse_openclaw_stdout(report_path: Path) -> tuple[bool, str | None]:
    if not report_path.is_file():
        return False, None
    report = json.loads(report_path.read_text(encoding="utf-8"))
    stdout = report.get("stdout", "")
    try:
        envelope = json.loads(stdout)
    except json.JSONDecodeError:
        return False, None
    outputs = envelope.get("outputs") or []
    if not envelope.get("ok") or not outputs:
        return False, None
    return True, outputs[0].get("text")


def reconcile_visual_report() -> tuple[dict, dict[str, dict]]:
    if not VALIDATION_REPORT.is_file():
        return {}, {}
    report = json.loads(VALIDATION_REPORT.read_text(encoding="utf-8"))
    document_reviews: dict[str, dict] = {}
    for sheet in report["sheets"]:
        report_path = Path(sheet.get("review_report", ""))
        output_complete, model_text = parse_openclaw_stdout(report_path)
        if output_complete and sheet.get("review_status") == "failed":
            sheet["review_status"] = "success_output_captured_before_process_timeout"
            sheet["process_warning"] = sheet.pop("review_error", "OpenClaw process exit wait timed out")
        sheet["model_output"] = model_text
        for document in sheet["documents"]:
            document_reviews[document.replace("\\", "/")] = {
                "status": sheet.get("review_status"),
                "report": relative(report_path) if report_path.is_file() else None,
                "model": report.get("model"),
                "model_output": model_text,
            }
    report["successful_review_batches"] = sum(
        item.get("review_status", "").startswith("success") for item in report["sheets"]
    )
    report["failed_review_batches"] = sum(item.get("review_status") == "failed" for item in report["sheets"])
    VALIDATION_REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report, document_reviews


def province_files(folder: str) -> list[Path]:
    files: list[Path] = []
    for root in (TEMPLATE_ROOT / "_docx" / folder, TEMPLATE_ROOT / "_original" / folder):
        if root.is_dir():
            files.extend(sorted(path for path in root.rglob("*") if path.is_file()))
    return files


def main() -> None:
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    visual_report, document_reviews = reconcile_visual_report()
    provinces = catalog["provinces"]
    editable_count = 0
    acquired_count = 0
    lines = [
        "# 中国大陆31个省级行政区劳动人事争议文书采集台账",
        "",
        f"生成时间：{datetime.now(timezone.utc).isoformat()}",
        "",
        "## 汇总",
        "",
        "- 覆盖范围：31个省级行政区，每个地区均有官方来源、采集状态和审计记录。",
        "- 文件原则：只保存官方来源实际公开的文件；未公开、端点失效或仅有文字说明的地区不生成替代模板。",
        f"- 视觉核验：OpenClaw + `{visual_report['model']}`，共 {visual_report['sheet_count']} 批，完整取得模型输出 {visual_report['successful_review_batches']} 批。",
        "- 视觉核验范围：每份已取得文件的首页缩略图，仅检查明显裁切、重叠或损坏；高清渲染图保存在 `_acquisition/document-visual-validation`。",
        "",
        "## 逐省记录",
        "",
    ]

    for province in provinces:
        folder = province["folder"]
        files = province_files(folder)
        editable = [path for path in files if path.suffix.casefold() == ".docx" and "_docx" in path.parts]
        if files:
            acquired_count += 1
        if editable:
            editable_count += 1
        reviews = []
        for path in files:
            key = relative(path)
            if key in document_reviews:
                reviews.append({"file": key, **document_reviews[key]})
        source_payload = {
            "schema_version": 1,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "province": province,
            "acquired_files": [relative(path) for path in files],
            "editable_docx_files": [relative(path) for path in editable],
            "visual_reviews": reviews,
        }
        source_path = SOURCE_ROOT / folder / "source.json"
        source_path.parent.mkdir(parents=True, exist_ok=True)
        source_path.write_text(json.dumps(source_payload, ensure_ascii=False, indent=2), encoding="utf-8")

        lines.extend(
            [
                f"### {province['province_zh']}（{folder}）",
                "",
                f"- 状态：{STATUS_LABELS.get(province['status'], province['status'])}",
                f"- 官方机构：{province.get('authority') or '目录未填写'}",
                f"- 适用范围：{province.get('scope') or province['province_zh']}",
                f"- 官方来源：[{province['source_url']}]({province['source_url']})",
                f"- 可编辑 DOCX：{len(editable)} 份",
            ]
        )
        if files:
            lines.append("- 已取得文件：")
            for path in files:
                lines.append(f"  - `{relative(path)}`")
        else:
            lines.append("- 已取得文件：无。未发现可验证的公开文件，未制作替代模板。")
        if reviews:
            status_set = sorted({item["status"] for item in reviews})
            lines.append(f"- OpenClaw 视觉复核：{', '.join(status_set)}")
        else:
            lines.append("- OpenClaw 视觉复核：无可下载文件可供渲染。")
        lines.extend([f"- 审计记录：`{relative(source_path)}`", ""])

    lines[8:8] = [
        f"- 已取得至少一份官方文件：{acquired_count}/31 个地区。",
        f"- 已取得可编辑 DOCX：{editable_count}/31 个地区，共 {len(list((TEMPLATE_ROOT / '_docx').rglob('*.docx')))} 份。",
    ]
    LEDGER_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "provinces": len(provinces),
                "acquired_provinces": acquired_count,
                "editable_provinces": editable_count,
                "ledger": str(LEDGER_PATH),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
