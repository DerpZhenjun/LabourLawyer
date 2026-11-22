"""Pin cohort accounting and the long-text case that overflowed in preflight."""

import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase


PATH = Path(__file__).resolve().parents[2] / "scripts/benchmark-regional-template-reuse.py"
SPEC = importlib.util.spec_from_file_location("template_reuse_benchmark", PATH)
benchmark = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(benchmark)


class BenchmarkInputTests(TestCase):
    def test_reused_document_path_rejects_tampered_existing_bytes(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "output.docx"
            benchmark.save_document(path, b"synthetic approved document")
            self.assertEqual(path.read_bytes(), b"synthetic approved document")
            path.write_bytes(b"tampered")
            with self.assertRaises(ValueError):
                benchmark.save_document(path, b"synthetic approved document")

    def test_fixed_line_capacity_limits_long_synthetic_facts(self):
        contract = {
            "defaults": {"facts": ""},
            "fields": [{"key": "facts", "type": "text", "maxLength": 12000}],
            "policy": {"layout_limits": {"fields": {
                "facts": {"first_width": 56, "later_width": 56, "max_lines": 10}}}},
        }
        data = benchmark.payload(contract, "long")
        self.assertGreater(len(data["facts"]), 100)
        self.assertLessEqual(len(data["facts"]), 196)

    def test_cohort_spreads_provinces_and_refuses_to_replace_missing_regions(self):
        template = {"can_generate": True, "official_kind": "blank", "adapter": "fixture"}
        rows = [{"province": province, "region_code": code, "templates": [template]}
                for province, code in (("jiangsu", "320501"), ("jiangsu", "320502"),
                                       ("fujian", "350101"))]
        selected = benchmark.choose_regions(rows, 2)
        self.assertEqual([row["region_code"] for row in selected], ["350101", "320501"])
        with self.assertRaises(ValueError):
            benchmark.choose_regions(rows, 50)

    def test_sample_and_unadapted_annexes_do_not_enter_blank_cohort(self):
        guide = {"templates": [
            {"can_generate": True, "official_kind": "sample", "adapter": "fixture"},
            {"can_generate": False, "official_kind": "blank", "adapter": "fixture"},
        ]}
        self.assertEqual(benchmark.eligible_templates(guide), [])
