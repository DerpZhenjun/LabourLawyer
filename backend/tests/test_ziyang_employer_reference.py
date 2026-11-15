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
EMPLOYER = os.environ.get("ZIYANG_EMPLOYER_LAYOUT_SOURCE")
WORKER = os.environ.get("ZIYANG_WORKER_LAYOUT_SOURCE")
VALUES = {
    "applicant_company": "虚构申请单位",
    "representative_name": "虚构甲",
    "representative_position": "虚构职务",
    "respondent_name": "虚构乙",
    "respondent_gender": "女",
    "respondent_id": "000000000000000000",
    "requests": ["虚构请求甲", "虚构请求乙"],
    "facts": ["虚构事实甲", "虚构事实乙"],
}


class ZiyangEmployerReferenceTests(TestCase):
    def test_rejects_worker_only_fields_manual_signing_and_oversized_values(self):
        from regional_ziyang_employer_reference import EmployerReferenceRequest, fill_reference

        for values in (
            {"applicant_name": "虚构劳动者"}, {"applicant_id": "0"}, {"signature": "虚构签名"},
            {"date": "2026-11-15"}, {"stamp": "虚构公章"}, {"respondent_name": "甲\n乙"},
            {"requests": ["甲"] * 3}, {"facts": ["甲" * 40]}, {"applicant_company": 5},
        ):
            with self.subTest(values=values), self.assertRaises(ValueError):
                EmployerReferenceRequest.model_validate(values)
        with self.assertRaises(ValueError):
            fill_reference(b"unrelated", {})

    @skipUnless(EMPLOYER and WORKER, "Exact role originals are retained in private evidence")
    def test_uses_employer_slots_and_preserves_reference_recipient_and_manual_signing(self):
        from regional_ziyang_employer_reference import fill_reference

        original = Path(EMPLOYER).read_bytes()
        with self.assertRaises(ValueError):
            fill_reference(Path(WORKER).read_bytes(), VALUES)
        before = Document(BytesIO(original))
        output = fill_reference(original, VALUES)
        for index in (0, 1, 2, 15, 16, 17, 18, 19, 20):
            self.assertEqual(output.paragraphs[index]._p.xml, before.paragraphs[index]._p.xml)
        self.assertIn("虚构申请单位", output.paragraphs[3].text)
        self.assertIn("虚构甲", output.paragraphs[4].text)
        self.assertIn("虚构乙", output.paragraphs[7].text)
        self.assertIn("000000000000000000", output.paragraphs[8].text)
        for index, value in [(10, "虚构请求甲"), (11, "虚构请求乙"), (13, "虚构事实甲"), (14, "虚构事实乙")]:
            self.assertIn(value, output.paragraphs[index].text)

    @skipUnless(EMPLOYER and WORKER, "Exact role originals are retained in private evidence")
    def test_both_roles_keep_independent_template_ids_hashes_and_contracts(self):
        from regional_ziyang_worker_reference import LAYOUT as WORKER_LAYOUT, PROOF, TEMPLATE_ID as WORKER_ID
        from regional_ziyang_employer_reference import LAYOUT, TEMPLATE_ID, staged_dual_role_candidate

        root = Path(self.enterContext(TemporaryDirectory()))
        for path, raw in ((WORKER_LAYOUT, Path(WORKER).read_bytes()), (LAYOUT, Path(EMPLOYER).read_bytes()),
                          (PROOF, (ROOT / PROOF).read_bytes())):
            (root / path).parent.mkdir(parents=True, exist_ok=True)
            (root / path).write_bytes(raw)
        store = RegionalStore(root / "guides.sqlite")
        guide = store.put_guide(staged_dual_role_candidate(root))
        adapter_files = [row for row in guide["templates"] if row["can_generate"]]
        self.assertEqual([row["id"] for row in adapter_files], [WORKER_ID, TEMPLATE_ID])
        self.assertNotEqual(adapter_files[0]["sha256"], adapter_files[1]["sha256"])
        app = FastAPI()
        app.include_router(routes.router, prefix="/regional")
        self.enterContext(patch.object(routes, "ROOT", root))
        self.enterContext(patch.object(routes, "store", return_value=store))
        self.enterContext(patch.dict(os.environ, {"LABOURLAWYER_DATA_DIR": str(root / "data")}))
        client = self.enterContext(TestClient(app))
        common = {key: guide[key] for key in ("province", "city", "district", "source_id", "version")}
        common["kind"] = "application"
        contracts = []
        for template_id in (WORKER_ID, TEMPLATE_ID):
            response = client.get("/regional/form-contract", params={**common, "template_id": template_id})
            self.assertEqual(response.status_code, 200, response.text)
            contracts.append(response.json())
        worker, employer = contracts
        self.assertNotEqual(worker["contract_id"], employer["contract_id"])
        self.assertNotIn("applicant_company", {field["key"] for field in worker["fields"]})
        self.assertIn("applicant_company", {field["key"] for field in employer["fields"]})
        payload = {**common, "template_id": TEMPLATE_ID, "mode": "reference_adaptation",
                   "data": VALUES, "contract_id": employer["contract_id"]}
        for wrong in ({"template_id": WORKER_ID}, {"mode": "blank"}, {"contract_id": worker["contract_id"]}):
            self.assertEqual(client.post("/regional/generate", json={**payload, **wrong}).status_code, 409)
        result = client.post("/regional/generate", json=payload)
        self.assertEqual(result.status_code, 200, result.text if not result.is_success else "")
        self.assertEqual(result.headers["x-document-origin"], "official-sample-adaptation-not-blank")
        self.assertIn("供当事人参考", Document(BytesIO(result.content)).paragraphs[0].text)
        (root / LAYOUT).write_bytes(Path(WORKER).read_bytes())
        self.assertEqual(client.get("/regional/form-contract", params={**common, "template_id": TEMPLATE_ID}).status_code, 409)
        self.assertEqual(client.get("/regional/form-contract", params={**common, "template_id": WORKER_ID}).status_code, 200)
        (root / LAYOUT).write_bytes(Path(EMPLOYER).read_bytes())
        (root / WORKER_LAYOUT).write_bytes(b"changed")
        self.assertEqual(client.get("/regional/form-contract", params={**common, "template_id": TEMPLATE_ID}).status_code, 200)
