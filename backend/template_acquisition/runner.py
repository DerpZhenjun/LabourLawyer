from __future__ import annotations

import asyncio
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from uuid import uuid4

from .adapters import ADAPTERS
from .browser import capture_guide
from .docx_analysis import analyze_docx, sha256_bytes
from .http_client import OfficialHttpClient
from .legacy_doc import convert_doc_to_docx
from .models import AcquisitionResult, SourceConfig
from .openclaw_bridge import describe_image
from .security import validate_docx, validate_legacy_doc
from .storage import CandidateStore


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUNTIME_ROOT = PROJECT_ROOT / "templates" / "_acquisition"


def _run_id(province: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{stamp}-{province}-{uuid4().hex[:8]}"


async def run_acquisition(
    source: SourceConfig,
    runtime_root: Path = DEFAULT_RUNTIME_ROOT,
    capture_browser: bool = True,
    use_vision: bool = True,
    promote: bool = True,
    progress: Callable[[str], None] | None = None,
) -> tuple[AcquisitionResult, Path]:
    def emit(message: str) -> None:
        if progress:
            progress(f"[{source.province}] {message}")

    store = CandidateStore(runtime_root)
    run_id = _run_id(source.province)
    run_dir = store.begin_run(run_id, source.province)
    result = AcquisitionResult(run_id=run_id, province=source.province, status="running")
    try:
        emit("正在读取官方办事指南接口…")
        adapter_type = ADAPTERS[source.adapter]
        async with OfficialHttpClient(
            source.allowed_domains,
            legacy_tls=bool(source.options.get("legacy_tls", False)),
        ) as client:
            candidates, guide_data = await adapter_type(source, client).discover()
            emit(f"已找到 {len(candidates)} 份官方空白模板。")
            guide_snapshot = run_dir / "official-api-response.json"
            guide_snapshot.write_text(json.dumps(guide_data, ensure_ascii=False, indent=2), encoding="utf-8")
            result.guide_snapshot = guide_snapshot
            for candidate in candidates:
                emit(f"正在下载：{candidate.display_name}")
                downloaded_data = await client.download(candidate.download_url)
                legacy_validation = {}
                if candidate.file_format == "doc":
                    legacy_validation = validate_legacy_doc(downloaded_data)
                    if not candidate.original_path or not candidate.production_path:
                        raise ValueError("Legacy DOC source requires original_path and production_path")
                    original_root = (PROJECT_ROOT / "templates" / "_original").resolve()
                    original_path = (PROJECT_ROOT / candidate.original_path).resolve()
                    if not original_path.is_relative_to(original_root):
                        raise ValueError(f"Original template path escapes template root: {original_path}")
                    original_sha = sha256_bytes(downloaded_data)
                    previous_original_sha = sha256_bytes(original_path.read_bytes()) if original_path.is_file() else None
                    original_path.parent.mkdir(parents=True, exist_ok=True)
                    original_path.write_bytes(downloaded_data)
                    production_path_for_reuse = (PROJECT_ROOT / candidate.production_path).resolve()
                    if previous_original_sha == original_sha and production_path_for_reuse.is_file():
                        data = production_path_for_reuse.read_bytes()
                        legacy_validation["conversion_reused"] = True
                    else:
                        converted_path = run_dir / f"{candidate.document_type}-converted.docx"
                        await asyncio.to_thread(
                            convert_doc_to_docx,
                            original_path,
                            converted_path,
                            run_dir / "word-temp",
                        )
                        data = converted_path.read_bytes()
                        legacy_validation["conversion_reused"] = False
                    legacy_validation.update(
                        {
                            "official_original_path": str(original_path),
                            "official_original_sha256": original_sha,
                        }
                    )
                else:
                    data = downloaded_data
                safe_docx = validate_docx(data)
                fingerprint, document_stats = analyze_docx(data)
                validation = legacy_validation | safe_docx.as_dict() | document_stats
                incoming_sha = sha256_bytes(data)
                if candidate.production_path:
                    production_root = (PROJECT_ROOT / "templates" / "_docx").resolve()
                    production_path = (PROJECT_ROOT / candidate.production_path).resolve()
                    if not production_path.is_relative_to(production_root):
                        raise ValueError(f"Production template path escapes template root: {production_path}")
                    production_sha = sha256_bytes(production_path.read_bytes()) if production_path.is_file() else None
                    validation.update(
                        {
                            "production_path": str(production_path),
                            "production_sha256": production_sha,
                            "matches_production_before_write": production_sha == incoming_sha,
                        }
                    )
                    if promote:
                        archive_path = None
                        if production_path.is_file() and production_sha != incoming_sha:
                            archive_dir = PROJECT_ROOT / "templates" / "_archive" / source.province / candidate.document_type
                            archive_dir.mkdir(parents=True, exist_ok=True)
                            archive_path = archive_dir / (
                                f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{production_sha[:12]}.docx"
                            )
                            shutil.copy2(production_path, archive_path)
                        production_path.parent.mkdir(parents=True, exist_ok=True)
                        temporary = production_path.with_name(f".{production_path.name}.{uuid4().hex}.tmp")
                        temporary.write_bytes(data)
                        os.replace(temporary, production_path)
                        validation.update(
                            {
                                "production_action": "refreshed" if production_sha == incoming_sha else "replaced",
                                "matches_production_after_write": sha256_bytes(production_path.read_bytes()) == incoming_sha,
                                "archived_previous_path": str(archive_path) if archive_path else None,
                            }
                        )
                        emit(f"已写入生产模板：{production_path}")
                result.artifacts.append(
                    store.save_artifact(
                        run_id, source.province, run_dir, candidate, data,
                        incoming_sha, fingerprint, validation,
                    )
                )
        if capture_browser:
            emit("正在无头浏览器中保存办事指南截图（不会显示窗口）…")
            try:
                focus_terms = tuple(item.display_name for item in reversed(candidates)) + ("申报材料", "材料清单")
                result.screenshot, _ = await capture_guide(source.guide_url, run_dir, focus_terms)
            except Exception as exc:
                result.warnings.append(f"Headless guide snapshot failed: {type(exc).__name__}: {exc}")
        if use_vision and result.screenshot:
            emit("正在使用 OpenClaw + Qwen 进行截图复核，通常需要 10–60 秒…")
            vision_output = run_dir / "openclaw-qwen-vision.json"
            try:
                await asyncio.to_thread(
                    describe_image,
                    result.screenshot,
                    vision_output,
                    runtime_root / "openclaw",
                )
                result.vision_report = vision_output
            except Exception as exc:
                result.warnings.append(f"OpenClaw vision failed: {type(exc).__name__}: {exc}")
        result.status = "success_with_warnings" if result.warnings else "success"
        emit("采集完成。")
    except Exception as exc:
        result.status = "failed"
        result.errors.append(f"{type(exc).__name__}: {exc}")
        emit(f"采集失败：{type(exc).__name__}: {exc}")
    report = store.finish_run(result)
    return result, report
