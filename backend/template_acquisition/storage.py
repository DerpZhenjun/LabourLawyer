from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from .models import AcquisitionResult, StoredArtifact, TemplateCandidate


class CandidateStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.database = self.root / "registry.sqlite3"
        self._init_database()

    def _connect(self):
        connection = sqlite3.connect(self.database)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_database(self) -> None:
        with closing(self._connect()) as db, db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY, province TEXT NOT NULL, started_at TEXT NOT NULL,
                    finished_at TEXT, status TEXT NOT NULL, errors_json TEXT NOT NULL DEFAULT '[]'
                );
                CREATE TABLE IF NOT EXISTS artifacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT NOT NULL, province TEXT NOT NULL,
                    document_type TEXT NOT NULL, display_name TEXT NOT NULL, source_url TEXT NOT NULL,
                    download_url TEXT NOT NULL, sha256 TEXT NOT NULL, structure_fingerprint TEXT NOT NULL,
                    path TEXT NOT NULL, status TEXT NOT NULL, validation_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(run_id) REFERENCES runs(run_id)
                );
                CREATE INDEX IF NOT EXISTS idx_artifact_latest
                    ON artifacts(province, document_type, id DESC);
                """
            )

    def begin_run(self, run_id: str, province: str) -> Path:
        run_dir = self.root / "runs" / run_id / province
        run_dir.mkdir(parents=True, exist_ok=False)
        with closing(self._connect()) as db, db:
            db.execute(
                "INSERT INTO runs(run_id, province, started_at, status) VALUES (?, ?, ?, ?)",
                (run_id, province, datetime.now(timezone.utc).isoformat(), "running"),
            )
        return run_dir

    def latest_sha(self, province: str, document_type: str) -> str | None:
        with closing(self._connect()) as db:
            row = db.execute(
                "SELECT sha256 FROM artifacts WHERE province=? AND document_type=? "
                "ORDER BY id DESC LIMIT 1",
                (province, document_type),
            ).fetchone()
        return row["sha256"] if row else None

    def save_artifact(
        self,
        run_id: str,
        province: str,
        run_dir: Path,
        candidate: TemplateCandidate,
        data: bytes,
        sha256: str,
        structure_fingerprint: str,
        validation: dict,
    ) -> StoredArtifact:
        previous_sha = self.latest_sha(province, candidate.document_type)
        status = "new" if previous_sha is None else "unchanged" if previous_sha == sha256 else "changed"
        path = run_dir / f"{candidate.document_type}-{sha256[:12]}.docx"
        path.write_bytes(data)
        artifact = StoredArtifact(
            province=province,
            document_type=candidate.document_type,
            display_name=candidate.display_name,
            source_url=candidate.source_url,
            download_url=candidate.download_url,
            sha256=sha256,
            structure_fingerprint=structure_fingerprint,
            path=path,
            status=status,
            validation=validation,
        )
        with closing(self._connect()) as db, db:
            db.execute(
                """INSERT INTO artifacts(
                    run_id, province, document_type, display_name, source_url, download_url,
                    sha256, structure_fingerprint, path, status, validation_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    run_id, province, candidate.document_type, candidate.display_name,
                    candidate.source_url, candidate.download_url, sha256, structure_fingerprint,
                    str(path), status, json.dumps(validation, ensure_ascii=False),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
        return artifact

    def finish_run(self, result: AcquisitionResult) -> Path:
        with closing(self._connect()) as db, db:
            db.execute(
                "UPDATE runs SET finished_at=?, status=?, errors_json=? WHERE run_id=?",
                (
                    datetime.now(timezone.utc).isoformat(), result.status,
                    json.dumps({"warnings": result.warnings, "errors": result.errors}, ensure_ascii=False), result.run_id,
                ),
            )
        report = self.root / "runs" / result.run_id / result.province / "report.json"
        report.write_text(
            json.dumps(
                {
                    "run_id": result.run_id,
                    "province": result.province,
                    "status": result.status,
                    "artifacts": [
                        {
                            "document_type": item.document_type,
                            "display_name": item.display_name,
                            "status": item.status,
                            "sha256": item.sha256,
                            "structure_fingerprint": item.structure_fingerprint,
                            "path": str(item.path),
                            "source_url": item.source_url,
                            "download_url": item.download_url,
                            "validation": item.validation,
                        }
                        for item in result.artifacts
                    ],
                    "guide_snapshot": str(result.guide_snapshot) if result.guide_snapshot else None,
                    "screenshot": str(result.screenshot) if result.screenshot else None,
                    "vision_report": str(result.vision_report) if result.vision_report else None,
                    "warnings": result.warnings,
                    "errors": result.errors,
                    "promotion": (
                        "written_to_production"
                        if any(item.validation.get("matches_production_after_write") for item in result.artifacts)
                        else "check_only"
                    ),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return report
