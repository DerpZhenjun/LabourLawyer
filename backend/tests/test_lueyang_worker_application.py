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
from regional_hanzhong_guides import NINGQIANG_LUEYANG_PROOF, staged_guide
from routes import regional_guides as routes


ROOT = Path(__file__).resolve().parents[2]
FOLLOWUP = NINGQIANG_LUEYANG_PROOF.with_name("ATTACHMENT-FOLLOWUP.json")
FIXTURE = os.environ.get("LUEYANG_LAYOUT_SOURCE")
SCOPE = {"province": "shaanxi", "city": "汉中市", "district": "略阳县"}
DATA = {
    "applicant_name": "虚构甲",
    "applicant_birth_date": "虚构出生日期",
    "applicant_agent_name": "虚构申请方代理",
    "respondent_name": "虚构乙单位",
    "respondent_agent_name": "虚构被申请方代理",
    "cause": "虚构案由",
    "requests": ["第一项虚构请求", "", "第三项虚构请求"],
    "facts": "虚构事实第一段\n虚构事实第二段",
    "evidence": "虚构证据及来源",
}


class LueyangApplicationTests(TestCase):
    def test_payload_cannot_assign_signatures_or_use_employer_application_fields(self):
        from regional_lueyang_application import LueyangApplicationRequest, fill_application

        for invalid in ({"signature": "虚构签名"}, {"applicant_company": "虚构企业"},
                        {"applicant_name": "甲\n乙"}, {"requests": ["一"] * 4},
                        {"facts": "甲\x00乙"}, {"witness_name": "甲" * 90}):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                LueyangApplicationRequest.model_validate(invalid)
        with self.assertRaises(ValueError):
            fill_application(b"unverified Word file", {})

    @skipUnless(FIXTURE, "Lueyang's verified Word conversion is held in private evidence")
    def test_exact_worker_guide_fills_only_the_first_page_and_keeps_source_notes(self):
        from regional_lueyang_application import LAYOUT, TEMPLATE_ID, staged_application_candidate

        work = Path(self.enterContext(TemporaryDirectory()))
        for proof in (NINGQIANG_LUEYANG_PROOF, FOLLOWUP):
            (work / proof).parent.mkdir(parents=True, exist_ok=True)
            (work / proof).write_bytes((ROOT / proof).read_bytes())
        original = Path(FIXTURE).read_bytes()
        (work / LAYOUT).parent.mkdir(parents=True)
        (work / LAYOUT).write_bytes(original)
        store = RegionalStore(work / "guides.sqlite")
        store.put_guide(staged_guide("610726", ROOT))
        guide = store.put_guide(staged_application_candidate(work))
        self.assertTrue(guide["can_generate"])
        self.assertFalse(guide["templates"][1]["can_generate"])
        self.assertEqual(guide["templates"][1]["official_kind"], "blank")
        app = FastAPI()
        app.include_router(routes.router, prefix="/regional")
        self.enterContext(patch.object(routes, "ROOT", work))
        self.enterContext(patch.object(routes, "store", return_value=store))
        self.enterContext(patch.dict(os.environ, {"LABOURLAWYER_DATA_DIR": str(work / "private")}))
        client = self.enterContext(TestClient(app))
        bind = {**SCOPE, "source_id": guide["source_id"], "version": guide["version"],
                "kind": "application", "template_id": TEMPLATE_ID}
        contract = client.get("/regional/form-contract", params=bind)
        self.assertEqual(contract.status_code, 200, contract.text)
        form = contract.json()
        self.assertEqual(form["context"]["mode"], "blank")
        self.assertNotIn("signature", [field["key"] for field in form["fields"]])
        payload = {**bind, "contract_id": form["contract_id"], "mode": "blank", "data": DATA}
        for invalid in ({"contract_id": None}, {"mode": "reference_adaptation"},
                        {"district": "宁强县"}, {"template_id": "hanzhong-610727-authorization"}):
            with self.subTest(invalid=invalid):
                self.assertEqual(client.post("/regional/generate", json={**payload, **invalid}).status_code, 409)
        response = client.post("/regional/generate", json=payload)
        self.assertEqual(response.status_code, 200, response.text if not response.is_success else "")
        self.assertEqual(response.headers["x-document-origin"], "official-blank-converted-filled")
        self.assertEqual(response.headers["x-form-contract-id"], form["contract_id"])
        self.assertEqual(client.get(f"/regional/templates/{TEMPLATE_ID}", params=bind).status_code, 404)
        before = Document(BytesIO(original))
        doc = Document(BytesIO(response.content))
        p = doc.paragraphs
        for index, value in {2: "虚构甲", 3: "虚构申请方代理", 4: "虚构乙单位", 6: "虚构被申请方代理",
                             9: "第一项虚构请求", 11: "第三项虚构请求", 12: "虚构事实第二段",
                             13: "虚构证据及来源"}.items():
            self.assertIn(value, p[index].text)
        self.assertEqual(p[2].text, "申请人：姓名：虚构甲，出生日期：虚构出生日期")
        self.assertEqual(p[5].text, "法定代表人（主要负责人）：")
        self.assertEqual(p[10].text.strip(), "2.")
        self.assertEqual(p[11].text, "3. 第三项虚构请求\n（有具体金额的要写金额）")
        self.assertEqual([para.text for para in p[18:]], [para.text for para in before.paragraphs[18:]])
        self.assertTrue(p[21].paragraph_format.page_break_before)
        (work / FOLLOWUP).write_bytes(b"tampered")
        self.assertEqual(client.get("/regional/form-contract", params=bind).status_code, 409)
