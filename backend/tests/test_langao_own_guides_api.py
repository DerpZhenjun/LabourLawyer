from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from regional_guides import RegionalStore
from routes import regional_guides as routes


ROOT = Path(__file__).resolve().parents[2]


class LangaoOfficialGuideTests(TestCase):
    def test_separate_role_channels_and_sample_metadata_preserve_source_notes(self):
        from regional_langao_guides import staged_guide

        guide = staged_guide(ROOT)
        self.assertEqual((guide["city"], guide["district"], guide["region_code"]), ("安康市", "岚皋县", "610925"))
        self.assertEqual([row["service_object"] for row in guide["materials"]], ["劳动者"] * 2 + ["用人单位"] * 3)
        self.assertIn("208室", guide["fields"]["办理地点"])
        self.assertIn("仲裁股", guide["fields"]["办理地点"])
        self.assertIn("打印", guide["sections"]["申请书填写说明"])
        self.assertIn("被申请人人数", guide["materials"][2]["instructions"])
        self.assertFalse(guide["can_generate"])
        self.assertFalse(guide["published"])
        templates = guide["templates"]
        self.assertEqual(len(templates), 5)
        self.assertEqual([item["service_object"] for item in templates], ["劳动者"] * 2 + ["用人单位"] * 3)
        self.assertEqual(templates[0]["official_sha256"], templates[2]["official_sha256"])
        self.assertEqual(templates[1]["official_sha256"], templates[4]["official_sha256"])
        self.assertTrue(all(t["official_kind"] == "sample" and t["download_status"] == "official_link_only"
                            and t["official_attachment_entry"] == "material_tab" and "file" not in t for t in templates))

    def test_api_rejects_original_proxy_and_blank_or_reference_generation(self):
        from regional_langao_guides import staged_guide

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
        other = client.get("/regional/lookup", params={"province": "shaanxi", "city": "安康市", "district": "平利县"})
        self.assertEqual(other.status_code, 200, other.text)
        self.assertEqual(other.json()["templates"], [])

    def test_pins_both_verification_files(self):
        from regional_langao_guides import NOTES, PROOF, staged_guide

        root = Path(self.enterContext(TemporaryDirectory()))
        (root / PROOF).parent.mkdir(parents=True)
        for changed in (PROOF, NOTES):
            for path in (PROOF, NOTES):
                (root / path).write_bytes(b"changed" if changed == path else (ROOT / path).read_bytes())
            with self.assertRaises(ValueError):
                staged_guide(root)
