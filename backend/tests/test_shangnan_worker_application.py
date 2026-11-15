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
FIXTURE = os.environ.get("SHANGNAN_WORKER_CONVERSION_SOURCE")
DATA = {
    "applicant_name": "虚构姓名", "sex": "女", "birth_date": "1990-01-02", "applicant_id": "000000000000000000",
    "ethnicity": "汉", "address": "虚构甲路", "phone": "00000000000", "postcode": "000001",
    "respondent": "虚构单位", "respondent_representative": "虚构负责人", "respondent_position": "代表",
    "respondent_address": "虚构乙路", "respondent_phone": "00000000001", "respondent_postcode": "000002",
    "third_party": "虚构第三人", "third_party_name": "虚构姓名丙", "third_party_representative": "虚构负责人丙",
    "third_party_position": "职务丙", "third_party_address": "虚构丙路", "third_party_phone": "00000000002",
    "third_party_postcode": "000003", "requests": "虚构请求", "facts": ["虚构事实甲", "虚构事实乙"],
}


class ShangnanWorkerApplicationTests(TestCase):
    def test_role_and_guide_provenance(self):
        from regional_shangnan_application import TEMPLATE_ID, staged_guide

        guide = staged_guide(ROOT)
        self.assertEqual((guide["city"], guide["district"], guide["region_code"]), ("商洛市", "商南县", "611023"))
        self.assertEqual([m["service_object"] for m in guide["materials"]], ["劳动者"] * 2 + ["用人单位"] * 2)
        self.assertEqual(len(guide["role_sources"]), 2)
        self.assertIn("507", guide["fields"]["办理地点"])
        self.assertIn("空表", guide["sections"]["官网附件核验"])
        self.assertFalse(guide["published"])
        self.assertFalse(guide["can_generate"])
        self.assertEqual([(t["id"], t["service_object"]) for t in guide["templates"]], [(TEMPLATE_ID, "劳动者")])

    def test_limits_and_manual_fields(self):
        from regional_shangnan_application import ShangnanWorkerRequest, fill_application

        for invalid in ({"signature": "签名"}, {"recipient": "其他地区"}, {"applicant_company": "用人单位"},
                        {"birth_date": "2023-02-29"}, {"phone": "甲\n乙"}, {"applicant_id": "0" * 19},
                        {"facts": ["甲"] * 3}, {"requests": "甲\u0000乙"}, {"respondent": 15}):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                ShangnanWorkerRequest.model_validate(invalid)
        with self.assertRaises(ValueError):
            fill_application(b"other", {})

    @skipUnless(FIXTURE, "Official conversion retained in private evidence")
    def test_uses_all_verified_slots_and_retains_signature_block(self):
        from regional_shangnan_application import fill_application

        raw = Path(FIXTURE).read_bytes()
        original = Document(BytesIO(raw))
        filled = fill_application(raw, DATA)
        content = "\n".join(p.text for p in filled.paragraphs)
        for key, value in DATA.items():
            if isinstance(value, list):
                for text in value:
                    self.assertIn(text, content)
            elif key != "birth_date":
                self.assertIn(value, content)
        self.assertIn("1990-01-02", filled.paragraphs[1].text)
        self.assertIn("虚构请求", filled.paragraphs[13].text)
        for index in (0, 16, 17, 18, 19):
            self.assertEqual(original.paragraphs[index]._p.xml, filled.paragraphs[index]._p.xml)

    @skipUnless(FIXTURE, "Official conversion retained in private evidence")
    def test_http_validation_and_word_generation(self):
        from regional_shangnan_application import LAYOUT, PROOF, TEMPLATE_ID, staged_application_candidate

        root = Path(self.enterContext(TemporaryDirectory()))
        for relative, evidence in ((PROOF, ROOT / PROOF), (LAYOUT, Path(FIXTURE))):
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(evidence.read_bytes())
        store = RegionalStore(root / "guides.sqlite")
        guide = store.put_guide(staged_application_candidate(root))
        app = FastAPI()
        app.include_router(routes.router, prefix="/regional")
        self.enterContext(patch.object(routes, "ROOT", root))
        self.enterContext(patch.object(routes, "store", return_value=store))
        self.enterContext(patch.dict(os.environ, {"LABOURLAWYER_DATA_DIR": str(root / "data")}))
        client = self.enterContext(TestClient(app))
        bound = {k: guide[k] for k in ("province", "city", "district", "source_id", "version")}
        bound.update(template_id=TEMPLATE_ID, kind="application")
        response = client.get("/regional/form-contract", params=bound)
        self.assertEqual(response.status_code, 200, response.text)
        contract = response.json()
        self.assertEqual({f["key"] for f in contract["fields"]}, set(DATA))
        payload = {**bound, "contract_id": contract["contract_id"], "mode": "blank", "data": DATA}
        for update in ({"contract_id": None}, {"district": "丹凤县"}, {"mode": "reference_adaptation"},
                       {"template_id": "shangluo-611023-employer-application"}, {"source_id": "province"}):
            with self.subTest(update=update):
                self.assertEqual(client.post("/regional/generate", json={**payload, **update}).status_code, 409)
        output = client.post("/regional/generate", json=payload)
        self.assertEqual(output.status_code, 200, output.text if not output.is_success else "")
        self.assertEqual(output.headers["x-document-origin"], "official-blank-converted-filled")
        self.assertEqual(output.headers["x-form-contract-id"], contract["contract_id"])
        self.assertIn(DATA["applicant_id"], Document(BytesIO(output.content)).paragraphs[2].text)
        self.assertEqual(client.get(f"/regional/templates/{TEMPLATE_ID}", params=bound).status_code, 404)
        (root / LAYOUT).write_bytes(b"changed")
        self.assertEqual(client.get("/regional/form-contract", params=bound).status_code, 409)
