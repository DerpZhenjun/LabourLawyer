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
PRIVATE = os.getenv("LABOURLAWYER_HEYANG_WORKER_LAYOUT")
DATA = {"request_one": "合成请求甲", "request_two": "合成请求乙", "request_three": "合成请求丙"}


class HeyangWorkerApplicationTests(TestCase):
    def test_request_model_keeps_party_and_narrative_fields_manual(self):
        from regional_heyang_application import HeyangWorkerApplicationRequest

        self.assertEqual(HeyangWorkerApplicationRequest.model_validate(DATA).model_dump(), DATA)
        for data in ({"applicant_name": "示例"}, {"signature": "示例"}, {"facts": "示例"},
                     {"request_one": "甲\n乙"}, {"request_one": "甲" * 16}, {"request_two": 1}):
            with self.subTest(data=data), self.assertRaises(ValueError):
                HeyangWorkerApplicationRequest.model_validate(data)

    @skipUnless(PRIVATE, "Word conversion retained in local evidence")
    def test_only_whitespace_runs_on_three_request_rows_are_filled(self):
        from regional_heyang_application import fill_application

        layout = Path(PRIVATE).read_bytes()
        baseline = Document(BytesIO(layout))
        output = fill_application(layout, DATA)
        self.assertEqual(len(output.paragraphs), len(baseline.paragraphs))
        for index, field in enumerate(DATA, start=7):
            filled = output.paragraphs[index].runs[0]
            self.assertEqual(filled.text.strip(), DATA[field])
            self.assertEqual(filled.underline, baseline.paragraphs[index].runs[0].underline)
        for index in set(range(18)) - {7, 8, 9}:
            self.assertEqual(output.paragraphs[index]._p.xml, baseline.paragraphs[index]._p.xml)
        empty = fill_application(layout, {})
        self.assertEqual([p._p.xml for p in empty.paragraphs], [p._p.xml for p in baseline.paragraphs])
        with self.assertRaises(ValueError):
            fill_application(layout + b" ", DATA)

    @skipUnless(PRIVATE, "Word conversion retained in local evidence")
    def test_routes_register_only_exact_worker_blank_and_require_current_contract(self):
        from regional_heyang_application import LAYOUT, TEMPLATE_ID, staged_worker_candidate
        from regional_heyang_guides import SOURCE

        root = Path(self.enterContext(TemporaryDirectory()))
        for target, evidence in ((SOURCE, ROOT / SOURCE), (LAYOUT, Path(PRIVATE))):
            path = root / target
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(evidence.read_bytes())
        store = RegionalStore(root / "guides.sqlite")
        guide = store.put_guide(staged_worker_candidate(root))
        self.assertFalse(guide["published"])
        self.assertEqual([t["service_object"] for t in guide["templates"]], ["劳动者"])
        self.assertEqual(set(guide["role_sources"]), {"劳动者", "用人单位"})

        app = FastAPI()
        app.include_router(routes.router, prefix="/regional")
        self.enterContext(patch.object(routes, "ROOT", root))
        self.enterContext(patch.object(routes, "store", return_value=store))
        self.enterContext(patch.dict(os.environ, {"LABOURLAWYER_DATA_DIR": str(root / "private")}))
        client = self.enterContext(TestClient(app))
        bound = {key: guide[key] for key in ("province", "city", "district", "source_id", "version")}
        bound.update(kind="application", template_id=TEMPLATE_ID)
        contract = client.get("/regional/form-contract", params=bound).json()
        self.assertEqual({f["key"] for f in contract["fields"]}, set(DATA))
        payload = {**bound, "contract_id": contract["contract_id"], "mode": "blank", "data": DATA}
        response = client.post("/regional/generate", json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["x-document-origin"], "official-blank-converted-filled")
        self.assertEqual(response.headers["x-form-contract-id"], contract["contract_id"])
        self.assertEqual(Document(BytesIO(response.content)).paragraphs[9].text.strip(), DATA["request_three"])
        for update in (
            {"contract_id": None}, {"mode": "reference_adaptation"}, {"district": "大荔县"},
            {"template_id": "weinan-610524-employer-application"}, {"template_id": "weinan-610524-identity"},
        ):
            self.assertEqual(client.post("/regional/generate", json={**payload, **update}).status_code, 409)
        self.assertEqual(client.post("/regional/generate", json={**payload, "data": {"request_two": "宽" * 16}}).status_code, 422)
        self.assertEqual(client.get(f"/regional/templates/{TEMPLATE_ID}", params=bound).status_code, 404)
        (root / LAYOUT).write_bytes(b"changed")
        self.assertEqual(client.get("/regional/form-contract", params=bound).status_code, 409)
