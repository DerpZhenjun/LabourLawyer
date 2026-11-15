from io import BytesIO
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, skipUnless
from unittest.mock import patch

from docx import Document
from fastapi import FastAPI
from fastapi.testclient import TestClient

from regional_guides import RegionalStore
from routes import regional_guides as routes


ROOT = Path(__file__).resolve().parents[2]
PRIVATE = os.environ.get("LABOURLAWYER_TONGGUAN_LAYOUT_REVIEW")
DATA = {
    "request_one": "核对测试事项甲",
    "request_two": "核对测试事项乙",
    "facts": "本段为虚构版式验收文本",
    "evidence_one": "虚构证据名称及来源甲",
    "evidence_two": "虚构证据名称及来源乙",
}


class TongguanRoleApplicationTests(TestCase):
    def test_guide_keeps_exact_role_sources_without_enabling_generation(self):
        from regional_tongguan_application import staged_guide

        guide = staged_guide(ROOT)
        self.assertEqual((guide["city"], guide["district"], guide["region_code"]), ("渭南市", "潼关县", "610522"))
        self.assertFalse(guide["can_generate"])
        self.assertFalse(guide["published"])
        self.assertIn("408室", guide["fields"]["办理地点"])
        self.assertIn("0 个工作日", guide["fields"]["承诺办结时限"])
        self.assertEqual([m["service_object"] for m in guide["materials"]], ["劳动者"] * 5 + ["用人单位"] * 4)
        templates = guide["templates"]
        self.assertEqual([t["service_object"] for t in templates], ["劳动者", "用人单位"])
        self.assertEqual(len({t["official_sha256"] for t in templates}), 2)
        for template in templates:
            self.assertEqual(template["guide_source_url"], guide["role_sources"][template["service_object"]])
            self.assertEqual(template["download_status"], "official_link_only")
            self.assertFalse(template["can_generate"])

    def test_model_rejects_capacity_excess_controls_and_manual_fields(self):
        from regional_tongguan_application import TongguanApplicationRequest

        self.assertEqual(TongguanApplicationRequest.model_validate({"facts": "  版式核验  "}).facts, "版式核验")
        for invalid in (
            {"signature": "姓名"}, {"applicant_name": "姓名"}, {"application_date": "2026-11-16"},
            {"recipient": "其他机构"}, {"facts": "同一行\n下一行"}, {"request_two": "宽" * 30},
            {"evidence_one": "\u0000"}, {"request_one": 1}, {"request_one": "宽" * 16},
        ):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                TongguanApplicationRequest.model_validate(invalid)

    @skipUnless(PRIVATE, "Reviewed Word conversions are retained in local evidence")
    def test_only_body_slots_change_in_both_role_layouts(self):
        from regional_tongguan_application import fill_application

        directory = Path(PRIVATE)
        worker = (directory / "610522-WORKER-APPLICATION-PORTAL-BLANK-ORIGINAL-converted.docx").read_bytes()
        employer = (directory / "610522-EMPLOYER-APPLICATION-PORTAL-BLANK-ORIGINAL-converted.docx").read_bytes()
        for role, layout, other in (("worker", worker, employer), ("employer", employer, worker)):
            with self.subTest(role=role):
                original = Document(BytesIO(layout))
                output = fill_application(role, layout, DATA)
                self.assertEqual(len(output.paragraphs), len(original.paragraphs))
                for index, field in ((5, "request_one"), (6, "request_two"), (9, "facts"),
                                     (11, "evidence_one"), (12, "evidence_two")):
                    self.assertEqual(output.paragraphs[index].text, original.paragraphs[index].text + DATA[field])
                    source_mark = original.paragraphs[index]._p.xpath("./w:pPr/w:rPr/w:sz")[0]
                    added_size = output.paragraphs[index].runs[-1]._r.xpath("./w:rPr/w:sz")[0]
                    self.assertEqual(dict(added_size.attrib), dict(source_mark.attrib))
                for index in set(range(19)) - {5, 6, 9, 11, 12}:
                    self.assertEqual(output.paragraphs[index]._p.xml, original.paragraphs[index]._p.xml)
                blank = fill_application(role, layout, {})
                self.assertEqual([p._p.xml for p in blank.paragraphs], [p._p.xml for p in original.paragraphs])
                with self.assertRaises(ValueError):
                    fill_application(role, other, DATA)

    @skipUnless(PRIVATE, "Reviewed Word conversions are retained in local evidence")
    def test_actual_routes_require_separate_role_contracts_and_pinned_bytes(self):
        from regional_tongguan_application import LAYOUTS, SOURCE, staged_application_candidate

        root = Path(self.enterContext(TemporaryDirectory()))
        layouts = Path(PRIVATE)
        files = {SOURCE: ROOT / SOURCE}
        for role, relative in LAYOUTS.items():
            files[relative] = layouts / f"610522-{role.upper()}-APPLICATION-PORTAL-BLANK-ORIGINAL-converted.docx"
        for relative, source in files.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(source.read_bytes())
        store = RegionalStore(root / "guides.sqlite")
        guide = store.put_guide(staged_application_candidate(root))
        app = FastAPI()
        app.include_router(routes.router, prefix="/regional")
        self.enterContext(patch.object(routes, "ROOT", root))
        self.enterContext(patch.object(routes, "store", return_value=store))
        self.enterContext(patch.dict(os.environ, {"LABOURLAWYER_DATA_DIR": str(root / "private")}))
        client = self.enterContext(TestClient(app))
        context = {k: guide[k] for k in ("province", "city", "district", "source_id", "version")}
        payloads = []
        for role, template in zip(("worker", "employer"), guide["templates"], strict=True):
            bound = {**context, "template_id": template["id"], "kind": "application"}
            response = client.get("/regional/form-contract", params=bound)
            self.assertEqual(response.status_code, 200, response.text)
            contract = response.json()
            self.assertEqual({field["key"] for field in contract["fields"]}, set(DATA))
            payload = {**bound, "contract_id": contract["contract_id"], "mode": "blank", "data": DATA}
            payloads.append(payload)
            output = client.post("/regional/generate", json=payload)
            self.assertEqual(output.status_code, 200, output.text if not output.is_success else "")
            self.assertEqual(output.headers["x-document-origin"], "official-blank-converted-filled")
            self.assertEqual(output.headers["x-form-contract-id"], contract["contract_id"])
            generated = Document(BytesIO(output.content))
            original = Document(root / LAYOUTS[role])
            self.assertEqual(generated.paragraphs[2]._p.xml, original.paragraphs[2]._p.xml)
            self.assertEqual(generated.paragraphs[17]._p.xml, original.paragraphs[17]._p.xml)
            self.assertEqual(client.get(f'/regional/templates/{template["id"]}', params=bound).status_code, 404)
        worker, employer = payloads
        self.assertNotEqual(worker["contract_id"], employer["contract_id"])
        for change in (
            {"template_id": employer["template_id"]}, {"contract_id": None},
            {"district": "临渭区"}, {"mode": "reference_adaptation"}, {"kind": "evidence"},
        ):
            with self.subTest(change=change):
                self.assertEqual(client.post("/regional/generate", json={**worker, **change}).status_code, 409)
        self.assertEqual(client.post("/regional/generate", json={**worker, "data": {"facts": "宽" * 55}}).status_code, 422)
        (root / LAYOUTS["worker"]).write_bytes((root / LAYOUTS["employer"]).read_bytes())
        bound = {k: v for k, v in worker.items() if k not in {"contract_id", "data", "mode"}}
        self.assertEqual(client.get("/regional/form-contract", params=bound).status_code, 409)
