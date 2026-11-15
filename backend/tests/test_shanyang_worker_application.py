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
FIXTURE = os.environ.get("SHANYANG_WORKER_LAYOUT_SOURCE")
DATA = {
    "applicant_name": "虚构甲", "sex": "女", "applicant_id": "000000000000000000", "birth_date": "1990-01-02",
    "ethnicity": "汉", "workplace": "虚构单位甲", "address": "虚构地址甲", "phone": "00000000000", "postcode": "000001",
    "respondent": "虚构单位乙", "respondent_representative": "虚构乙", "respondent_position": "负责人",
    "respondent_address": "虚构地址乙", "respondent_phone": "00000000001", "respondent_postcode": "000002",
    "third_party": "虚构丙", "third_party_representative": "虚构代理", "third_party_address": "虚构地址丙",
    "third_party_phone": "00000000002", "third_party_postcode": "000003",
    "requests": "虚构请求", "facts": "虚构事实",
}


class ShanyangWorkerApplicationTests(TestCase):
    def test_guide_preserves_role_specific_location_and_authorization(self):
        from regional_shanyang_application import TEMPLATE_ID, staged_guide

        guide = staged_guide(ROOT)
        self.assertEqual((guide["city"], guide["district"], guide["region_code"]), ("商洛市", "山阳县", "611024"))
        self.assertIn("G70", guide["fields"]["办理地点"])
        self.assertIn("北五楼", guide["fields"]["办理地点"])
        self.assertIn("核实", guide["fields"]["办理地点"])
        self.assertIn("0 个工作日", guide["fields"]["承诺办结时限"])
        self.assertEqual([m["required"] for m in guide["materials"] if "授权委托书" in m["official_name"]], ["非必要", "必要"])
        self.assertEqual(set(guide["role_sources"]), {"劳动者", "用人单位"})
        self.assertEqual([(t["id"], t["service_object"]) for t in guide["templates"]], [(TEMPLATE_ID, "劳动者")])
        self.assertFalse(guide["can_generate"])
        self.assertFalse(guide["published"])

    def test_technical_limits_and_protected_signature_fields(self):
        from regional_shanyang_application import ShanyangWorkerRequest, fill_application

        for invalid in ({"signature": "虚构签名"}, {"recipient": "虚构机关"}, {"copies": "4"},
                        {"applicant_id": "0" * 19}, {"birth_date": "2025-02-29"}, {"sex": "甲\n乙"},
                        {"facts": "甲" * 10_000}, {"requests": "甲\u0000乙"}, {"applicant_company": "虚构单位"}):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                ShanyangWorkerRequest.model_validate(invalid)
        with self.assertRaises(ValueError):
            fill_application(b"other", {})

    @skipUnless(FIXTURE, "Official source retained in private evidence")
    def test_fills_checked_slots_and_preserves_manual_fields(self):
        from regional_shanyang_application import fill_application

        source = Path(FIXTURE).read_bytes()
        original = Document(BytesIO(source))
        filled = fill_application(source, DATA)
        for key, value in DATA.items():
            self.assertIn(value, "\n".join(p.text for p in filled.paragraphs), key)
        self.assertIn(DATA["facts"], filled.paragraphs[2].text)
        self.assertIn(DATA["requests"], filled.paragraphs[21].text)
        self.assertIn("邮政编码：", filled.paragraphs[20].text)
        for i in (0, 1, 5, 17, 18, *range(22, 31)):
            self.assertEqual(original.paragraphs[i]._p.xml, filled.paragraphs[i]._p.xml)

    @skipUnless(FIXTURE, "Official source retained in private evidence")
    def test_worker_only_http_generation_requires_exact_binding(self):
        from regional_shanyang_application import LAYOUT, PROOF, TEMPLATE_ID, staged_application_candidate

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
                       {"template_id": "shangluo-611024-employer-application"}, {"source_id": "province"}):
            with self.subTest(update=update):
                self.assertEqual(client.post("/regional/generate", json={**payload, **update}).status_code, 409)
        output = client.post("/regional/generate", json=payload)
        self.assertEqual(output.status_code, 200, output.text if not output.is_success else "")
        self.assertEqual(output.headers["x-document-origin"], "official-blank-filled")
        self.assertEqual(output.headers["x-form-contract-id"], contract["contract_id"])
        self.assertIn(DATA["applicant_id"], Document(BytesIO(output.content)).paragraphs[4].text)
        self.assertEqual(client.get(f"/regional/templates/{TEMPLATE_ID}", params=bound).status_code, 404)
        (root / LAYOUT).write_bytes(b"changed")
        self.assertEqual(client.get("/regional/form-contract", params=bound).status_code, 409)
