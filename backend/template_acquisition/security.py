from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass
from urllib.parse import urlparse

from defusedxml.ElementTree import fromstring


MAX_DOWNLOAD_BYTES = 25 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 150 * 1024 * 1024
MAX_ZIP_MEMBERS = 2_000
MAX_COMPRESSION_RATIO = 150


@dataclass(frozen=True)
class DocxValidation:
    member_count: int
    compressed_bytes: int
    uncompressed_bytes: int

    def as_dict(self) -> dict[str, int | bool]:
        return {
            "valid_docx": True,
            "member_count": self.member_count,
            "compressed_bytes": self.compressed_bytes,
            "uncompressed_bytes": self.uncompressed_bytes,
            "macros_present": False,
        }


def host_is_allowed(url: str, allowed_domains: tuple[str, ...]) -> bool:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        return False
    host = parsed.hostname.casefold().rstrip(".")
    return any(host == domain.casefold() or host.endswith("." + domain.casefold()) for domain in allowed_domains)


def validate_download_url(url: str, allowed_domains: tuple[str, ...]) -> None:
    if not host_is_allowed(url, allowed_domains):
        raise ValueError(f"Download URL is outside the official allowlist: {url}")


def validate_docx(data: bytes) -> DocxValidation:
    if not data.startswith(b"PK\x03\x04"):
        raise ValueError("Downloaded file is not an OOXML ZIP archive")
    if len(data) > MAX_DOWNLOAD_BYTES:
        raise ValueError("Downloaded file exceeds the 25 MiB limit")
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        infos = archive.infolist()
        if len(infos) > MAX_ZIP_MEMBERS:
            raise ValueError("DOCX contains too many ZIP members")
        names = {info.filename.casefold() for info in infos}
        if "[content_types].xml" not in names or "word/document.xml" not in names:
            raise ValueError("Archive is missing required DOCX parts")
        if any("vbaproject.bin" in name or name.endswith(".bin") for name in names):
            raise ValueError("Macro or binary payload detected in DOCX")
        total_uncompressed = sum(info.file_size for info in infos)
        total_compressed = max(sum(info.compress_size for info in infos), 1)
        if total_uncompressed > MAX_UNCOMPRESSED_BYTES:
            raise ValueError("DOCX expands beyond the safe size limit")
        if total_uncompressed / total_compressed > MAX_COMPRESSION_RATIO:
            raise ValueError("DOCX compression ratio is unsafe")
        content_types = archive.read("[Content_Types].xml")
        fromstring(content_types)
        if b"macroEnabled" in content_types:
            raise ValueError("Macro-enabled Office document rejected")
        fromstring(archive.read("word/document.xml"))
    return DocxValidation(len(infos), len(data), total_uncompressed)


def validate_legacy_doc(data: bytes) -> dict[str, int | bool]:
    if len(data) > MAX_DOWNLOAD_BYTES:
        raise ValueError("Downloaded legacy Word file exceeds the 25 MiB limit")
    if not data.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
        raise ValueError("Downloaded file is not a legacy Microsoft Compound Document")
    return {
        "valid_legacy_doc": True,
        "legacy_doc_bytes": len(data),
        "conversion_required": True,
    }
