from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from regional_directory import DirectoryStore
from regional_guides import RegionalStore
from routes import regional_guides as routes


ROOT = Path(__file__).resolve().parents[2]
CITY = {"province": "shaanxi", "city": "商洛市"}


class ShangluoMunicipalOfficialGuidesTests(TestCase):
    def test_staged_guide_reports_cross_material_sample_conflict(self):
        from regional_shangluo_municipal_guides import exact_municipal, staged_guide

        guide = staged_guide(ROOT)
        self.assertTrue(exact_municipal(guide))
        self.assertFalse(exact_municipal({**guide, "source_version": "0" * 64}))
        self.assertEqual((guide["district"], guide["scope_level"], guide["region_code"]),
                         ("市本级", "municipal", "611000"))
        self.assertEqual([m["service_object"] for m in guide["materials"]], ["劳动者"] * 5 + ["用人单位"] * 4)
        self.assertIn("713", guide["fields"]["办理地点"])
        self.assertEqual(guide["fields"]["承诺办结时限"], "5 个工作日")
        self.assertIn("8 个", guide["sections"]["官网附件核验"])
        self.assertEqual(guide["templates"], [])
        self.assertFalse(guide["can_generate"])
        self.assertFalse(guide["published"])

    def test_municipal_option_has_no_proxy_download_or_subordinate_fallback(self):
        from regional_shangluo_municipal_guides import staged_guide

        root = Path(self.enterContext(TemporaryDirectory()))
        store = RegionalStore(root / "guides.sqlite")
        directory = DirectoryStore(root / "areas.sqlite")
        for row in json.loads((ROOT / "data/public-regions/directory.json").read_bytes()):
            if row["code"] in ("611000", "611002"):
                directory.put_area(row)
        app = FastAPI()
        app.include_router(routes.router, prefix="/regional")
        self.enterContext(patch.object(routes, "ROOT", ROOT))
        self.enterContext(patch.object(routes, "store", return_value=store))
        self.enterContext(patch.object(routes, "directory_store", return_value=directory))
        client = self.enterContext(TestClient(app))

        self.assertNotIn("市本级", [r["district"] for r in client.get("/regional/areas", params=CITY).json()["items"]])
        guide = store.put_guide(staged_guide(ROOT))
        areas = client.get("/regional/areas", params=CITY).json()["items"]
        self.assertEqual((areas[0]["district"], areas[0]["source_id"]), ("市本级", guide["source_id"]))
        self.assertFalse(areas[0]["can_generate"])
        for district in ("", "商州区", "洛南县"):
            result = client.get("/regional/lookup", params={**CITY, "district": district})
            self.assertEqual(result.status_code, 200)
            self.assertEqual(result.json()["templates"], [])
            self.assertIsNone(result.json()["source_id"])
        template = "shangluo-611000-worker-application-sample"
        params = {**CITY, "district": "市本级", "source_id": guide["source_id"], "version": guide["version"],
                  "kind": "application", "template_id": template}
        self.assertEqual(client.get(f"/regional/templates/{template}", params=params).status_code, 404)
        self.assertIn(client.get("/regional/form-contract", params=params).status_code, (404, 409))
        self.assertIn(client.post("/regional/generate", json={**params, "mode": "reference_adaptation", "data": {}}).status_code,
                      (404, 409))

    def test_source_proof_is_byte_pinned(self):
        from regional_shangluo_municipal_guides import PROOF, staged_guide

        root = Path(self.enterContext(TemporaryDirectory()))
        (root / PROOF).parent.mkdir(parents=True)
        (root / PROOF).write_bytes(b"modified")
        with self.assertRaises(ValueError):
            staged_guide(root)
