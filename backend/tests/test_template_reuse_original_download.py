"""Exercise the pilot's real own-source original download failure."""

from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from regional_guides import RegionalStore
from routes import regional_guides as routes


ROOT = Path(__file__).resolve().parents[2]


class OwnOriginalDownloadTests(TestCase):
    def test_quangang_canonical_original_download_retains_source_binding(self):
        snapshot = json.loads((ROOT / "data/public-regions/guides.json").read_bytes())
        guide = next(row for row in snapshot if row["region_code"] == "350505")
        root = Path(self.enterContext(TemporaryDirectory()))
        store = RegionalStore(root / "guides.sqlite")
        guide = store.put_guide(guide)
        template = next(row for row in guide["templates"] if row.get("can_generate"))
        self.enterContext(patch.object(routes, "ROOT", ROOT))
        self.enterContext(patch.object(routes, "store", return_value=store))
        app = FastAPI()
        app.include_router(routes.router, prefix="/regional")
        client = self.enterContext(TestClient(app))
        query = {key: guide[key] for key in ("province", "city", "district", "source_id", "version")}
        contract = client.get("/regional/form-contract", params={
            **query, "template_id": template["id"], "kind": template["document_types"][0],
        })
        self.assertEqual(contract.status_code, 200)
        response = client.get("/regional/templates/" + template["id"], params=query)
        self.assertEqual(response.status_code, 200, response.text if response.status_code != 200 else "")
        self.assertEqual(sha256(response.content).hexdigest(), template["sha256"])
        self.assertEqual(response.headers["x-guide-source-id"], guide["source_id"])
        for delta in ({"district": "惠安县"}, {"source_id": "other-source"}):
            rejected = client.get("/regional/templates/" + template["id"], params={**query, **delta})
            self.assertNotEqual(rejected.status_code, 200)
