from __future__ import annotations

import argparse
import hashlib
import io
import json
import shutil
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import httpx


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.template_acquisition.legacy_doc import convert_doc_to_docx
from backend.template_acquisition.security import validate_docx, validate_legacy_doc
from backend.terminal_progress import emit


CATALOG_PATH = PROJECT_ROOT / "config" / "province_official_template_catalog.json"
TEMPLATE_ROOT = PROJECT_ROOT / "templates"
REPORT_PATH = TEMPLATE_ROOT / "province-template-acquisition-report.json"
MAX_DOWNLOAD_BYTES = 25 * 1024 * 1024


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def host_allowed(url: str, domains: list[str], allow_http: bool = False) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in ({"https", "http"} if allow_http else {"https"}) or not parsed.hostname:
        return False
    hostname = parsed.hostname.casefold().rstrip(".")
    return any(hostname == item.casefold() or hostname.endswith("." + item.casefold()) for item in domains)


def download(client: httpx.Client, url: str, domains: list[str], allow_http: bool = False) -> tuple[bytes, str, str | None]:
    if not host_allowed(url, domains, allow_http):
        raise ValueError(f"URL 不在该官方来源允许域名中: {url}")
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with client.stream("GET", url) as response:
                response.raise_for_status()
                final_url = str(response.url)
                if not host_allowed(final_url, domains, allow_http):
                    raise ValueError(f"重定向离开官方来源允许域名: {final_url}")
                chunks: list[bytes] = []
                total = 0
                for chunk in response.iter_bytes():
                    total += len(chunk)
                    if total > MAX_DOWNLOAD_BYTES:
                        raise ValueError("下载文件超过 25 MiB 安全限制")
                    chunks.append(chunk)
                return b"".join(chunks), final_url, response.headers.get("content-type")
        except (httpx.HTTPStatusError, httpx.TimeoutException, httpx.NetworkError) as exc:
            last_error = exc
            retryable = not isinstance(exc, httpx.HTTPStatusError) or exc.response.status_code >= 500
            if not retryable or attempt == 2:
                raise
            time.sleep(attempt + 1)
    raise RuntimeError(f"下载失败: {last_error}")


def decoded_zip_name(name: str) -> str:
    try:
        return name.encode("cp437").decode("gb18030")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return name


def archive_member(data: bytes, prefix: str | None = None, name_contains: str | None = None) -> tuple[bytes, str]:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        infos = archive.infolist()
        if len(infos) > 500:
            raise ValueError("压缩包文件数量异常")
        matches = [
            item for item in infos
            if not item.is_dir()
            and (prefix is None or item.filename.startswith(prefix))
            and (name_contains is None or name_contains in decoded_zip_name(item.filename))
        ]
        if len(matches) != 1:
            raise ValueError(f"压缩包成员选择条件匹配到 {len(matches)} 个文件")
        info = matches[0]
        if info.file_size > MAX_DOWNLOAD_BYTES or ".." in Path(info.filename).parts:
            raise ValueError("压缩包成员不安全")
        return archive.read(info), decoded_zip_name(info.filename)


def write_if_changed(path: Path, data: bytes, check_only: bool) -> str:
    if path.is_file() and path.read_bytes() == data:
        return "unchanged"
    existed = path.exists()
    if check_only:
        return "would_update" if existed else "would_create"
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_bytes(data)
    temp_path.replace(path)
    return "updated" if existed else "created"


def validate_xlsx(data: bytes) -> dict:
    if not data.startswith(b"PK\x03\x04"):
        raise ValueError("下载文件不是 XLSX")
    with zipfile.ZipFile(io.BytesIO(data)) as workbook:
        names = set(workbook.namelist())
        required = {"[Content_Types].xml", "xl/workbook.xml"}
        if not required.issubset(names):
            raise ValueError("XLSX 结构不完整")
        if any(name.casefold().endswith("vbaproject.bin") for name in names):
            raise ValueError("XLSX 包含宏，不进入模板目录")
        return {
            "valid_xlsx": True,
            "member_count": len(names),
            "macros_present": False,
        }


def acquire_document(client: httpx.Client, province: dict, document: dict, check_only: bool) -> dict:
    domains = province["allowed_domains"]
    download_url = document.get("url") or document["archive_url"]
    payload, final_url, content_type = download(client, download_url, domains, bool(province.get("allow_http")))
    archive_name = None
    if document.get("archive_member_prefix") or document.get("archive_member_name_contains"):
        payload, archive_name = archive_member(
            payload,
            document.get("archive_member_prefix"),
            document.get("archive_member_name_contains"),
        )
    file_format = document["format"]
    digest = sha256(payload)
    folder = province["folder"]
    original_dir = TEMPLATE_ROOT / "_original" / folder
    production_dir = TEMPLATE_ROOT / "_docx" / folder
    temp_dir = TEMPLATE_ROOT / "_acquisition" / "temp" / folder
    validation: dict
    outputs: list[dict] = []

    if file_format == "docx":
        validation = validate_docx(payload).as_dict()
        output = production_dir / document["output_name"]
        status = write_if_changed(output, payload, check_only)
        outputs.append({"path": str(output), "status": status})
    elif file_format == "doc":
        validation = validate_legacy_doc(payload)
        original = original_dir / document["original_name"]
        original_status = write_if_changed(original, payload, check_only)
        outputs.append({"path": str(original), "status": original_status})
        output = production_dir / document["output_name"]
        if check_only:
            outputs.append({"path": str(output), "status": "conversion_skipped_in_check_only"})
        elif output.is_file() and original_status == "unchanged":
            validate_docx(output.read_bytes())
            outputs.append({"path": str(output), "status": "unchanged"})
        else:
            production_dir.mkdir(parents=True, exist_ok=True)
            convert_doc_to_docx(original, output, temp_dir)
            converted = output.read_bytes()
            converted_validation = validate_docx(converted).as_dict()
            validation["converted_docx"] = converted_validation
            validation["converted_sha256"] = sha256(converted)
            outputs.append({"path": str(output), "status": "converted"})
    elif file_format == "pdf":
        if not payload.startswith(b"%PDF-"):
            raise ValueError("下载文件不是 PDF")
        validation = {"valid_pdf": True, "bytes": len(payload)}
        original = original_dir / document["original_name"]
        status = write_if_changed(original, payload, check_only)
        outputs.append({"path": str(original), "status": status})
    elif file_format == "xlsx":
        validation = validate_xlsx(payload)
        original = original_dir / document["original_name"]
        status = write_if_changed(original, payload, check_only)
        outputs.append({"path": str(original), "status": status})
    else:
        raise ValueError(f"不支持的格式: {file_format}")

    return {
        "document_type": document["document_type"],
        "display_name": document["display_name"],
        "download_url": download_url,
        "final_url": final_url,
        "content_type": content_type,
        "archive_member": archive_name,
        "sha256": digest,
        "bytes": len(payload),
        "validation": validation,
        "outputs": outputs,
        "status": "success",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="按官方来源目录批量获取各省劳动仲裁文书")
    parser.add_argument("--province", action="append", help="仅处理指定英文省份名，可重复")
    parser.add_argument("--check-only", action="store_true", help="只检查，不写入模板目录")
    args = parser.parse_args()

    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    selected = {item.casefold() for item in (args.province or [])}
    started = datetime.now(timezone.utc).isoformat()
    results: list[dict] = []
    client = httpx.Client(
        follow_redirects=True,
        timeout=httpx.Timeout(45.0, connect=20.0),
        headers={"User-Agent": "Partlawyer-LAA official-template-acquirer/1.0"},
    )
    try:
        for province in catalog["provinces"]:
            if selected and province["province"].casefold() not in selected:
                continue
            record = {
                "province": province["province"],
                "province_zh": province["province_zh"],
                "folder": province["folder"],
                "authority": province.get("authority"),
                "scope": province.get("scope"),
                "source_url": province.get("source_url"),
                "catalog_status": province["status"],
                "documents": [],
                "errors": [],
            }
            print(f"[{province['province_zh']}] {province['status']}", flush=True)
            emit('download',province=province['province_zh'],message='核对官方来源目录',output=str(TEMPLATE_ROOT))
            for document in province.get("documents", []):
                try:
                    result = acquire_document(client, province, document, args.check_only)
                    record["documents"].append(result)
                    print(f"  OK {document['display_name']} ({result['bytes']} bytes)", flush=True)
                    emit('download','completed',province=province['province_zh'],message=document['display_name']+f" / {result['bytes']} bytes")
                    for output in result['outputs']:
                        print(f"    {output['status']}: {output['path']}", flush=True)
                except Exception as exc:
                    record["errors"].append({"document": document["display_name"], "error": str(exc)})
                    print(f"  ERROR {document['display_name']}: {exc}", flush=True)
                    emit('download','failed',province=province['province_zh'],message=document['display_name'],error=str(exc)[:400])
            results.append(record)
            emit('download',kind='region',province=province['province_zh'],region_state='failed' if record['errors'] else 'complete' if record['documents'] else 'not_detected',message='来源目录已检查',completed=len(results),total=sum(not selected or p['province'].casefold() in selected for p in catalog['provinces']))
    finally:
        client.close()

    report = {
        "schema_version": 1,
        "started_at": started,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "check_only": args.check_only,
        "province_count": len(results),
        "successful_documents": sum(len(item["documents"]) for item in results),
        "failed_documents": sum(len(item["errors"]) for item in results),
        "provinces": results,
    }
    if not args.check_only:
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        check_report = TEMPLATE_ROOT / '_acquisition' / 'catalog-checks' / (datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.json')
        check_report.parent.mkdir(parents=True, exist_ok=True)
        check_report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f'检查记录（未替换生产模板）：{check_report}', flush=True)
    print(json.dumps({key: report[key] for key in ("province_count", "successful_documents", "failed_documents")}, ensure_ascii=False), flush=True)
    emit('job','failed' if report['failed_documents'] else 'complete_with_gaps' if any(not r['documents'] for r in results) else 'complete',message='来源目录检查结束',counts={k:report[k] for k in ('province_count','successful_documents','failed_documents')})
    return 1 if report["failed_documents"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
