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
DISTRICT = {**CITY, "district": "华州区"}


class HuazhouOwnGuidesTests(TestCase):
    def test_role_materials_keep_labels_and_conflict(self):
        from regional_huazhou_guides import staged_guide

        guide = staged_guide(ROOT)
        self.assertEqual((guide["city"], guide["district"], guide["region_code"], guide["authority"]),
                         ("渭南市", "华州区", "610503", "渭南市华州区人力资源和社会保障局"))
        self.assertIn("二楼劳动仲裁股", guide["fields"]["办理地点"])
        self.assertIn("子仪路", guide["fields"]["办理地点"])
        self.assertIn("0 个工作日", guide["fields"]["承诺办结时限"])
        self.assertIn("0913-4733358", guide["fields"]["咨询方式"])
        for role, matter in (("劳动者", "1110811215226"), ("用人单位", "1119477206821")):
            expected = f"https://zwfw.shaanxi.gov.cn/pc//#/c/service-guide?matterId={matter}&siteCode=610503000000"
            rows = [row for row in guide["materials"] if row["service_object"] == role]
            self.assertEqual(len(rows), 4)
            self.assertEqual({(row["region_code"], row["required"], row["source_url"]) for row in rows},
                             {("610503", "必要", expected)})
            self.assertEqual(guide["role_sources"][role], expected)
        notice = guide["sections"]["官网附件核验"]
        self.assertIn("7 对", notice)
        self.assertIn("逐字节相同", notice)
        self.assertIn("法定代表人（或主要负责人）身份证明书", notice)
        self.assertEqual(guide["verification_status"], "conflict")
        self.assertEqual(guide["templates"], [])
        self.assertFalse(guide["can_generate"])
        self.assertFalse(guide["published"])

    def test_guide_does_not_activate_sample_download_or_another_area(self):
        from regional_huazhou_guides import staged_guide

        root = Path(self.enterContext(TemporaryDirectory()))
        directory = DirectoryStore(root / "directory.sqlite")
        for row in json.loads((ROOT / "data/public-regions/directory.json").read_bytes()):
            if row["code"] in {"610500", "610502", "610503"}:
                directory.put_area(row)
        store = RegionalStore(root / "guides.sqlite")
        guide = store.put_guide(staged_guide(ROOT))
        app = FastAPI()
        app.include_router(routes.router, prefix="/regional")
        self.enterContext(patch.object(routes, "ROOT", ROOT))
        self.enterContext(patch.object(routes, "store", return_value=store))
        self.enterContext(patch.object(routes, "directory_store", return_value=directory))
        client = self.enterContext(TestClient(app))

        areas = client.get("/regional/areas", params=CITY).json()["items"]
        row = next(area for area in areas if area["district"] == "华州区")
        self.assertEqual(row["source_id"], guide["source_id"])
        self.assertFalse(row["can_generate"])
        result = client.get("/regional/lookup", params=DISTRICT).json()
        self.assertEqual(result["role_sources"], guide["role_sources"])
        self.assertEqual(result["templates"], [])
        for district in ("", "市本级", "临渭区", "高新区"):
            result = client.get("/regional/lookup", params={**CITY, "district": district}).json()
            self.assertIsNone(result["source_id"])
            self.assertEqual(result["templates"], [])
        template_id = "huazhou-610503-worker-application"
        params = {**DISTRICT, "source_id": guide["source_id"], "version": guide["version"],
                  "kind": "application", "template_id": template_id}
        self.assertEqual(client.get(f"/regional/templates/{template_id}", params=params).status_code, 404)
        self.assertEqual(client.get("/regional/form-contract", params=params).status_code, 409)
        for mode in ("blank", "reference_adaptation"):
            response = client.post("/regional/generate", json={**params, "mode": mode, "data": {}})
            self.assertEqual(response.status_code, 409)

    def test_requires_byte_pinned_source_and_content_proofs(self):
        from regional_huazhou_guides import SOURCE, staged_guide

        root = Path(self.enterContext(TemporaryDirectory()))
        for path in (SOURCE,):
            with self.assertRaises(ValueError):
                staged_guide(root)
            (root / path).parent.mkdir(parents=True, exist_ok=True)
            (root / path).write_bytes((ROOT / path).read_bytes())
        self.assertEqual(staged_guide(root)["region_code"], "610503")
        for path in (SOURCE,):
            original = (ROOT / path).read_bytes()
            (root / path).write_bytes(original + b" ")
            with self.assertRaises(ValueError):
                staged_guide(root)
            (root / path).write_bytes(original)
