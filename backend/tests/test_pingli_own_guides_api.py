from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from regional_guides import RegionalStore
from routes import regional_guides as routes


ROOT = Path(__file__).resolve().parents[2]


class PingliOfficialGuideTests(TestCase):
    def test_own_guides_preserve_role_specific_windows_and_sample_classification(self):
        from regional_pingli_guides import staged_guide

        guide = staged_guide(ROOT)
        self.assertEqual((guide["city"], guide["district"], guide["region_code"]), ("安康市", "平利县", "610926"))
        self.assertIn("劳动者事项：", guide["fields"]["办理地点"])
        self.assertIn("一楼西区", guide["fields"]["办理地点"])
        self.assertIn("用人单位事项：", guide["fields"]["办理地点"])
        self.assertIn("一楼东区", guide["fields"]["办理地点"])
        self.assertEqual([row["service_object"] for row in guide["materials"]], ["劳动者"] * 4 + ["用人单位"] * 3)
        self.assertEqual([row["required"] for row in guide["materials"]], ["必要"] * 7)
        self.assertIn("无固定样式", guide["materials"][2]["instructions"])
        self.assertFalse(guide["published"])
        self.assertFalse(guide["can_generate"])
        templates = guide["templates"]
        self.assertEqual(len(templates), 6)
        self.assertEqual([item["service_object"] for item in templates], ["劳动者"] * 3 + ["用人单位"] * 3)
        self.assertTrue(all(t["official_kind"] == "sample" and t["download_status"] == "official_link_only"
                            and t["official_attachment_entry"] == "material_tab" and "file" not in t for t in templates))
        self.assertFalse(any("身份证" in t["original_name"] for t in templates))
        self.assertTrue(all("matterId=" in t["source_url"] for t in templates))

    def test_api_denies_both_generation_modes_and_original_proxy(self):
        from regional_pingli_guides import staged_guide

        directory = self.enterContext(TemporaryDirectory())
        store = RegionalStore(Path(directory) / "guides.sqlite")
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
        other = client.get("/regional/lookup", params={"province": "shaanxi", "city": "安康市", "district": "镇坪县"})
        self.assertEqual(other.status_code, 200, other.text)
        self.assertEqual(other.json()["templates"], [])

    def test_source_receipt_byte_pin(self):
        from regional_pingli_guides import PROOF, staged_guide

        directory = Path(self.enterContext(TemporaryDirectory()))
        (directory / PROOF).parent.mkdir(parents=True)
        (directory / PROOF).write_bytes((ROOT / PROOF).read_bytes() + b"\n")
        with self.assertRaises(ValueError):
            staged_guide(directory)
