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
DISTRICT = {**CITY, "district": "横山区"}


class HengshanOwnGuidesTests(TestCase):
    def test_role_materials_preserve_sample_labels_and_scope(self):
        from regional_hengshan_guides import staged_guide

        guide = staged_guide(ROOT)
        self.assertEqual((guide["city"], guide["district"], guide["region_code"], guide["authority"]),
                         ("榆林市", "横山区", "610803", "横山区人社局"))
        self.assertIn("劳动者事项", guide["fields"]["办理地点"])
        self.assertIn("(办理窗口:仲裁院)", guide["fields"]["办理地点"])
        self.assertIn("政务大楼2楼劳动人事争议调解仲裁窗口", guide["fields"]["办理地点"])
        self.assertEqual(guide["fields"]["承诺办结时限"].count("0 个工作日"), 2)
        self.assertEqual(guide["fields"]["咨询方式"], "0912-7618282")
        prefix = "https://zwfw.shaanxi.gov.cn/pc//#/c/service-guide?matterId="
        worker = f"{prefix}1114382136663&siteCode=610803000000"
        employer = f"{prefix}1119882126762&siteCode=610803000000"
        self.assertEqual(guide["role_sources"], {"劳动者": worker, "用人单位": employer})
        rows = guide["materials"]
        self.assertEqual([r["official_name"] for r in rows[:5]], [
            "身份证", "劳动（人事）关系证明材料", "外国人就业证", "劳动人事争议仲裁申请书", "授权委托书",
        ])
        self.assertEqual([r["official_name"] for r in rows[5:]], [
            "劳动人事争议仲裁申请书", "主体资格证明材料", "劳动（人事）关系证明材料", "授权委托书",
        ])
        self.assertEqual(len({r["id"] for r in rows}), 9)
        self.assertEqual({(r["service_object"], r["region_code"], r["source_url"], r["required"]) for r in rows},
                         {("劳动者", "610803", worker, "必要"), ("用人单位", "610803", employer, "必要")})
        self.assertEqual(rows[2]["format"], "电子和纸质")
        self.assertEqual(rows[3]["original_copy"], "原件")
        self.assertEqual(rows[3]["copies"], "原件3 份")
        self.assertEqual(rows[5]["original_copy"], "原件和复印件")
        self.assertEqual(rows[5]["copies"], "原件1 份 复印件1 份")
        notice = guide["sections"]["官网附件核验"]
        self.assertIn("范本", notice)
        self.assertIn("预填", notice)
        self.assertIn("逐字节相同", notice)
        self.assertTrue(any("范本" in warning for warning in guide["warnings"]))
        self.assertEqual(guide["verification_status"], "conflict")
        self.assertEqual(guide["templates"], [])
        self.assertFalse(guide["can_generate"])
        self.assertFalse(guide["published"])

    def test_guide_does_not_activate_sample_download_or_another_area(self):
        from regional_hengshan_guides import staged_guide

        root = Path(self.enterContext(TemporaryDirectory()))
        directory = DirectoryStore(root / "directory.sqlite")
        for row in json.loads((ROOT / "data/public-regions/directory.json").read_bytes()):
            if row["code"] in {"610800", "610802", "610803"}:
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
        row = next(area for area in areas if area["district"] == "横山区")
        self.assertEqual(row["source_id"], guide["source_id"])
        self.assertFalse(row["can_generate"])
        result = client.get("/regional/lookup", params=DISTRICT).json()
        self.assertEqual(result["role_sources"], guide["role_sources"])
        self.assertEqual(result["templates"], [])
        for district in ("", "市本级", "榆阳区", "高新区", "神木市"):
            result = client.get("/regional/lookup", params={**CITY, "district": district}).json()
            self.assertIsNone(result["source_id"])
            self.assertEqual(result["templates"], [])
        template_id = "hengshan-610803-employer-application"
        params = {**DISTRICT, "source_id": guide["source_id"], "version": guide["version"],
                  "kind": "application", "template_id": template_id}
        self.assertEqual(client.get(f"/regional/templates/{template_id}", params=params).status_code, 404)
        self.assertEqual(client.get("/regional/form-contract", params=params).status_code, 409)
        for mode in ("blank", "reference_adaptation"):
            response = client.post("/regional/generate", json={**params, "mode": mode, "data": {}})
            self.assertEqual(response.status_code, 409)

    def test_requires_byte_pinned_source_and_content_proofs(self):
        from regional_hengshan_guides import SOURCE, staged_guide

        root = Path(self.enterContext(TemporaryDirectory()))
        for path in (SOURCE,):
            with self.assertRaises(ValueError):
                staged_guide(root)
            (root / path).parent.mkdir(parents=True, exist_ok=True)
            (root / path).write_bytes((ROOT / path).read_bytes())
        self.assertEqual(staged_guide(root)["region_code"], "610803")
        for path in (SOURCE,):
            original = (ROOT / path).read_bytes()
            (root / path).write_bytes(original + b" ")
            with self.assertRaises(ValueError):
                staged_guide(root)
            (root / path).write_bytes(original)
