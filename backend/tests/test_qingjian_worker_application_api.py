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
from regional_qingjian_application import LAYOUT, TEMPLATE_ID, staged_worker_candidate
from regional_qingjian_guides import SOURCE
from routes import regional_guides as routes


ROOT = Path(__file__).resolve().parents[2]
PRIVATE = os.getenv("LABOURLAWYER_QINGJIAN_WORKER_LAYOUT")


class QingjianWorkerApplicationApiTests(TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory()))
        source = self.root / SOURCE
        source.parent.mkdir(parents=True)
        source.write_bytes((ROOT / SOURCE).read_bytes())
        self.layout = self.root / LAYOUT
        self.layout.parent.mkdir(parents=True)
        self.store = RegionalStore(self.root / "candidate.sqlite")
        app = FastAPI()
        app.include_router(routes.router, prefix="/regional")
        self.enterContext(patch.object(routes, "ROOT", self.root))
        self.enterContext(patch.object(routes, "store", return_value=self.store))
        self.enterContext(patch.dict(os.environ, {"LABOURLAWYER_DATA_DIR": str(self.root / "private")}))
        self.client = self.enterContext(TestClient(app))

    def test_candidate_requires_local_pinned_layout(self):
        with self.assertRaises(ValueError):
            staged_worker_candidate(self.root)
        self.layout.write_bytes(b"unverified")
        with self.assertRaises(ValueError):
            staged_worker_candidate(self.root)

    @skipUnless(PRIVATE, "verified Qingjian blank layout is kept locally")
    def test_worker_contract_and_download_require_exact_candidate(self):
        self.layout.write_bytes(Path(PRIVATE).read_bytes())
        candidate = staged_worker_candidate(self.root)
        self.assertEqual([t["service_object"] for t in candidate["templates"]], ["劳动者"])
        self.assertEqual(set(candidate["role_sources"]), {"劳动者", "用人单位"})
        self.assertFalse(candidate["published"])
        guide = self.store.put_guide(candidate)
        binding = {key: guide[key] for key in ("province", "city", "district", "source_id", "version")}
        binding.update(template_id=TEMPLATE_ID, kind="application")
        response = self.client.get("/regional/form-contract", params=binding)
        self.assertEqual(response.status_code, 200, response.text)
        contract = response.json()
        self.assertEqual((contract["context"]["district"], contract["context"]["region_code"]), ("清涧县", "610830"))
        self.assertEqual(contract["context"]["template_sha256"], candidate["templates"][0]["sha256"])
        self.assertEqual({field["key"]:field["maxItems"] for field in contract["fields"]}, {"requests":4,"facts":10})
        payload = {**binding, "mode": "blank", "contract_id": contract["contract_id"],
                   "data": {"requests": ["合成请求"], "facts": ["合成事实"]}}
        generated = self.client.post("/regional/generate", json=payload)
        self.assertEqual(generated.status_code, 200, generated.text if generated.status_code != 200 else "")
        self.assertEqual(generated.headers["x-document-origin"], "official-blank-filled")
        self.assertEqual(generated.headers["x-form-contract-id"], contract["contract_id"])
        self.assertEqual(generated.headers["cache-control"], "no-store")
        doc = Document(BytesIO(generated.content))
        self.assertTrue(doc.paragraphs[16].text.endswith("合成请求"))
        self.assertEqual(doc.paragraphs[24].text, "合成事实")
        for changes in (
            {"contract_id": None}, {"contract_id": "0" * 64}, {"mode": "reference_adaptation"},
            {"district": "靖边县"}, {"source_id": "elsewhere"}, {"version": guide["version"] + 1},
            {"kind": "evidence"}, {"template_id": "yulin-610830-employer-application"},
        ):
            self.assertEqual(self.client.post("/regional/generate", json={**payload, **changes}).status_code, 409)
        self.assertEqual(self.client.post("/regional/generate", json={**payload, "data": {"requests": ["甲" * 21]}}).status_code, 422)
        self.assertEqual(self.client.get(f"/regional/templates/{TEMPLATE_ID}", params=binding).status_code, 404)
        candidate["templates"][0]["service_object"] = "用人单位"
        self.store.put_guide(candidate)
        forged = {**binding, "version": self.store.lookup("shaanxi", "榆林市", "清涧县")["version"]}
        self.assertEqual(self.client.get("/regional/form-contract", params=forged).status_code, 409)
        self.store.put_guide(staged_worker_candidate(self.root))
        binding["version"] = self.store.lookup("shaanxi", "榆林市", "清涧县")["version"]
        self.layout.write_bytes(b"layout changed")
        self.assertEqual(self.client.get("/regional/form-contract", params=binding).status_code, 409)
