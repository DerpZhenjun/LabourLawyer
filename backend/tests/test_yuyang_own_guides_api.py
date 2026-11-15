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
DISTRICT = {**CITY, "district": "榆阳区"}


class YuyangOwnGuidesTests(TestCase):
    def test_role_materials_preserve_sample_labels_and_scope(self):
        from regional_yuyang_guides import staged_guide

        guide = staged_guide(ROOT)
        self.assertEqual((guide["city"], guide["district"], guide["region_code"], guide["authority"]),
                         ("榆林市", "榆阳区", "610802", "榆阳区人社局"))
        self.assertIn("上郡南路185", guide["fields"]["办理地点"])
        self.assertIn("仲裁院案件受理办公室", guide["fields"]["办理地点"])
        self.assertIn("5 个工作日", guide["fields"]["承诺办结时限"])
        self.assertIn("0912-3739566", guide["fields"]["咨询方式"])
        source = "https://zwfw.shaanxi.gov.cn/pc//#/c/service-guide?matterId=1116112144785&siteCode=610802000000"
        self.assertEqual(guide["role_sources"], {"用人单位":source})
        rows = guide["materials"]
        self.assertEqual([r["official_name"] for r in rows],
                         ["授权委托书", "劳动人事争议仲裁申请书", "申请机构法定代表人及主要负责人证明"])
        self.assertEqual({(r["service_object"], r["region_code"], r["source_url"], r["required"]) for r in rows},
                         {("用人单位", "610802", source, "必要")})
        self.assertEqual(rows[1]["original_copy"], "原件和复印件")
        self.assertEqual(rows[1]["copies"], "原件1 份 复印件2 份")
        self.assertEqual(rows[1]["format"], "纸质材料")
        notice = guide["sections"]["官网附件核验"]
        self.assertIn("空表", notice)
        self.assertIn("逐字节相同", notice)
        self.assertIn("法定代表人", notice)
        self.assertTrue(any("空白模板仍待核验" in warning for warning in guide["warnings"]))
        self.assertEqual(guide["verification_status"], "conflict")
        self.assertEqual(guide["templates"], [])
        self.assertFalse(guide["can_generate"])
        self.assertFalse(guide["published"])

    def test_guide_does_not_activate_sample_download_or_another_area(self):
        from regional_yuyang_guides import staged_guide

        root = Path(self.enterContext(TemporaryDirectory()))
        directory = DirectoryStore(root / "directory.sqlite")
        for row in json.loads((ROOT / "data/public-regions/directory.json").read_bytes()):
            if row["code"] in {"610800", "610803", "610802"}:
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
        row = next(area for area in areas if area["district"] == "榆阳区")
        self.assertEqual(row["source_id"], guide["source_id"])
        self.assertFalse(row["can_generate"])
        result = client.get("/regional/lookup", params=DISTRICT).json()
        self.assertEqual(result["role_sources"], guide["role_sources"])
        self.assertEqual(result["templates"], [])
        for district in ("", "市本级", "横山区", "高新区", "神木市"):
            result = client.get("/regional/lookup", params={**CITY, "district": district}).json()
            self.assertIsNone(result["source_id"])
            self.assertEqual(result["templates"], [])
        template_id = "yuyang-610802-employer-application"
        params = {**DISTRICT, "source_id": guide["source_id"], "version": guide["version"],
                  "kind": "application", "template_id": template_id}
        self.assertEqual(client.get(f"/regional/templates/{template_id}", params=params).status_code, 404)
        self.assertEqual(client.get("/regional/form-contract", params=params).status_code, 409)
        for mode in ("blank", "reference_adaptation"):
            response = client.post("/regional/generate", json={**params, "mode": mode, "data": {}})
            self.assertEqual(response.status_code, 409)

    def test_requires_byte_pinned_source_and_content_proofs(self):
        from regional_yuyang_guides import SOURCE, staged_guide

        root = Path(self.enterContext(TemporaryDirectory()))
        for path in (SOURCE,):
            with self.assertRaises(ValueError):
                staged_guide(root)
            (root / path).parent.mkdir(parents=True, exist_ok=True)
            (root / path).write_bytes((ROOT / path).read_bytes())
        self.assertEqual(staged_guide(root)["region_code"], "610802")
        for path in (SOURCE,):
            original = (ROOT / path).read_bytes()
            (root / path).write_bytes(original + b" ")
            with self.assertRaises(ValueError):
                staged_guide(root)
            (root / path).write_bytes(original)
