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
FIXTURE = os.environ.get("DANFENG_WORKER_LAYOUT_SOURCE")
DATA = {
    "applicant_name": "虚构申请人", "sex": "男", "ethnicity": "汉",
    "birth_date": "1990-01-02", "origin": "虚构县",
    "home_address": "虚构甲路", "phone": "00000000", "mail_address": "虚构乙路", "postcode": "000000",
    "respondent": "虚构单位", "respondent_representative": "虚构负责人", "respondent_position": "负责人",
    "respondent_address": "虚构丙路", "respondent_phone": "00000001",
    "third_party": "虚构第三人", "third_party_representative": "虚构代理人", "third_party_position": "代表",
    "third_party_address": "虚构丁路", "third_party_phone": "00000002",
    "requests": ["虚构请求甲", "虚构请求乙"], "facts": ["虚构事实甲", "虚构事实乙"],
}


class DanfengWorkerApplicationTests(TestCase):
    def test_role_mismatch_keeps_employer_from_generation(self):
        from regional_danfeng_application import TEMPLATE_ID, staged_guide

        guide = staged_guide(ROOT)
        self.assertEqual((guide["city"], guide["district"], guide["region_code"]), ("商洛市", "丹凤县", "611022"))
        self.assertEqual([m["service_object"] for m in guide["materials"]], ["劳动者"] * 5 + ["用人单位"] * 6)
        self.assertIn("四楼", guide["fields"]["办理地点"])
        self.assertEqual(len(guide["role_sources"]), 2)
        self.assertEqual([(t["id"], t["service_object"], t["can_generate"]) for t in guide["templates"]],
                         [(TEMPLATE_ID, "劳动者", False)])
        self.assertFalse(guide["published"])

    def test_invalid_or_manual_fields_are_rejected(self):
        from regional_danfeng_application import DanfengWorkerRequest, fill_application

        for payload in (
            {"signature": "虚构签名"}, {"recipient_prefix": "其他地区"}, {"date": "2026-11-15"},
            {"applicant_company": "虚构公司"}, {"birth_date": "2001-02-29"}, {"applicant_name": "甲\n乙"},
            {"mail_address": "甲" * 20}, {"facts": ["甲"] * 3}, {"requests": ["甲\u0000乙"]},
        ):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                DanfengWorkerRequest.model_validate(payload)
        with self.assertRaises(ValueError):
            fill_application(b"other document", {})

    @skipUnless(FIXTURE, "The exact source is stored in private evidence")
    def test_fills_exact_document_without_touching_recipient_and_signature(self):
        from regional_danfeng_application import fill_application

        raw = Path(FIXTURE).read_bytes()
        original = Document(BytesIO(raw))
        document = fill_application(raw, DATA)
        text = "\n".join(p.text for p in document.paragraphs)
        for name, value in DATA.items():
            if isinstance(value, list):
                for line in value:
                    self.assertIn(line, text)
            elif name != "birth_date":
                self.assertIn(value, text)
        self.assertIn("1990年01月02日", document.paragraphs[2].text)
        self.assertIn("1、虚构请求甲", document.paragraphs[15].text)
        self.assertIn("2、虚构请求乙", document.paragraphs[16].text)
        self.assertEqual(document.paragraphs[20].text, "虚构事实甲")
        self.assertEqual(document.paragraphs[21].text, "虚构事实乙")
        for index in (0, 13, 14, 17, 18, 19, 22, 23, 24, 25):
            self.assertEqual(document.paragraphs[index]._p.xml, original.paragraphs[index]._p.xml)

    @skipUnless(FIXTURE, "The exact source is stored in private evidence")
    def test_http_contract_and_generation_use_exact_worker_source_and_file(self):
        from regional_danfeng_application import LAYOUT, PROOF, TEMPLATE_ID, staged_application_candidate

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
        bound.update(kind="application", template_id=TEMPLATE_ID)
        contract_response = client.get("/regional/form-contract", params=bound)
        self.assertEqual(contract_response.status_code, 200, contract_response.text)
        contract = contract_response.json()
        self.assertEqual({f["key"] for f in contract["fields"]}, set(DATA))
        self.assertEqual(contract["context"]["mode"], "blank")
        payload = {**bound, "contract_id": contract["contract_id"], "mode": "blank", "data": DATA}
        generated = client.post("/regional/generate", json=payload)
        self.assertEqual(generated.status_code, 200, generated.text if not generated.is_success else "")
        self.assertEqual(generated.headers["x-document-origin"], "official-blank-filled")
        self.assertEqual(generated.headers["x-form-contract-id"], contract["contract_id"])
        self.assertIn(DATA["applicant_name"], Document(BytesIO(generated.content)).paragraphs[1].text)
        for update in ({"contract_id": None}, {"mode": "reference_adaptation"}, {"version": 0},
                       {"district": "洛南县"}, {"template_id": "shangluo-611022-employer-application"}):
            with self.subTest(update=update):
                self.assertEqual(client.post("/regional/generate", json={**payload, **update}).status_code, 409)
        self.assertEqual(client.get(f"/regional/templates/{TEMPLATE_ID}", params=bound).status_code, 404)
        (root / LAYOUT).write_bytes(b"changed")
        self.assertEqual(client.get("/regional/form-contract", params=bound).status_code, 409)
