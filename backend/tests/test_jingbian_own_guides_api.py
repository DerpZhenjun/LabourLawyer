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
CITY = {"province": "shaanxi", "city": "榆林市"}
DISTRICT = {**CITY, "district": "靖边县"}


class JingbianOwnGuidesTests(TestCase):
    def test_role_materials_preserve_sample_labels_and_scope(self):
        from regional_jingbian_guides import staged_guide

        guide = staged_guide(ROOT)
        self.assertEqual((guide["city"], guide["district"], guide["region_code"], guide["authority"]),
                         ("榆林市", "靖边县", "610824", "靖边县人力资源和社会保障局"))
        self.assertIn("劳动者事项", guide["fields"]["办理地点"])
        self.assertIn("用人单位事项", guide["fields"]["办理地点"])
        self.assertEqual(guide["fields"]["办理地点"].count("办理窗口:88"), 2)
        self.assertEqual(guide["fields"]["承诺办结时限"].count("5 个工作日"), 2)
        self.assertEqual(guide["fields"]["咨询方式"], "0912-4611349")
        prefix = "https://zwfw.shaanxi.gov.cn/pc//#/c/service-guide?matterId="
        worker = f"{prefix}1115711136362&siteCode=610824000000"
        employer = f"{prefix}1111789141933&siteCode=610824000000"
        self.assertEqual(guide["role_sources"], {"劳动者": worker, "用人单位": employer})
        rows = guide["materials"]
        self.assertEqual(len({r["id"] for r in rows}), 2)
        for row in rows:
            self.assertEqual(
                (row["official_name"], row["region_code"], row["required"],
                 row["original_copy"], row["format"], row["copies"]),
                ("劳动人事争议仲裁申请书", "610824", "必要", "原件", "纸质材料", "原件2 份"),
            )
        self.assertEqual([(r["service_object"], r["source_url"]) for r in rows],
                         [("劳动者", worker), ("用人单位", employer)])
        notice = guide["sections"]["官网附件核验"]
        self.assertIn("样本", notice)
        self.assertIn("预填", notice)
        self.assertIn("逐字节相同", notice)
        self.assertTrue(any("样本" in warning for warning in guide["warnings"]))
        self.assertEqual(guide["verification_status"], "conflict")
        self.assertEqual(guide["templates"], [])
        self.assertFalse(guide["can_generate"])
        self.assertFalse(guide["published"])

    def test_guide_does_not_activate_sample_download_or_another_area(self):
        from regional_jingbian_guides import staged_guide

        root = Path(self.enterContext(TemporaryDirectory()))
        directory = DirectoryStore(root / "directory.sqlite")
        for row in json.loads((ROOT / "data/public-regions/directory.json").read_bytes()):
            if row["code"] in {"610800", "610802", "610803", "610824"}:
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
        row = next(area for area in areas if area["district"] == "靖边县")
        self.assertEqual(row["source_id"], guide["source_id"])
        self.assertFalse(row["can_generate"])
        result = client.get("/regional/lookup", params=DISTRICT).json()
        self.assertEqual(result["role_sources"], guide["role_sources"])
        self.assertEqual(result["templates"], [])
        for district in ("", "市本级", "横山区", "榆阳区", "高新区", "神木市"):
            result = client.get("/regional/lookup", params={**CITY, "district": district}).json()
            self.assertIsNone(result["source_id"])
            self.assertEqual(result["templates"], [])
        template_id = "jingbian-610824-employer-application"
        params = {**DISTRICT, "source_id": guide["source_id"], "version": guide["version"],
                  "kind": "application", "template_id": template_id}
        self.assertEqual(client.get(f"/regional/templates/{template_id}", params=params).status_code, 404)
        self.assertEqual(client.get("/regional/form-contract", params=params).status_code, 409)
        for mode in ("blank", "reference_adaptation"):
            response = client.post("/regional/generate", json={**params, "mode": mode, "data": {}})
            self.assertEqual(response.status_code, 409)

    def test_requires_byte_pinned_source_and_content_proofs(self):
        from regional_jingbian_guides import SOURCE, staged_guide

        root = Path(self.enterContext(TemporaryDirectory()))
        for path in (SOURCE,):
            with self.assertRaises(ValueError):
                staged_guide(root)
            (root / path).parent.mkdir(parents=True, exist_ok=True)
            (root / path).write_bytes((ROOT / path).read_bytes())
        self.assertEqual(staged_guide(root)["region_code"], "610824")
        for path in (SOURCE,):
            original = (ROOT / path).read_bytes()
            (root / path).write_bytes(original + b" ")
            with self.assertRaises(ValueError):
                staged_guide(root)
            (root / path).write_bytes(original)
