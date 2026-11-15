from io import BytesIO
import os
from pathlib import Path
from unittest import TestCase, skipUnless
from urllib.parse import unquote

from docx import Document


FIXTURE = os.environ.get("ZIYANG_WORKER_LAYOUT_SOURCE")


class ZiyangWorkerReferenceTests(TestCase):
    def test_rejects_manual_fields_and_out_of_layout_values(self):
        from regional_ziyang_worker_reference import WorkerReferenceRequest, fill_reference

        for data in (
            {"committee": "外地机构"}, {"signature": "虚构签名"}, {"date": "2026-11-15"},
            {"applicant_name": "甲\n乙"}, {"requests": ["虚构"] * 3}, {"facts": ["甲" * 35]},
            {"agent_authority": "甲" * 15}, {"representative_position": "甲" * 7}, {"facts": ["甲" * 24]},
        ):
            with self.subTest(data=data), self.assertRaises(ValueError):
                WorkerReferenceRequest.model_validate(data)
        with self.assertRaises(ValueError):
            fill_reference(b"wrong file", {})

    @skipUnless(FIXTURE, "The exact county original is retained in private evidence")
    def test_original_keeps_reference_label_and_manual_second_page(self):
        from regional_ziyang_worker_reference import fill_reference

        raw = Path(FIXTURE).read_bytes()
        before = Document(BytesIO(raw))
        filled = fill_reference(raw, {
            "applicant_name": "虚构甲", "applicant_id": "123456789012345678",
            "respondent_name": "虚构单位", "requests": ["虚构请求一", "虚构请求二"],
            "facts": ["虚构事实一", "虚构事实二"],
        })
        self.assertEqual(filled.paragraphs[3].runs[1].text.strip(), "虚构甲")
        self.assertIn("123456789012345678", filled.paragraphs[4].text)
        self.assertIn("虚构单位", filled.paragraphs[6].text)
        for index, value in [(10,"虚构请求一"),(11,"虚构请求二"),(13,"虚构事实一"),(14,"虚构事实二")]:
            self.assertIn(value, filled.paragraphs[index].text)
        for index in [0, 1, 15, 16, 17, 18, 19, 20]:
            self.assertEqual(filled.paragraphs[index]._p.xml, before.paragraphs[index]._p.xml)


class ZiyangWorkerReferenceContractTests(TestCase):
    def test_initial_guide_binds_roles_and_classifies_the_application_as_reference(self):
        from regional_ziyang_worker_reference import staged_guide

        guide = staged_guide()
        self.assertEqual((guide["city"], guide["district"], guide["region_code"]), ("安康市", "紫阳县", "610924"))
        self.assertEqual([item["service_object"] for item in guide["materials"]], ["劳动者"] * 4 + ["用人单位"] * 6)
        self.assertEqual([item["official_kind"] for item in guide["templates"]], ["sample", "sample", "blank", "blank"])
        self.assertTrue(all(item["download_status"] == "official_link_only" for item in guide["templates"]))
        self.assertFalse(guide["can_generate"])

    @skipUnless(FIXTURE, "The exact county original is retained in private evidence")
    def test_api_requires_current_reference_mode_and_exact_source_file(self):
        from tempfile import TemporaryDirectory
        from unittest.mock import patch

        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from regional_guides import RegionalStore
        from regional_ziyang_worker_reference import LAYOUT, PROOF, ROOT, TEMPLATE_ID, staged_reference_candidate
        from routes import regional_guides as routes

        root = Path(self.enterContext(TemporaryDirectory()))
        (root / PROOF).parent.mkdir(parents=True)
        (root / PROOF).write_bytes((ROOT / PROOF).read_bytes())
        (root / LAYOUT).parent.mkdir(parents=True)
        original = Path(FIXTURE).read_bytes()
        (root / LAYOUT).write_bytes(original)
        store = RegionalStore(root / "guides.sqlite")
        proposed = staged_reference_candidate(root)
        guide = store.put_guide(proposed)
        other = store.put_guide({**proposed, "district": "岚皋县", "region_code": "610925"})
        app = FastAPI()
        app.include_router(routes.router, prefix="/regional")
        self.enterContext(patch.object(routes, "ROOT", root))
        self.enterContext(patch.object(routes, "store", return_value=store))
        self.enterContext(patch.dict(os.environ, {"LABOURLAWYER_DATA_DIR": str(root / "data")}))
        client = self.enterContext(TestClient(app))
        bind = {"province": "shaanxi", "city": "安康市", "district": "紫阳县",
                "source_id": guide["source_id"], "version": guide["version"], "kind": "application",
                "template_id": TEMPLATE_ID}
        contract_response = client.get("/regional/form-contract", params=bind)
        self.assertEqual(contract_response.status_code, 200, contract_response.text)
        contract = contract_response.json()
        self.assertEqual(contract["context"]["mode"], "reference_adaptation")
        self.assertEqual({f["key"]: f["maxItems"] for f in contract["fields"] if f["type"] == "text_list"},
                         {"requests": 2, "facts": 2})
        payload = {**bind, "mode": "reference_adaptation", "contract_id": contract["contract_id"],
                   "data": {"applicant_name": "虚构甲", "requests": ["虚构请求"], "facts": ["虚构事实"]}}
        for bad in ({"mode": "blank"}, {"contract_id": None}, {"version": 0}, {"kind": "evidence"},
                    {"template_id": "ankang-610924-employer-reference"}, {"source_id": "unrelated-source"},
                    {"district": "岚皋县", "version": other["version"]}):
            with self.subTest(bad=bad):
                self.assertEqual(client.post("/regional/generate", json={**payload, **bad}).status_code, 409)
        output = client.post("/regional/generate", json=payload)
        self.assertEqual(output.status_code, 200, output.text if not output.is_success else "")
        self.assertIn("参考样表辅助填写.docx", unquote(output.headers["content-disposition"]))
        self.assertIn("供当事人参考", Document(BytesIO(output.content)).paragraphs[0].text)
        self.assertEqual(client.get(f"/regional/templates/{TEMPLATE_ID}", params=bind).status_code, 404)
        (root / LAYOUT).write_bytes(b"tampered")
        self.assertEqual(client.get("/regional/form-contract", params=bind).status_code, 409)
        (root / LAYOUT).write_bytes(original)
        (root / PROOF).write_bytes(b"tampered")
        self.assertEqual(client.get("/regional/form-contract", params=bind).status_code, 409)
