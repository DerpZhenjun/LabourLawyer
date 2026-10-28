from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SourceConfig:
    province: str
    adapter: str
    guide_url: str
    allowed_domains: tuple[str, ...]
    options: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TemplateCandidate:
    document_type: str
    display_name: str
    download_url: str
    source_url: str
    production_path: str | None = None
    file_format: str = "docx"
    original_path: str | None = None


@dataclass
class StoredArtifact:
    province: str
    document_type: str
    display_name: str
    source_url: str
    download_url: str
    sha256: str
    structure_fingerprint: str
    path: Path
    status: str
    validation: dict[str, Any]


@dataclass
class AcquisitionResult:
    run_id: str
    province: str
    status: str
    artifacts: list[StoredArtifact] = field(default_factory=list)
    guide_snapshot: Path | None = None
    screenshot: Path | None = None
    vision_report: Path | None = None
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
