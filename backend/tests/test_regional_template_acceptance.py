"""Regression coverage for source-scoped reuse of document QA evidence."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from hashlib import sha256
import importlib
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase


class TemplateAcceptanceTests(TestCase):
    def setUp(self):
        name = "regional_template_acceptance"
        self.assertIsNotNone(importlib.util.find_spec(name), "Template QA reuse is missing")
        self.module = importlib.import_module(name)
        self.root = Path(self.enterContext(TemporaryDirectory()))
        (self.root / "original.docx").write_bytes(b"public original")
        self.evidence = self.root / "review.json"
        self.evidence.write_bytes(b'{"status":"PASS","synthetic":true}')
        self.template = {
            "id": "own-annex", "region_code": "320507", "file": "original.docx",
            "sha256": sha256(b"public original").hexdigest(), "official_kind": "blank",
            "can_generate": True, "adapter": "fixture", "document_types": ["application"],
        }
        self.guide = {
            "province": "jiangsu", "city": "苏州市", "district": "相城区",
            "region_code": "320507", "source_id": "own-source", "version": 1,
            "source_url": "https://fixture.gov.cn/xiangcheng", "templates": [self.template],
        }
        self.contract = {
            "context": {key: self.guide[key] for key in (
                "province", "city", "district", "region_code", "source_id", "version")},
            "fields": [{"key": "name", "maxLength": 30}], "defaults": {"name": ""},
            "policy": {"unknown_fields": "reject"},
        }
        self.contract["context"].update(template_id="own-annex", kind="application", mode="blank")
        self.store = self.module.AcceptanceStore(self.root / "qa.sqlite", root=self.root)

    def review(self, **overrides):
        arguments = dict(guide=self.guide, template=self.template, contract=self.contract,
                         output=b"synthetic filled document", renderer_sha256="a" * 64,
                         reviewer_version="qa-v1", scenario="normal", reviewer=self.accept)
        arguments.update(overrides)
        return self.store.review(**arguments)

    def accept(self, output):
        return {"status": "PASS", "artifacts": [{
            "path": "review.json", "sha256": sha256(self.evidence.read_bytes()).hexdigest(),
        }]}

    def test_identical_own_bound_templates_reuse_one_technical_review(self):
        first = self.review()
        guide, template, contract = deepcopy((self.guide, self.template, self.contract))
        guide.update(district="吴江区", region_code="320509", source_id="another-own-source")
        template["region_code"] = "320509"
        guide["templates"] = [template]
        contract["context"].update(district="吴江区", region_code="320509", source_id="another-own-source")
        second = self.review(guide=guide, template=template, contract=contract,
                             reviewer=lambda _: self.fail("Identical content was reviewed again"))
        self.assertFalse(first["reused"])
        self.assertTrue(second["reused"])
        self.assertEqual(first["key"], second["key"])

    def test_cross_region_contract_and_template_cannot_hit_cached_review(self):
        self.review()
        for field, value in (("district", "吴江区"), ("source_id", "other"), ("version", 2)):
            contract = deepcopy(self.contract)
            contract["context"][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.review(contract=contract)
        template = {**self.template, "region_code": "320509"}
        with self.assertRaises(ValueError):
            self.review(template=template)

    def test_changed_original_output_schema_renderer_or_scenario_requires_review(self):
        initial = self.review()
        schema = deepcopy(self.contract)
        schema["fields"][0]["maxLength"] = 20
        changes = [dict(output=b"changed result"), dict(contract=schema),
                   dict(renderer_sha256="b" * 64), dict(reviewer_version="qa-v2"),
                   dict(scenario="long")]
        for change in changes:
            with self.subTest(change=change):
                result = self.review(**change)
                self.assertFalse(result["reused"])
                self.assertNotEqual(initial["key"], result["key"])
        (self.root / "original.docx").write_bytes(b"changed original")
        with self.assertRaises(ValueError):
            self.review()

    def test_missing_tampered_or_escaped_review_evidence_cannot_reuse(self):
        self.review()
        self.evidence.write_bytes(b"tampered")
        repaired = self.review()
        self.assertFalse(repaired["reused"])
        self.evidence.unlink()
        with self.assertRaises(ValueError):
            self.review(reviewer=lambda _: {"status": "PASS", "artifacts": [
                {"path": "review.json", "sha256": "0" * 64}]})
        with self.assertRaises(ValueError):
            self.review(reviewer=lambda _: {"status": "PASS", "artifacts": [
                {"path": "../escaped.json", "sha256": "0" * 64}]})

    def test_failed_review_is_retryable_and_never_a_cache_hit(self):
        with self.assertRaises(ValueError):
            self.review(reviewer=lambda _: {"status": "FAIL", "artifacts": []})
        self.assertFalse(self.review()["reused"])
        self.assertTrue(self.review()["reused"])

    def test_concurrent_reviews_publish_one_consistent_receipt(self):
        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(lambda _: self.review(), range(4)))
        self.assertEqual(sum(not row["reused"] for row in results), 1)
        self.assertEqual(len({row["key"] for row in results}), 1)

    def test_dedup_manifest_keeps_all_sources_and_rejects_changed_bytes(self):
        other = deepcopy(self.guide)
        other.update(district="吴江区", region_code="320509", source_id="another-own-source")
        other["templates"][0]["region_code"] = "320509"
        result = self.module.template_families([self.guide, other], self.root)
        self.assertEqual(len(result["families"]), 1)
        self.assertEqual(len(result["families"][0]["bindings"]), 2)
        self.assertEqual(result["invalid"], [])
        (self.root / "original.docx").write_bytes(b"changed original")
        result = self.module.template_families([self.guide, other], self.root)
        self.assertEqual(result["families"], [])
        self.assertEqual(len(result["invalid"]), 2)
