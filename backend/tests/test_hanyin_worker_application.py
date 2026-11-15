from hashlib import sha256
from io import BytesIO
import os
from pathlib import Path
from unittest import TestCase, skipUnless

from docx import Document


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = os.environ.get("HANYIN_LAYOUT_SOURCE")


class HanyinApplicationLayoutTests(TestCase):
    def test_request_rejects_fields_and_text_outside_the_original_layout(self):
        from regional_hanyin_application import HanyinApplicationRequest, fill_application

        for invalid in (
            {"recipient": "异地委员会"}, {"signature": "虚构签名"}, {"date": "2026-11-15"},
            {"requests": ["各一项"] * 4}, {"requests": ["断行\n文本"]},
            {"applicant_name": "某" * 6}, {"applicant_address": "甲\x00乙"},
            {"facts_and_evidence": "甲" * 72}, {"requests": ["W" * 22]},
        ):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                HanyinApplicationRequest.model_validate(invalid)
        with self.assertRaises(ValueError):
            fill_application(b"unexpected template", {})

    @skipUnless(FIXTURE, "The Word conversion is retained in private evidence")
    def test_hanyin_original_fills_three_requests_and_leaves_manual_sections_unchanged(self):
        from regional_hanyin_application import CONVERTED_SHA256, fill_application

        original = Path(FIXTURE).read_bytes()
        self.assertEqual(sha256(original).hexdigest(), CONVERTED_SHA256)
        before = Document(BytesIO(original))
        after = fill_application(original, {
            "applicant_name": "虚构甲",
            "applicant_id": "123456789012345678",
            "respondent_name": "虚构企业",
            "requests": ["虚构请求一", "", "虚构请求三"],
            "facts_and_evidence": "虚构事实及证据",
        })
        self.assertEqual(len(after.paragraphs), len(before.paragraphs))
        paragraphs = after.paragraphs
        self.assertEqual(paragraphs[1].runs[1].text.strip(), "虚构甲")
        self.assertTrue(paragraphs[1].runs[1].underline)
        self.assertEqual(paragraphs[2].runs[5].text.strip(), "123456789012345678")
        self.assertEqual(paragraphs[3].runs[1].text.strip(), "虚构企业")
        self.assertEqual(paragraphs[8].runs[2].text.strip(), "虚构请求一")
        self.assertEqual(paragraphs[8].runs[5].text, before.paragraphs[8].runs[5].text)
        self.assertEqual(paragraphs[8].text.splitlines()[1].strip(), "2、")
        self.assertEqual(paragraphs[9].runs[2].text.strip(), "虚构请求三")
        self.assertEqual(paragraphs[10].runs[2].text.strip(), "虚构事实及证据")
        for index in range(11, 20):
            self.assertEqual(paragraphs[index]._p.xml, before.paragraphs[index]._p.xml)

    @skipUnless(FIXTURE, "The Word conversion is retained in private evidence")
    def test_phone_and_identity_values_keep_the_original_contact_row_starts(self):
        from regional_hanyin_application import fill_application

        raw = Path(FIXTURE).read_bytes()
        doc = fill_application(raw, {
            "applicant_id": "123456789012345678", "applicant_landline": "0123-4567890",
            "applicant_mobile": "12345678901",
        })
        lines = doc.paragraphs[2].text.splitlines()
        self.assertEqual(len(lines), 4)
        self.assertEqual([line.strip().split("：", 1)[0].split(" ", 1)[0] for line in lines],
                         ["详细住址", "身份证号123456789012345678", "工作单位", "联系电话"])
        self.assertIn("12345678901", lines[-1])


class HanyinSourceContractTests(TestCase):
    def test_worker_guide_uses_the_exact_source_and_excludes_conflicting_attachments(self):
        from regional_hanyin_application import staged_guide

        guide = staged_guide(ROOT)
        self.assertEqual(guide["region_code"], "610921")
        self.assertIn("matterId=1119159132100", guide["source_url"])
        self.assertIn("汉阴县政务大厅", guide["fields"]["办理地点"])
        self.assertIn("3", guide["fields"]["承诺办结时限"])
        self.assertEqual([item["name"] for item in guide["materials"]],
                         ["劳动人事争议仲裁申请书", "身份证", "劳动（人事）关系证明材料", "授权委托书"])
        self.assertFalse(guide["can_generate"])
        self.assertEqual(len(guide["templates"]), 1)
        self.assertEqual(guide["templates"][0]["official_kind"], "blank")
        self.assertNotIn("file", guide["templates"][0])

    @skipUnless(FIXTURE, "The Word conversion is retained in private evidence")
    def test_contract_and_generation_require_the_exact_source_version_and_private_layout(self):
        from tempfile import TemporaryDirectory
        from unittest.mock import patch

        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from regional_guides import RegionalStore
        from regional_hanyin_application import LAYOUT, PROOF, TEMPLATE_ID, staged_application_candidate
        from routes import regional_guides as routes

        root = Path(self.enterContext(TemporaryDirectory()))
        (root / PROOF).parent.mkdir(parents=True)
        (root / PROOF).write_bytes((ROOT / PROOF).read_bytes())
        (root / LAYOUT).parent.mkdir(parents=True)
        (root / LAYOUT).write_bytes(Path(FIXTURE).read_bytes())
        store = RegionalStore(root / "guides.sqlite")
        proposed = staged_application_candidate(root)
        guide = store.put_guide(proposed)
        wrong_scope = store.put_guide({**proposed, "district": "石泉县", "region_code": "610922"})
        app = FastAPI()
        app.include_router(routes.router, prefix="/regional")
        self.enterContext(patch.object(routes, "ROOT", root))
        self.enterContext(patch.object(routes, "store", return_value=store))
        self.enterContext(patch.dict(os.environ, {"LABOURLAWYER_DATA_DIR": str(root / "data")}))
        client = self.enterContext(TestClient(app))
        binding = {
            "province": "shaanxi", "city": "安康市", "district": "汉阴县",
            "kind": "application", "source_id": guide["source_id"],
            "version": guide["version"], "template_id": TEMPLATE_ID,
        }
        result = client.get("/regional/form-contract", params=binding)
        self.assertEqual(result.status_code, 200, result.text)
        contract = result.json()
        self.assertEqual(contract["context"]["mode"], "blank")
        self.assertEqual(contract["context"]["region_code"], "610921")
        fields = {field["key"]: field for field in contract["fields"]}
        self.assertEqual(fields["requests"]["maxItems"], 3)
        self.assertIn("facts_and_evidence", fields)
        self.assertFalse({"date", "recipient", "signature"} & fields.keys())
        payload = {**binding, "mode": "blank", "contract_id": contract["contract_id"],
                   "data": {"applicant_name": "虚构甲", "requests": ["虚构请求"]}}
        for invalid in ({"version": 0}, {"mode": "reference_adaptation"}, {"kind": "evidence"},
                        {"contract_id": None}, {"template_id": "employer-application"},
                        {"district": "石泉县", "version": wrong_scope["version"]}):
            with self.subTest(invalid=invalid):
                self.assertEqual(client.post("/regional/generate", json={**payload, **invalid}).status_code, 409)
        generated = client.post("/regional/generate", json=payload)
        self.assertEqual(generated.status_code, 200, generated.text if not generated.is_success else "")
        self.assertEqual(generated.headers["x-document-origin"], "official-blank-converted-filled")
        self.assertEqual(generated.headers["x-form-contract-id"], contract["contract_id"])
        self.assertIn("虚构请求", Document(BytesIO(generated.content)).paragraphs[8].text)
        self.assertEqual(client.get(f"/regional/templates/{TEMPLATE_ID}", params=binding).status_code, 404)
        (root / LAYOUT).write_bytes(b"changed")
        self.assertEqual(client.get("/regional/form-contract", params=binding).status_code, 409)
        (root / LAYOUT).write_bytes(Path(FIXTURE).read_bytes())
        (root / PROOF).write_bytes(b"changed")
        self.assertEqual(client.get("/regional/form-contract", params=binding).status_code, 409)
