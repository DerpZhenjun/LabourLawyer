import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from regional_directory import DirectoryStore
from regional_guides import RegionalStore
from routes import regional_guides as routes


ROOT = Path(__file__).resolve().parents[2]
CITY = {"province": "shaanxi", "city": "商洛市"}
DISTRICT = {**CITY, "district": "商州区"}


class ShangzhouOwnOfficialGuidesTests(TestCase):
    def test_candidate_preserves_role_sources_and_official_time_display(self):
        from regional_shangzhou_guides import staged_guide

        guide = staged_guide(ROOT)
        self.assertEqual((guide["city"], guide["district"], guide["region_code"], guide["authority"]),
                         ("商洛市", "商州区", "611002", "商州区人社局"))
        self.assertEqual([m["service_object"] for m in guide["materials"]], ["劳动者"] * 4 + ["用人单位"] * 4)
        self.assertEqual({m["region_code"] for m in guide["materials"]}, {"611002"})
        self.assertIn("人社局202", guide["fields"]["办理地点"])
        self.assertEqual(guide["fields"]["承诺办结时限"], "劳动者事项：官网显示 0 个工作日。用人单位事项：3 个工作日。")
        self.assertIn("核实", guide["sections"]["承诺时限说明"])
        self.assertIn("8 个", guide["sections"]["官网附件核验"])
        for role, matter in (("劳动者", "1119288134594"), ("用人单位", "1118197133804")):
            source = guide["role_sources"][role]
            self.assertTrue(source.endswith(f"matterId={matter}&siteCode=611002000000"))
            self.assertEqual({m["source_url"] for m in guide["materials"] if m["service_object"] == role}, {source})
        self.assertEqual(guide["templates"], [])
        self.assertFalse(guide["published"])
        self.assertFalse(guide["can_generate"])

    def test_exact_district_lookup_has_no_generation_or_neighbor_inheritance(self):
        from regional_shangzhou_guides import staged_guide

        root = Path(self.enterContext(TemporaryDirectory()))
        store = RegionalStore(root / "guides.sqlite")
        directory = DirectoryStore(root / "areas.sqlite")
        for row in json.loads((ROOT / "data/public-regions/directory.json").read_bytes()):
            if row["code"] in {"611000", "611002", "611021"}:
                directory.put_area(row)
        app = FastAPI()
        app.include_router(routes.router, prefix="/regional")
        self.enterContext(patch.object(routes, "ROOT", ROOT))
        self.enterContext(patch.object(routes, "store", return_value=store))
        self.enterContext(patch.object(routes, "directory_store", return_value=directory))
        client = self.enterContext(TestClient(app))

        guide = store.put_guide(staged_guide(ROOT))
        areas = client.get("/regional/areas", params=CITY).json()["items"]
        shangzhou = next(area for area in areas if area["district"] == "商州区")
        self.assertEqual(shangzhou["source_id"], guide["source_id"])
        self.assertFalse(shangzhou["can_generate"])
        result = client.get("/regional/lookup", params=DISTRICT).json()
        self.assertEqual(result["role_sources"], guide["role_sources"])
        self.assertEqual(result["templates"], [])
        for district in ("", "市本级", "洛南县"):
            result = client.get("/regional/lookup", params={**CITY, "district": district}).json()
            self.assertIsNone(result["source_id"])
            self.assertEqual(result["templates"], [])
        template = "shangzhou-611002-worker-application"
        params = {**DISTRICT, "source_id": guide["source_id"], "version": guide["version"],
                  "kind": "application", "template_id": template}
        self.assertEqual(client.get(f"/regional/templates/{template}", params=params).status_code, 404)
        self.assertIn(client.get("/regional/form-contract", params=params).status_code, (404, 409))
        self.assertIn(client.post("/regional/generate", json={**params, "mode": "reference_adaptation", "data": {}}).status_code,
                      (404, 409))

    def test_requires_unchanged_local_source_proof(self):
        from regional_shangzhou_guides import PROOF, staged_guide

        root = Path(self.enterContext(TemporaryDirectory()))
        with self.assertRaises(ValueError):
            staged_guide(root)
        (root / PROOF).parent.mkdir(parents=True)
        (root / PROOF).write_bytes((ROOT / PROOF).read_bytes() + b" ")
        with self.assertRaises(ValueError):
            staged_guide(root)
