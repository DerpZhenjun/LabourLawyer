"""Protect fresh-byte checks between requests while reusing one request's proof."""

from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import importlib
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient


class RegionalEvidenceSessionTests(TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec("regional_evidence_session"),
                             "Request-scoped evidence reuse is missing")
        self.module = importlib.import_module("regional_evidence_session")
        self.root = Path(self.enterContext(TemporaryDirectory()))
        (self.root / "source.json").write_bytes(b"pinned public source")
        self.pin = sha256(b"pinned public source").hexdigest()
        self.reads = []

        @self.module.evidence_once
        def proof(root):
            raw = (root / "source.json").read_bytes()
            self.reads.append(root)
            if sha256(raw).hexdigest() != self.pin:
                raise ValueError("Source bytes changed")
            return {"source": raw, "labels": []}

        self.proof = proof
        app = FastAPI()

        @app.get("/proof", dependencies=[Depends(self.module.evidence_validation_scope)])
        def route():
            first = proof(self.root)
            first["labels"].append("caller mutation")
            second = proof(self.root)
            return {"identical": first["source"] == second["source"], "labels": second["labels"]}

        self.client = self.enterContext(TestClient(app, raise_server_exceptions=False))

    def test_one_request_reuses_proof_and_returns_independent_values(self):
        response = self.client.get("/proof")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"identical": True, "labels": []})
        self.assertEqual(len(self.reads), 1)

    def test_next_request_detects_changed_file_even_with_same_size_and_timestamp(self):
        self.assertEqual(self.client.get("/proof").status_code, 200)
        path = self.root / "source.json"
        original_stat = path.stat()
        changed = b"tampered".ljust(len(b"pinned public source"), b" ")
        path.write_bytes(changed)
        import os
        os.utime(path, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns))
        self.assertEqual(self.client.get("/proof").status_code, 500)

    def test_calls_outside_request_scope_keep_fresh_verification(self):
        self.proof(self.root)
        self.proof(self.root)
        self.assertEqual(len(self.reads), 2)

    def test_concurrent_requests_never_share_validation_results(self):
        with ThreadPoolExecutor(max_workers=4) as executor:
            responses = list(executor.map(lambda _: self.client.get("/proof"), range(4)))
        self.assertTrue(all(response.status_code == 200 for response in responses))
        self.assertEqual(len(self.reads), 4)

    def test_source_roots_and_failed_attempts_stay_distinct(self):
        other = self.root / "other"
        other.mkdir()
        (other / "source.json").write_bytes(b"different source")
        app = FastAPI()

        @app.get("/recover", dependencies=[Depends(self.module.evidence_validation_scope)])
        def route():
            self.proof(self.root)
            rejected = False
            try:
                self.proof(other)
            except ValueError:
                rejected = True
            (other / "source.json").write_bytes(b"pinned public source")
            recovered = self.proof(other)
            return {"other_root_rejected": rejected, "recovered": recovered["source"].decode()}

        with TestClient(app) as client:
            self.assertEqual(client.get("/recover").json(), {
                "other_root_rejected": True, "recovered": "pinned public source"})
        self.assertEqual(len(self.reads), 3)

    def test_invalid_typed_argument_cannot_reuse_a_valid_same_request_result(self):
        @self.module.evidence_once
        def stage_receipt(stage):
            if type(stage) is not bool:
                raise ValueError("Invalid stage type")
            return {"stage": stage}

        app = FastAPI()

        @app.get("/stage", dependencies=[Depends(self.module.evidence_validation_scope)])
        def route():
            stage_receipt(True)
            try:
                stage_receipt(1)
            except ValueError:
                return {"invalid_stage_rejected": True}
            return {"invalid_stage_rejected": False}

        with TestClient(app) as client:
            self.assertEqual(client.get("/stage").json(), {"invalid_stage_rejected": True})

    def test_installation_is_idempotent_and_preserves_provider_file_bytes(self):
        import regional_fujian_oct31j as provider
        path = Path(provider.__file__)
        original = path.read_bytes()
        self.module.install_provider_evidence_reuse()
        first = provider._word_manifest
        self.module.install_provider_evidence_reuse()
        self.assertIs(provider._word_manifest, first)
        self.assertTrue(getattr(first, "_regional_evidence_once", False))
        self.assertEqual(path.read_bytes(), original)
