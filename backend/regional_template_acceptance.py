"""Content-addressed QA evidence, with a fresh regional binding check per use.

This module stores technical review receipts in a separately supplied QA database.
Regional eligibility still comes from the existing source and generation routes.
The caller supplies synthetic QA outputs, never applicant documents or payloads.
"""

from collections import defaultdict
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
import re
import sqlite3


def content_digest(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(raw.encode("utf-8")).hexdigest()


def checked_file(root, relative, expected):
    if not isinstance(relative, str) or not relative:
        raise ValueError("Missing QA evidence path")
    path = Path(relative)
    target = (root / path).resolve()
    if path.is_absolute() or not target.is_relative_to(root):
        raise ValueError("QA evidence escaped its configured root")
    if not isinstance(expected, str) or not re.fullmatch(r"[a-f0-9]{64}", expected):
        raise ValueError("Invalid evidence digest")
    try:
        body = target.read_bytes()
    except OSError as exc:
        raise ValueError("QA evidence is unavailable") from exc
    if sha256(body).hexdigest() != expected:
        raise ValueError("QA evidence bytes changed")
    return body


def template_families(guides, root):
    """Group equal original bytes while retaining every regional source binding."""
    root = Path(root).resolve()
    families = defaultdict(list)
    invalid = []
    for guide in guides:
        for template in guide.get("templates", []):
            binding = {
                "region_code": guide.get("region_code"), "province": guide.get("province"),
                "city": guide.get("city"), "district": guide.get("district"),
                "source_id": guide.get("source_id"), "source_url": guide.get("source_url"),
                "template_id": template.get("id"), "file": template.get("file"),
                "official_kind": template.get("official_kind"), "adapter": template.get("adapter"),
                "document_types": template.get("document_types", []),
                "can_generate": template.get("can_generate") is True,
            }
            try:
                if template.get("region_code") != guide.get("region_code"):
                    raise ValueError("Template belongs to another region")
                checked_file(root, template.get("file"), template.get("sha256"))
            except ValueError as exc:
                invalid.append({**binding, "reason": str(exc)})
                continue
            families[template["sha256"]].append(binding)
    return {
        "families": [{"sha256": checksum, "bindings": bindings}
                     for checksum, bindings in sorted(families.items())],
        "invalid": invalid,
    }


class AcceptanceStore:
    def __init__(self, path, *, root):
        self.root = Path(root).resolve()
        self.path = Path(path).resolve()
        if not self.path.is_relative_to(self.root):
            raise ValueError("QA database must stay inside its configured root")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path, timeout=60)) as db, db:
            db.execute("""CREATE TABLE IF NOT EXISTS template_qa_receipts(
                review_key TEXT PRIMARY KEY, identity TEXT NOT NULL, receipt TEXT NOT NULL
            )""")

    def _binding(self, guide, template, contract):
        context = contract.get("context", {})
        for key in ("province", "city", "district", "region_code", "source_id", "version"):
            if not guide.get(key) or context.get(key) != guide[key]:
                raise ValueError("Current regional contract identity does not match")
        matches = [item for item in guide.get("templates", []) if item.get("id") == template.get("id")]
        kind = context.get("kind")
        if (matches != [template] or template.get("region_code") != guide["region_code"]
                or context.get("template_id") != template.get("id")
                or kind not in {"application", "evidence"}
                or kind not in template.get("document_types", [])
                or template.get("can_generate") is not True):
            raise ValueError("Current regional template binding does not match")
        official_kind = template.get("official_kind")
        expected_mode = "blank" if official_kind == "blank" else "reference_adaptation"
        if official_kind not in {"blank", "sample"} or context.get("mode") != expected_mode:
            raise ValueError("Official template classification does not match")
        checked_file(self.root, template.get("file"), template.get("sha256"))

    def _evidence_valid(self, receipt):
        artifacts = receipt.get("artifacts")
        if receipt.get("status") != "PASS" or not isinstance(artifacts, list) or not artifacts:
            return False
        try:
            for artifact in artifacts:
                checked_file(self.root, artifact["path"], artifact["sha256"])
        except (ValueError, KeyError, TypeError):
            return False
        return True

    def review(self, *, guide, template, contract, output, renderer_sha256,
               reviewer_version, scenario, reviewer):
        self._binding(guide, template, contract)
        if (not isinstance(output, bytes) or not output or not reviewer_version or not scenario
                or not re.fullmatch(r"[a-f0-9]{64}", renderer_sha256)):
            raise ValueError("Incomplete technical review identity")
        context = contract["context"]
        identity = {
            "schema_version": 1, "original_sha256": template["sha256"],
            "output_sha256": sha256(output).hexdigest(), "kind": context["kind"],
            "official_kind": template["official_kind"], "mode": context["mode"],
            "case_scope": context.get("case_scope"),
            "contract_shape": {key: contract[key] for key in ("fields", "defaults", "policy")},
            "renderer_sha256": renderer_sha256, "reviewer_version": reviewer_version,
            "scenario": scenario,
        }
        key = content_digest(identity)
        with closing(sqlite3.connect(self.path, timeout=60)) as db, db:
            # Serialize a missing review and its insert so concurrent retries publish one receipt.
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT identity,receipt FROM template_qa_receipts WHERE review_key=?", (key,)
            ).fetchone()
            if row is not None:
                try:
                    saved_identity, receipt = json.loads(row[0]), json.loads(row[1])
                    valid = saved_identity == identity and self._evidence_valid(receipt)
                except (ValueError, TypeError, AttributeError):
                    valid = False
                if valid:
                    return {"key": key, "reused": True, "receipt": receipt}
            receipt = reviewer(output)
            if not isinstance(receipt, dict) or not self._evidence_valid(receipt):
                raise ValueError("Review did not produce valid passing evidence")
            db.execute(
                "INSERT OR REPLACE INTO template_qa_receipts VALUES(?,?,?)",
                (key, json.dumps(identity, ensure_ascii=False, sort_keys=True),
                 json.dumps(receipt, ensure_ascii=False, sort_keys=True)),
            )
        return {"key": key, "reused": False, "receipt": receipt}
