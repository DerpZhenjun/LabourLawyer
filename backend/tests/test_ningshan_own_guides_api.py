from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from regional_guides import RegionalStore
from routes import regional_guides as routes


ROOT = Path(__file__).resolve().parents[2]


class NingshanOwnGuidesTests(TestCase):
    def test_role_sources_and_addresses_are_not_combined_into_one_requirement(self):
        from regional_ningshan_guides import staged_guide

        guide = staged_guide(ROOT)
        self.assertEqual((guide["city"], guide["district"], guide["region_code"]), ("安康市", "宁陕县", "610923"))
        worker, employer = guide["materials"][:4], guide["materials"][4:]
        self.assertEqual([row["service_object"] for row in worker], ["劳动者"] * 4)
        self.assertEqual([row["service_object"] for row in employer], ["用人单位"] * 4)
        self.assertTrue(all("1118247286707" in row["source_url"] for row in worker))
        self.assertTrue(all("1119437277504" in row["source_url"] for row in employer))
        self.assertIn("劳动者事项：宁陕县城关镇迎宾大道32号", guide["fields"]["办理地点"])
        self.assertIn("用人单位事项：宁陕县城关镇长安街13号", guide["fields"]["办理地点"])
        self.assertIn("三份", guide["sections"]["申请书份数"])
        self.assertIn("两份", guide["sections"]["申请书份数"])
        self.assertFalse(guide["published"])

    def test_link_only_templates_exclude_role_mismatches_and_never_generate(self):
        from regional_ningshan_guides import staged_guide

        data = self.enterContext(TemporaryDirectory())
        store = RegionalStore(Path(data) / "guides.sqlite")
        guide = store.put_guide(staged_guide(ROOT))
        app = FastAPI()
        app.include_router(routes.router, prefix="/regional")
        self.enterContext(patch.object(routes, "ROOT", ROOT))
        self.enterContext(patch.object(routes, "store", return_value=store))
        client = self.enterContext(TestClient(app))
        scope = {key: guide[key] for key in ("province", "city", "district", "source_id", "version")}
        response = client.get("/regional/lookup", params={key: scope[key] for key in ("province", "city", "district")})
        self.assertEqual(response.status_code, 200, response.text)
        public = response.json()
        self.assertFalse(public["can_generate"])
        templates = public["templates"]
        self.assertEqual([t["official_kind"] for t in templates], ["sample", "sample", "blank"])
        self.assertEqual([t["service_object"] for t in templates], ["劳动者", "用人单位", "劳动者"])
        self.assertTrue(all(t["download_status"] == "official_link_only" and "file" not in t for t in templates))
        self.assertIn("1118247286707", templates[0]["source_url"])
        self.assertIn("1119437277504", templates[1]["source_url"])
        self.assertTrue(templates[2]["source_url"].endswith("710.doc"))
        for t in templates:
            bind = {**scope, "template_id": t["id"], "kind": "application"}
            self.assertEqual(client.get(f"/regional/templates/{t['id']}", params=scope).status_code, 404)
            self.assertEqual(client.get("/regional/form-contract", params=bind).status_code, 409)
            for mode in ("blank", "reference_adaptation"):
                self.assertEqual(client.post("/regional/generate", json={**bind, "mode": mode, "data": {}}).status_code, 409)
        neighbour = client.get("/regional/lookup", params={"province": "shaanxi", "city": "安康市", "district": "紫阳县"})
        self.assertEqual(neighbour.status_code, 200, neighbour.text)
        self.assertEqual(neighbour.json()["templates"], [])

    def test_changed_proof_is_rejected(self):
        from regional_ningshan_guides import PROOF, staged_guide

        root = Path(self.enterContext(TemporaryDirectory()))
        (root / PROOF).parent.mkdir(parents=True)
        (root / PROOF).write_bytes(b'{"area":{"region_code":"610923"}}')
        with self.assertRaises(ValueError):
            staged_guide(root)
