from hashlib import sha256
from io import BytesIO
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, skipUnless
from unittest.mock import patch
from zipfile import ZipFile

from docx import Document
from fastapi import FastAPI
from fastapi.testclient import TestClient

from regional_guides import RegionalStore
from regional_hanzhong_guides import ZHENBA_LIUBA_FOPING_PROOF, staged_guide
from routes import regional_guides as routes


ROOT = Path(__file__).resolve().parents[2]
OFFICIAL_SHA = "dae75fba8210fede01e8f5a22e45ff66dabfe8f081c6092037460ef6878014cd"
SCOPE = {"province": "shaanxi", "city": "汉中市", "district": "佛坪县"}
FIXTURE = os.environ.get("FOPING_LAYOUT_SOURCE")
VALUES = {
    "applicant_name": "虚构甲", "applicant_gender": "女", "applicant_age": "32",
    "applicant_address": "虚构长街一号", "respondent_name": "虚构企业",
    "respondent_representative_name": "虚构乙", "respondent_representative_title": "经理",
    "requests": ["虚构请求一", "", "虚构请求三"],
    "facts": "用于验收的虚构事项。",
}


class FopingReferenceTests(TestCase):
    def test_official_reference_review_keeps_the_attachment_as_sample(self):
        from regional_foping_reference import TEMPLATE_ID
        guide = staged_guide("610730", ROOT)
        evidence = next(t for t in guide["templates"] if t["id"] == TEMPLATE_ID)
        self.assertEqual(evidence["official_sha256"], OFFICIAL_SHA)
        self.assertEqual(evidence["official_kind"], "sample")
        self.assertFalse(evidence["can_generate"])
        self.assertTrue(any("一页" in warning for warning in guide["warnings"]))

    def test_wrong_bytes_and_unsupported_fields_are_rejected(self):
        from regional_foping_reference import FopingReferenceRequest, fill_application
        with self.assertRaises(ValueError):
            fill_application(b"neighbor's document", {})
        for wrong in ({"signature": "虚构"}, {"committee_name": "其他机关"},
                      {"applicant_name": "甲\n乙"}, {"requests":["虚构"]*4},
                      {"facts":"甲\x00乙"}, {"applicant_age":"9999"}):
            with self.subTest(wrong=wrong), self.assertRaises(ValueError):
                FopingReferenceRequest.model_validate(wrong)

    @skipUnless(FIXTURE, "Foping's reviewed Word conversion is held in private evidence")
    def test_actual_own_sample_generates_reference_only_and_preserves_manual_fields(self):
        from regional_foping_reference import LAYOUT, TEMPLATE_ID, CONVERTED_SHA256, staged_reference_candidate
        work = Path(self.enterContext(TemporaryDirectory()))
        proof = work / ZHENBA_LIUBA_FOPING_PROOF
        proof.parent.mkdir(parents=True)
        proof.write_bytes((ROOT/ZHENBA_LIUBA_FOPING_PROOF).read_bytes())
        source = work / LAYOUT
        source.parent.mkdir(parents=True)
        source.write_bytes(Path(FIXTURE).read_bytes())
        self.assertEqual(sha256(source.read_bytes()).hexdigest(), CONVERTED_SHA256)
        store = RegionalStore(work/"guides.sqlite")
        guide = store.put_guide(staged_reference_candidate(work))
        store.put_guide(staged_guide("610728", ROOT))
        bind={**SCOPE,"source_id":guide["source_id"],"version":guide["version"],
              "kind":"application","template_id":TEMPLATE_ID}
        app=FastAPI()
        app.include_router(routes.router,prefix="/regional")
        self.enterContext(patch.object(routes,"ROOT", work))
        self.enterContext(patch.object(routes,"store",return_value=store))
        self.enterContext(patch.dict(os.environ,{"LABOURLAWYER_DATA_DIR":str(work/"private")}))
        client=self.enterContext(TestClient(app))
        got=client.get("/regional/form-contract",params=bind)
        self.assertEqual(got.status_code,200,got.text)
        form=got.json()
        self.assertEqual(form["context"]["mode"],"reference_adaptation")
        payload={**bind,"mode":"reference_adaptation","contract_id":form["contract_id"],"data":VALUES}
        for invalid in ({"mode":"blank"}, {"contract_id":None}, {"district":"镇巴县"}, {"version":0}):
            self.assertEqual(client.post("/regional/generate",json={**payload,**invalid}).status_code,409)
        response=client.post("/regional/generate",json=payload)
        self.assertEqual(response.status_code,200,response.text if not response.is_success else "")
        self.assertEqual(response.headers["x-document-origin"], "official-sample-adaptation-not-blank")
        self.assertEqual(response.headers["x-form-contract-id"],form["contract_id"])
        self.assertIn(".docx",response.headers["content-disposition"])
        self.assertEqual(client.get(f"/regional/templates/{TEMPLATE_ID}",params=bind).status_code,404)
        doc=Document(BytesIO(response.content))
        paragraphs=[p.text.strip() for p in doc.paragraphs]
        self.assertIn("参考填写",paragraphs[0])
        self.assertIn("虚构甲",paragraphs[2])
        self.assertIn("虚构请求一",paragraphs[7])
        self.assertTrue(doc.paragraphs[8].text.startswith("          2."))
        self.assertIn("虚构请求三",paragraphs[9])
        self.assertEqual(paragraphs[17],"申请人（手写签名）：")
        self.assertIn("年",paragraphs[18])
        self.assertNotIn("XXXX","\n".join(paragraphs))
        self.assertNotIn("仲裁委员会","\n".join(paragraphs))
        with ZipFile(BytesIO(response.content)) as out:
            self.assertFalse(any(k.startswith("customXml/") for k in out.namelist()))
