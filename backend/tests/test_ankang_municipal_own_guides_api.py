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
CITY = {"province": "shaanxi", "city": "安康市"}
MUNICIPAL = {**CITY, "district": "市本级"}


class AnkangMunicipalOfficialGuidesTests(TestCase):
    def test_staged_guide_preserves_role_materials_and_original_sample_metadata(self):
        from regional_ankang_municipal_guides import exact_municipal, staged_guide

        guide = staged_guide(ROOT)
        self.assertTrue(exact_municipal(guide))
        self.assertFalse(exact_municipal({**guide, "district": "高新区"}))
        self.assertFalse(exact_municipal({**guide, "source_version": "different"}))
        self.assertEqual(guide["scope_level"], "municipal")
        self.assertEqual(guide["region_code"], "610900")
        self.assertFalse(guide["published"])
        self.assertFalse(guide["can_generate"])
        self.assertIn("947室", guide["fields"]["办理地点"])
        self.assertEqual(guide["fields"]["承诺办结时限"], "5 个工作日")
        self.assertEqual([m["service_object"] for m in guide["materials"]], ["劳动者"] * 5 + ["用人单位"] * 4)
        templates = guide["templates"]
        self.assertEqual([t["file_type"] for t in templates], ["doc", "pdf", "doc", "pdf"])
        self.assertTrue(all(t["official_kind"] == "sample" and t["download_status"] == "official_link_only"
                            and "siteCode=610900000000" in t["source_url"] and "file" not in t for t in templates))
        self.assertNotEqual(templates[0]["official_sha256"], templates[2]["official_sha256"])
        self.assertEqual(templates[1]["official_sha256"], templates[3]["official_sha256"])
        self.assertFalse(any("营业执照" in t["original_name"] or "关系证明" in t["original_name"] for t in templates))

    def test_city_choice_is_explicit_and_never_inherited_by_address_districts(self):
        from regional_ankang_municipal_guides import staged_guide

        root = Path(self.enterContext(TemporaryDirectory()))
        store = RegionalStore(root / "guides.sqlite")
        directory = DirectoryStore(root / "areas.sqlite")
        for row in json.loads((ROOT / "data/public-regions/directory.json").read_bytes()):
            if row["code"] in ("610900", "610902", "610930"):
                directory.put_area(row)
        app = FastAPI()
        app.include_router(routes.router, prefix="/regional")
        self.enterContext(patch.object(routes, "ROOT", ROOT))
        self.enterContext(patch.object(routes, "store", return_value=store))
        self.enterContext(patch.object(routes, "directory_store", return_value=directory))
        client = self.enterContext(TestClient(app))

        self.assertNotIn("市本级", [a["district"] for a in client.get("/regional/areas", params=CITY).json()["items"]])
        guide = store.put_guide(staged_guide(ROOT))
        area = client.get("/regional/areas", params=CITY).json()["items"][0]
        self.assertEqual((area["district"], area["region_code"], area["source_id"]),
                         ("市本级", "610900", guide["source_id"]))
        self.assertFalse(area["can_generate"])
        for district in ("", "汉滨区", "高新区", "恒口示范区", "瀛湖生态旅游区"):
            query = {**CITY, "district": district}
            result = client.get("/regional/lookup", params=query)
            self.assertEqual(result.status_code, 200)
            self.assertIsNone(result.json()["source_id"])
        bound = {**MUNICIPAL, "source_id": guide["source_id"], "version": guide["version"], "kind": "application"}
        for template in guide["templates"]:
            template_id = template["id"]
            query = {**bound, "template_id": template_id}
            self.assertEqual(client.get(f"/regional/templates/{template_id}", params=query).status_code, 404)
            self.assertEqual(client.get("/regional/form-contract", params=query).status_code, 409)
            for mode in ("blank", "reference_adaptation"):
                self.assertEqual(client.post("/regional/generate", json={**query, "mode": mode, "data": {}}).status_code, 409)

    def test_source_proof_is_byte_pinned(self):
        from regional_ankang_municipal_guides import PROOF, staged_guide

        root = Path(self.enterContext(TemporaryDirectory()))
        (root / PROOF).parent.mkdir(parents=True)
        (root / PROOF).write_bytes((ROOT / PROOF).read_bytes() + b"\n")
        with self.assertRaises(ValueError):
            staged_guide(root)
