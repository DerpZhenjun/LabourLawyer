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
CITY = {"province": "shaanxi", "city": "咸阳市"}
AREA = {**CITY, "district": "三原县"}
WORKER = "https://zwfw.shaanxi.gov.cn/pc//#/c/service-guide?matterId=1116001147713&siteCode=610422000000"
EMPLOYER = "https://zwfw.shaanxi.gov.cn/pc//#/c/service-guide?matterId=1118123147108&siteCode=610422000000"


class XianyangSanyuanOwnGuideTests(TestCase):
    def test_preserves_role_specific_sources_materials_and_login_boundary(self):
        from regional_xianyang_sanyuan_guides import staged_guide

        guide = staged_guide(ROOT)
        self.assertEqual((guide["region_code"], guide["district"]), ("610422", "三原县"))
        self.assertEqual(guide["role_sources"], {"劳动者": WORKER, "用人单位": EMPLOYER})
        self.assertIn("劳动者：4 个工作日", guide["fields"]["承诺办结时限"])
        self.assertIn("用人单位：5 个工作日", guide["fields"]["承诺办结时限"])
        self.assertIn("8楼仲裁股", guide["fields"]["办理地点"])
        self.assertEqual(guide["channel"]["online_status"], "auth_required")
        self.assertIsNone(guide["channel"]["entry_url"])
        self.assertFalse(guide["channel"]["submission_verified"])
        self.assertIn("统一身份认证", guide["sections"]["办理渠道核验"])
        self.assertIn("713800", guide["sections"]["办理渠道核验"])
        self.assertIn("同一份 DOCX", guide["sections"]["官网附件核验"])
        self.assertIn("证据清单", guide["sections"]["官网附件核验"])
        rows = guide["materials"]
        self.assertEqual(
            [(row["official_name"], row["service_object"], row["copies"], row["source_url"]) for row in rows],
            [
                ("劳动人事争议仲裁申请书", "劳动者", "原件2份", WORKER),
                ("身份证", "劳动者", "原件1份、复印件2份", WORKER),
                ("劳动（人事）关系证明材料", "劳动者", "复印件2份", WORKER),
                ("劳动人事争议仲裁申请书", "用人单位", "原件2份", EMPLOYER),
                ("劳动（人事）关系证明材料", "用人单位", "原件2份、复印件2份", EMPLOYER),
            ],
        )
        self.assertEqual(guide["templates"], [])
        self.assertFalse(guide["published"])
        self.assertFalse(guide["can_generate"])

    def test_sanyuan_cannot_inherit_or_enable_local_generation(self):
        from regional_xianyang_municipal_guides import staged_guide as staged_municipal
        from regional_xianyang_sanyuan_guides import staged_guide

        root = Path(self.enterContext(TemporaryDirectory()))
        directory = DirectoryStore(root / "directory.sqlite")
        for area in json.loads((ROOT / "data/public-regions/directory.json").read_bytes()):
            if area["code"] in {"610400", "610402", "610404", "610405", "610422", "610481"}:
                directory.put_area(area)
        store = RegionalStore(root / "guides.sqlite")
        municipal = store.put_guide(staged_municipal(ROOT))
        item = store.put_guide(staged_guide(ROOT))
        self.enterContext(patch.object(routes, "ROOT", root))
        self.enterContext(patch.object(routes, "store", return_value=store))
        self.enterContext(patch.object(routes, "directory_store", return_value=directory))
        app = FastAPI()
        app.include_router(routes.router, prefix="/regional")
        client = self.enterContext(TestClient(app))

        own = client.get("/regional/lookup", params=AREA).json()
        self.assertEqual(own["source_id"], item["source_id"])
        self.assertEqual(own["templates"], [])
        self.assertEqual(len(own["materials"]), 5)
        city = client.get("/regional/lookup", params={**CITY, "district": "市本级"}).json()
        self.assertEqual(city["source_id"], municipal["source_id"])
        for district in ("", "渭城区", "高新区", "兴平市"):
            with self.subTest(district=district):
                other = client.get("/regional/lookup", params={**CITY, "district": district}).json()
                self.assertIsNone(other["source_id"])
                self.assertEqual(other["templates"], [])
        params = {**AREA, "source_id": item["source_id"], "version": item["version"],
                  "kind": "application", "template_id": "xianyang-sanyuan-application"}
        self.assertEqual(client.get("/regional/form-contract", params=params).status_code, 409)
        payload = {**params, "mode": "blank", "data": {}}
        self.assertEqual(client.post("/regional/generate", json=payload).status_code, 409)

    def test_modified_source_proof_is_rejected(self):
        from regional_xianyang_sanyuan_guides import SOURCE, staged_guide

        root = Path(self.enterContext(TemporaryDirectory()))
        target = root / SOURCE
        target.parent.mkdir(parents=True)
        with self.assertRaises(ValueError):
            staged_guide(root)
        original = (ROOT / SOURCE).read_bytes()
        target.write_bytes(original)
        self.assertEqual(staged_guide(root)["region_code"], "610422")
        target.write_bytes(original + b" ")
        with self.assertRaises(ValueError):
            staged_guide(root)
