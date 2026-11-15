from io import BytesIO
import os
from pathlib import Path
from unittest import TestCase, skipUnless
from urllib.parse import unquote

from docx import Document


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = os.environ.get("BAIHE_EMPLOYER_LAYOUT_SOURCE")
VALUES = {
    "applicant_company": "虚构用人单位",
    "applicant_representative": "虚构负责人",
    "applicant_address": "虚构地址",
    "applicant_contact": "00000000",
    "respondent": "虚构被申请人",
    "requests": ["虚构请求甲", "虚构请求乙"],
    "facts": ["虚构事实甲", "虚构事实乙", "虚构事实丙"],
}


class BaiheEmployerApplicationTests(TestCase):
    def test_limits_reject_manual_fields_and_malformed_values(self):
        from regional_baihe_application import BaiheEmployerApplicationRequest, fill_application

        for payload in (
            {"signature": "虚构公章"}, {"date": "2026-11-15"}, {"applicant_id": "000"},
            {"applicant_company": "甲\n乙"}, {"respondent": "甲" * 50}, {"facts": ["甲"] * 4},
            {"requests": ["甲\u0000乙"]}, {"facts": "不接受字符串"}, {"applicant_contact": 0},
        ):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                BaiheEmployerApplicationRequest.model_validate(payload)
        with self.assertRaises(ValueError):
            fill_application(b"unrelated", {})

    @skipUnless(FIXTURE, "The verified employer conversion is retained in private evidence")
    def test_fills_only_baihe_fields_and_keeps_signature_and_date(self):
        from regional_baihe_application import fill_application

        raw = Path(FIXTURE).read_bytes()
        before = Document(BytesIO(raw))
        filled = fill_application(raw, VALUES)
        for index, field in enumerate(("applicant_company", "applicant_representative", "applicant_address", "applicant_contact", "respondent"), 2):
            self.assertEqual(filled.paragraphs[index].text, before.paragraphs[index].text + VALUES[field])
        for index, expected in ((9, VALUES["requests"]), (11, VALUES["facts"])):
            self.assertEqual(filled.paragraphs[index].text, "\n".join(expected))
        for index in (0, 8, 10, 15, 16):
            self.assertEqual(filled.paragraphs[index]._p.xml, before.paragraphs[index]._p.xml)
        self.assertFalse(filled.core_properties.author)
        self.assertFalse(filled.core_properties.last_modified_by)

    def test_guide_keeps_worker_signature_conflict_out_of_generation(self):
        from regional_baihe_application import TEMPLATE_ID, staged_guide

        guide = staged_guide(ROOT)
        self.assertEqual((guide["city"], guide["district"], guide["region_code"]), ("安康市", "白河县", "610929"))
        self.assertEqual([m["service_object"] for m in guide["materials"]], ["劳动者"] * 6 + ["用人单位"] * 4)
        self.assertFalse(guide["published"])
        self.assertFalse(guide["can_generate"])
        self.assertIn("盖章", next(m for m in guide["materials"] if m["id"] == "610929-worker-application")["instructions"])
        self.assertEqual([t["id"] for t in guide["templates"] if t["official_kind"] == "blank" and t["service_object"] == "用人单位"],
                         [TEMPLATE_ID, "ankang-610929-employer-representative", "ankang-610929-employer-authorization"])

    @skipUnless(FIXTURE, "The verified employer conversion is retained in private evidence")
    def test_contract_and_download_bind_employer_only_to_exact_baihe_source(self):
        from tempfile import TemporaryDirectory
        from unittest.mock import patch

        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from regional_baihe_application import LAYOUT, PROOF, TEMPLATE_ID, staged_application_candidate
        from regional_guides import RegionalStore
        from routes import regional_guides as routes

        root = Path(self.enterContext(TemporaryDirectory()))
        for name in (PROOF, LAYOUT):
            (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / PROOF).write_bytes((ROOT / PROOF).read_bytes())
        (root / LAYOUT).write_bytes(Path(FIXTURE).read_bytes())
        store = RegionalStore(root / "guides.sqlite")
        guide = store.put_guide(staged_application_candidate(root))
        selected = {k: guide[k] for k in ("province", "city", "district", "version", "source_id")}
        app = FastAPI()
        app.include_router(routes.router, prefix="/regional")
        self.enterContext(patch.object(routes, "ROOT", root))
        self.enterContext(patch.object(routes, "store", return_value=store))
        self.enterContext(patch.dict(os.environ, {"LABOURLAWYER_DATA_DIR": str(root / "data")}))
        client = self.enterContext(TestClient(app))
        bound = {**selected, "kind": "application", "template_id": TEMPLATE_ID}
        response = client.get("/regional/form-contract", params=bound)
        self.assertEqual(response.status_code, 200, response.text)
        contract = response.json()
        self.assertEqual(contract["context"]["mode"], "blank")
        self.assertEqual({f["key"] for f in contract["fields"]}, set(VALUES))
        payload = {**bound, "contract_id": contract["contract_id"], "mode": "blank", "data": VALUES}
        for wrong in ({"contract_id": None}, {"mode": "reference_adaptation"}, {"version": 0},
                      {"source_id": "other"}, {"kind": "evidence"}, {"district": "镇坪县"},
                      {"template_id": "ankang-610929-worker-application"}):
            with self.subTest(wrong=wrong):
                self.assertEqual(client.post("/regional/generate", json={**payload, **wrong}).status_code, 409)
        output = client.post("/regional/generate", json=payload)
        self.assertEqual(output.status_code, 200, output.text if not output.is_success else "")
        self.assertIn("依据官方DOC转换填写.docx", unquote(output.headers["content-disposition"]))
        self.assertEqual(output.headers["x-document-origin"], "official-blank-converted-filled")
        self.assertIn(VALUES["applicant_company"], Document(BytesIO(output.content)).paragraphs[2].text)
        self.assertEqual(client.get(f"/regional/templates/{TEMPLATE_ID}", params=bound).status_code, 404)
        (root / LAYOUT).write_bytes(b"changed")
        self.assertEqual(client.get("/regional/form-contract", params=bound).status_code, 409)
