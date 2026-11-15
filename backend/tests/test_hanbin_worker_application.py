from hashlib import sha256
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
PROOF = Path("reports/overnight-gap-closure-20261030/localities/ankang-hanbin-worker/SOURCE-PROOF.json")
FIXTURE = os.environ.get("HANBIN_LAYOUT_SOURCE")
SCOPE = {"province": "shaanxi", "city": "安康市", "district": "汉滨区"}
VALUES = {
    "applicant_name": "虚构甲",
    "applicant_id": "123456789012345678",
    "respondent_name": "虚构企业",
    "requests": ["虚构请求第一行", "", "虚构请求第三行"],
    "facts": ["虚构事实"],
    "evidence": ["虚构材料第一行", "虚构材料第二行"],
}


class HanbinOwnApplicationTests(TestCase):
    def test_public_guide_only_uses_worker_scope_and_official_blank(self):
        from regional_hanbin_application import staged_guide

        guide = staged_guide(ROOT)
        self.assertEqual(guide["region_code"], "610902")
        self.assertIn("matterId=1112299132275", guide["source_url"])
        self.assertEqual([m["name"] for m in guide["materials"]],
                         ["劳动人事争议仲裁申请书", "身份证", "劳动（人事）关系证明材料", "授权委托书"])
        self.assertEqual(guide["materials"][3]["required"], "非必要")
        self.assertEqual(len(guide["templates"]), 1)
        self.assertFalse(guide["templates"][0]["can_generate"])
        self.assertEqual(guide["templates"][0]["official_kind"], "blank")
        self.assertNotIn("file", guide["templates"][0])

    def test_blocks_fields_outside_form_and_overflow(self):
        from regional_hanbin_application import HanbinApplicationRequest, fill_application

        for bad in ({"recipient": "其他地区"}, {"signature": "虚构甲"}, {"date": "2026-11-15"},
                    {"requests": ["甲"]*7}, {"facts": ["甲\n乙"]}, {"evidence": ["汉"*35]},
                    {"applicant_name": "汉"*8}, {"applicant_id": "甲\x00乙"}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                HanbinApplicationRequest.model_validate(bad)
        with self.assertRaises(ValueError):
            fill_application(b"missing or mismatched official conversion", {})

    @skipUnless(FIXTURE, "Hanbin's reviewed Word conversion is held in private evidence")
    def test_exact_contract_fills_verified_rows_and_preserves_notes_and_manual_slots(self):
        from regional_hanbin_application import LAYOUT, TEMPLATE_ID, staged_application_candidate

        root = Path(self.enterContext(TemporaryDirectory()))
        (root/PROOF).parent.mkdir(parents=True)
        (root/PROOF).write_bytes((ROOT/PROOF).read_bytes())
        original = Path(FIXTURE).read_bytes()
        (root/LAYOUT).parent.mkdir(parents=True)
        (root/LAYOUT).write_bytes(original)
        store = RegionalStore(root/"guides.sqlite")
        proposed = staged_application_candidate(root)
        guide = store.put_guide(proposed)
        other = store.put_guide({**proposed,"district":"汉阴县","region_code":"610921"})
        app = FastAPI()
        app.include_router(routes.router,prefix="/regional")
        self.enterContext(patch.object(routes,"ROOT",root))
        self.enterContext(patch.object(routes,"store",return_value=store))
        self.enterContext(patch.dict(os.environ,{"LABOURLAWYER_DATA_DIR":str(root/"data")}))
        client = self.enterContext(TestClient(app))
        bind = {**SCOPE,"kind":"application","source_id":guide["source_id"],"version":guide["version"],
                "template_id":TEMPLATE_ID}
        result = client.get("/regional/form-contract",params=bind)
        self.assertEqual(result.status_code,200,result.text)
        contract = result.json()
        self.assertEqual(contract["context"]["mode"],"blank")
        counts = {field["key"]:field["maxItems"] for field in contract["fields"] if field["type"]=="text_list"}
        self.assertEqual(counts,{"requests":6,"facts":6,"evidence":7})
        payload = {**bind,"mode":"blank","contract_id":contract["contract_id"],"data":VALUES}
        for invalid in ({"mode":"reference_adaptation"},{"contract_id":None},{"version":0},
                        {"district":"汉阴县","version":other["version"]},{"kind":"evidence"},
                        {"template_id":"hanbin-employer-reference"}):
            with self.subTest(invalid=invalid):
                self.assertEqual(client.post("/regional/generate",json={**payload,**invalid}).status_code,409)
        response = client.post("/regional/generate",json=payload)
        self.assertEqual(response.status_code,200,response.text if not response.is_success else "")
        self.assertEqual(response.headers["x-document-origin"],"official-blank-converted-filled")
        self.assertEqual(response.headers["x-form-contract-id"],contract["contract_id"])
        self.assertEqual(client.get(f"/regional/templates/{TEMPLATE_ID}",params=bind).status_code,404)
        before = Document(BytesIO(original))
        filled = Document(BytesIO(response.content))
        p = filled.paragraphs
        self.assertIn("虚构甲",p[2].text)
        self.assertTrue(p[2].runs[2].underline)
        self.assertIn(VALUES["applicant_id"],p[2].runs[9].text)
        self.assertIn("虚构请求第一行",p[9].text)
        self.assertEqual(p[10].text,before.paragraphs[10].text)
        self.assertIn("虚构请求第三行",p[11].text)
        self.assertIn("虚构事实",p[17].text)
        self.assertIn("虚构材料第二行",p[26].text)
        for index in [*range(33,45)]:
            self.assertEqual(p[index].text,before.paragraphs[index].text)
        (root/PROOF).write_bytes(b"altered")
        self.assertEqual(client.get("/regional/form-contract",params=bind).status_code,409)
        (root/PROOF).write_bytes((ROOT/PROOF).read_bytes())
        (root/LAYOUT).write_bytes(b"altered")
        self.assertEqual(client.get("/regional/form-contract",params=bind).status_code,409)
