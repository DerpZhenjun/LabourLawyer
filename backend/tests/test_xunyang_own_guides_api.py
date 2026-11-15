from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from regional_guides import RegionalStore
from routes import regional_guides as routes


ROOT = Path(__file__).resolve().parents[2]


class XunyangOfficialGuidesTests(TestCase):
    def test_binds_current_city_code_and_keeps_both_samples_distinct(self):
        from regional_xunyang_guides import staged_guide

        guide = staged_guide(ROOT)
        self.assertEqual((guide["city"], guide["district"], guide["region_code"]), ("安康市", "旬阳市", "610981"))
        self.assertEqual([m["service_object"] for m in guide["materials"]], ["劳动者"] * 2 + ["用人单位"] * 2)
        self.assertEqual([m["required"] for m in guide["materials"]], ["必要"] * 4)
        self.assertIn("前楼404室", guide["fields"]["办理地点"])
        self.assertIn("5 个工作日", guide["fields"]["承诺办结时限"])
        self.assertFalse(guide["published"])
        self.assertFalse(guide["can_generate"])
        templates = guide["templates"]
        self.assertEqual([t["service_object"] for t in templates], ["劳动者", "用人单位"])
        self.assertNotEqual(templates[0]["official_sha256"], templates[1]["official_sha256"])
        self.assertTrue(all(t["official_kind"] == "sample" and t["download_status"] == "official_link_only"
                            and "siteCode=610981000000" in t["source_url"] and "file" not in t for t in templates))
        self.assertFalse(any("身份证" in t["original_name"] or "主体资格" in t["original_name"] for t in templates))

    def test_samples_cannot_be_proxied_or_used_for_generation(self):
        from regional_xunyang_guides import staged_guide

        data = self.enterContext(TemporaryDirectory())
        store = RegionalStore(Path(data) / "guides.sqlite")
        guide = store.put_guide(staged_guide(ROOT))
        app = FastAPI()
        app.include_router(routes.router, prefix="/regional")
        self.enterContext(patch.object(routes, "ROOT", ROOT))
        self.enterContext(patch.object(routes, "store", return_value=store))
        client = self.enterContext(TestClient(app))
        bound = {key: guide[key] for key in ("province", "city", "district", "source_id", "version")}
        for template in guide["templates"]:
            self.assertEqual(client.get(f"/regional/templates/{template['id']}", params=bound).status_code, 404)
            params = {**bound, "template_id": template["id"], "kind": "application"}
            self.assertEqual(client.get("/regional/form-contract", params=params).status_code, 409)
            for mode in ("blank", "reference_adaptation"):
                self.assertEqual(client.post("/regional/generate", json={**params, "mode": mode, "data": {}}).status_code, 409)
        for district in ("旬阳县", "白河县"):
            other = client.get("/regional/lookup", params={"province": "shaanxi", "city": "安康市", "district": district})
            self.assertEqual(other.status_code, 200, other.text)
            self.assertEqual(other.json()["templates"], [])

    def test_rejects_changed_source_proof(self):
        from regional_xunyang_guides import PROOF, staged_guide

        directory = Path(self.enterContext(TemporaryDirectory()))
        (directory / PROOF).parent.mkdir(parents=True)
        (directory / PROOF).write_bytes((ROOT / PROOF).read_bytes() + b"\n")
        with self.assertRaises(ValueError):
            staged_guide(directory)
