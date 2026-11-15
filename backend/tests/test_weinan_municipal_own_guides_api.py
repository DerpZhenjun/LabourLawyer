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
CITY = {"province": "shaanxi", "city": "渭南市"}
MUNICIPAL = {**CITY, "district": "市本级"}


class WeinanMunicipalOfficialGuidesTests(TestCase):
    def test_role_windows_and_source_links_are_preserved(self):
        from regional_weinan_municipal_guides import staged_guide

        guide = staged_guide(ROOT)
        self.assertEqual((guide["district"], guide["scope_level"], guide["region_code"], guide["authority"]),
                         ("市本级", "municipal", "610500", "渭南市人力资源和社会保障局"))
        self.assertEqual(guide["fields"]["承诺办结时限"], "5 个工作日")
        self.assertIn("709办公室", guide["fields"]["办理地点"])
        self.assertIn("709室", guide["fields"]["办理地点"])
        self.assertIn("0913-2363017", guide["fields"]["咨询方式"])
        self.assertEqual(len(guide["materials"]), 2)
        for row, role, matter in zip(guide["materials"], ("劳动者", "用人单位"),
                                     ("1113560176120", "1112609175553"), strict=True):
            expected = f"https://zwfw.shaanxi.gov.cn/pc//#/c/service-guide?matterId={matter}&siteCode=610500000000"
            self.assertEqual((row["service_object"], row["source_url"], row["region_code"], row["required"]),
                             (role, expected, "610500", "必要"))
            self.assertEqual(guide["role_sources"][role], expected)
        self.assertIn("样表", guide["sections"]["官网附件核验"])
        self.assertEqual(guide["templates"], [])
        self.assertFalse(guide["published"])
        self.assertFalse(guide["can_generate"])

    def test_public_routes_expose_only_exact_municipal_candidate(self):
        from regional_weinan_municipal_guides import staged_guide

        root = Path(self.enterContext(TemporaryDirectory()))
        directory = DirectoryStore(root / "areas.sqlite")
        for row in json.loads((ROOT / "data/public-regions/directory.json").read_bytes()):
            if row["code"] in {"610500", "610502", "610503"}:
                directory.put_area(row)
        store = RegionalStore(root / "guides.sqlite")
        app = FastAPI()
        app.include_router(routes.router, prefix="/regional")
        self.enterContext(patch.object(routes, "ROOT", ROOT))
        self.enterContext(patch.object(routes, "store", return_value=store))
        self.enterContext(patch.object(routes, "directory_store", return_value=directory))
        client = self.enterContext(TestClient(app))

        candidate = staged_guide(ROOT)
        store.put_guide({**candidate, "source_version": "0" * 64})
        areas = client.get("/regional/areas", params=CITY).json()["items"]
        self.assertNotIn("市本级", {area["district"] for area in areas})

        guide = store.put_guide(candidate)
        areas = client.get("/regional/areas", params=CITY).json()["items"]
        municipal = next(area for area in areas if area["district"] == "市本级")
        self.assertEqual(municipal["source_id"], guide["source_id"])
        self.assertFalse(municipal["can_generate"])
        lookup = client.get("/regional/lookup", params=MUNICIPAL).json()
        self.assertEqual(lookup["role_sources"], guide["role_sources"])
        self.assertEqual(lookup["templates"], [])
        for district in ("", "临渭区", "华州区", "高新区"):
            result = client.get("/regional/lookup", params={**CITY, "district": district}).json()
            self.assertIsNone(result["source_id"])
            self.assertEqual(result["templates"], [])

        template_id = "weinan-610500-worker-application-sample"
        params = {**MUNICIPAL, "source_id": guide["source_id"], "version": guide["version"],
                  "kind": "application", "template_id": template_id}
        self.assertEqual(client.get(f"/regional/templates/{template_id}", params=params).status_code, 404)
        self.assertIn(client.get("/regional/form-contract", params=params).status_code, (404, 409))
        self.assertIn(client.post("/regional/generate", json={**params, "mode": "reference_adaptation", "data": {}}).status_code,
                      (404, 409))

    def test_missing_or_modified_own_proof_is_rejected(self):
        from regional_weinan_municipal_guides import PROOF, staged_guide

        root = Path(self.enterContext(TemporaryDirectory()))
        with self.assertRaises(ValueError):
            staged_guide(root)
        (root / PROOF).parent.mkdir(parents=True)
        (root / PROOF).write_bytes((ROOT / PROOF).read_bytes() + b" ")
        with self.assertRaises(ValueError):
            staged_guide(root)
