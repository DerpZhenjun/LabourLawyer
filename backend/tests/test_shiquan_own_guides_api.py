from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from regional_guides import RegionalStore
from routes import regional_guides as routes


ROOT = Path(__file__).resolve().parents[2]


class ShiquanOfficialAttachmentsTests(TestCase):
    def test_role_bound_materials_and_four_distinct_official_blanks(self):
        from regional_shiquan_guides import staged_guide

        guide = staged_guide(ROOT)
        self.assertEqual((guide["city"], guide["district"], guide["region_code"]), ("安康市", "石泉县", "610922"))
        self.assertFalse(guide["can_generate"])
        self.assertFalse(guide["published"])
        self.assertEqual([row["service_object"] for row in guide["materials"]], ["劳动者"] * 3 + ["用人单位"] * 3)
        self.assertEqual([row["official_name"] for row in guide["materials"] if row["service_object"] == "劳动者"],
                         ["劳动人事争议仲裁申请书", "身份证", "授权委托书"])
        self.assertEqual([row["official_name"] for row in guide["materials"] if row["service_object"] == "用人单位"],
                         ["劳动人事争议仲裁申请书", "主体资格证明材料", "授权委托书"])
        self.assertTrue(all("1114908280209" in row["source_url"] for row in guide["materials"][:3]))
        self.assertTrue(all("1110665283374" in row["source_url"] for row in guide["materials"][3:]))
        templates = guide["templates"]
        self.assertEqual(len({t["official_sha256"] for t in templates}), 4)
        self.assertEqual(len(templates), 4)
        self.assertTrue(all(t["official_kind"] == "blank" for t in templates))
        self.assertTrue(all(t["download_status"] == "official_link_only" and "file" not in t for t in templates))
        self.assertEqual([t.get("fill_method") for t in templates], ["handwritten", "handwritten", None, None])
        self.assertTrue(all(t["source_url"].startswith("https://zwfwxtzx.shaanxi.gov.cn/") for t in templates))

    def test_no_generation_or_platform_copy_and_no_neighbour_inheritance(self):
        from regional_shiquan_guides import staged_guide

        with TemporaryDirectory() as data:
            store = RegionalStore(Path(data) / "guides.sqlite")
            guide = store.put_guide(staged_guide(ROOT))
            app = FastAPI()
            app.include_router(routes.router, prefix="/regional")
            with patch.object(routes, "ROOT", ROOT), patch.object(routes, "store", return_value=store), TestClient(app) as client:
                scope = {key: guide[key] for key in ("province", "city", "district", "source_id", "version")}
                public = client.get("/regional/lookup", params={key: scope[key] for key in ("province", "city", "district")})
                self.assertEqual(public.status_code, 200, public.text)
                self.assertEqual(len(public.json()["templates"]), 4)
                for tpl in guide["templates"]:
                    query = {**scope, "template_id": tpl["id"], "kind": "application"}
                    self.assertEqual(client.get(f"/regional/templates/{tpl['id']}", params=scope).status_code, 404)
                    self.assertEqual(client.get("/regional/form-contract", params=query).status_code, 409)
                    self.assertEqual(client.post("/regional/generate", json={**query, "mode": "blank", "data": {}}).status_code, 409)
                neighbour = client.get("/regional/lookup", params={"province": "shaanxi", "city": "安康市", "district": "宁陕县"})
                self.assertEqual(neighbour.status_code, 200, neighbour.text)
                self.assertEqual(neighbour.json()["verification_status"], "unverified")
                self.assertEqual(neighbour.json()["templates"], [])

    def test_changed_proof_is_rejected(self):
        from regional_shiquan_guides import PROOF, staged_guide

        with TemporaryDirectory() as data:
            root = Path(data)
            (root / PROOF).parent.mkdir(parents=True)
            (root / PROOF).write_bytes(b'{"area":{"region_code":"610922"}}')
            with self.assertRaises(ValueError):
                staged_guide(root)
