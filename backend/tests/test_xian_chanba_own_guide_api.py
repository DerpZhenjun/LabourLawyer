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
CITY = {"province": "shaanxi", "city": "西安市"}
AREA = {**CITY, "district": "西安浐灞国际港"}


class XianChanbaOwnGuideTests(TestCase):
    def test_keeps_roles_and_material_counts_from_their_own_guides(self):
        from regional_xian_chanba_guides import staged_guide

        guide = staged_guide(ROOT)
        self.assertEqual((guide["region_code"], guide["district"]), ("610158", AREA["district"]))
        self.assertEqual(guide["authority"], "组织人事部")
        self.assertEqual(guide["fields"]["办理形式"], "窗口办理")
        self.assertEqual(guide["fields"]["到办事现场次数"], "1 次")
        self.assertEqual(guide["fields"]["是否收费"], "不收费")
        self.assertEqual(guide["role_sources"], {
            "劳动者": "https://zwfw.shaanxi.gov.cn/pc//#/c/service-guide?matterId=1118846332097&siteCode=610158000000",
            "用人单位": "https://zwfw.shaanxi.gov.cn/pc//#/c/service-guide?matterId=1114531332028&siteCode=610158000000",
        })
        self.assertEqual(guide["verification_status"], "conflict")
        self.assertEqual(guide["channel"]["online_status"], "unavailable")
        self.assertFalse(guide["channel"]["submission_verified"])
        materials = {(row["service_object"], row["official_name"]): row for row in guide["materials"]}
        self.assertEqual(len(materials), 7)
        self.assertEqual(materials["劳动者", "劳动人事争议仲裁申请书"]["copies"], "原件3 份")
        self.assertEqual(materials["用人单位", "劳动人事争议仲裁申请书"]["copies"], "原件1 份 复印件1 份")
        self.assertIn("按照被申请人个数提交副本", materials["劳动者", "劳动人事争议仲裁申请书"]["instructions"])
        self.assertEqual(materials["用人单位", "授权委托书"]["required"], "必要")
        self.assertNotIn(("劳动者", "授权委托书"), materials)
        self.assertTrue(all(row["region_code"] == "610158" for row in materials.values()))
        self.assertIn("周至县劳动人事争议仲裁院", guide["sections"]["官网附件核验"])
        self.assertIn("自然人", guide["sections"]["官网附件核验"])
        self.assertEqual(guide["templates"], [])
        self.assertFalse(guide["published"])
        self.assertFalse(guide["can_generate"])

    def test_own_guide_stays_inside_zone_and_exposes_no_form_contract(self):
        from regional_xian_chanba_guides import staged_guide

        root = Path(self.enterContext(TemporaryDirectory()))
        directory = DirectoryStore(root / "directory.sqlite")
        for row in json.loads((ROOT / "data/public-regions/directory.json").read_bytes()):
            if row["code"] in {"610100", "610111", "610154", "610155", "610158"}:
                directory.put_area(row)
        store = RegionalStore(root / "guides.sqlite")
        candidate = store.put_guide(staged_guide(ROOT))
        self.enterContext(patch.object(routes, "ROOT", root))
        self.enterContext(patch.object(routes, "store", return_value=store))
        self.enterContext(patch.object(routes, "directory_store", return_value=directory))
        app = FastAPI()
        app.include_router(routes.router, prefix="/regional")
        client = self.enterContext(TestClient(app))

        own = client.get("/regional/lookup", params=AREA).json()
        self.assertEqual(own["source_id"], candidate["source_id"])
        self.assertEqual(len(own["materials"]), 7)
        self.assertEqual(own["templates"], [])
        for district in ("", "市本级", "灞桥区", "浐灞生态区", "国际港务区"):
            with self.subTest(district=district):
                other = client.get("/regional/lookup", params={**CITY, "district": district}).json()
                self.assertIsNone(other["source_id"])
                self.assertEqual(other["templates"], [])
        params = {**AREA, "source_id": candidate["source_id"], "version": candidate["version"],
                  "kind": "application", "template_id": "xian-chanba-application"}
        self.assertEqual(client.get("/regional/form-contract", params=params).status_code, 409)
        self.assertEqual(client.post("/regional/generate", json={**params, "mode": "blank", "data": {}}).status_code, 409)

    def test_staging_requires_original_proof_bytes(self):
        from regional_xian_chanba_guides import SOURCE, staged_guide

        root = Path(self.enterContext(TemporaryDirectory()))
        target = root / SOURCE
        target.parent.mkdir(parents=True)
        with self.assertRaises(ValueError):
            staged_guide(root)
        target.write_bytes((ROOT / SOURCE).read_bytes())
        self.assertEqual(staged_guide(root)["region_code"], "610158")
        target.write_bytes(target.read_bytes() + b" ")
        with self.assertRaises(ValueError):
            staged_guide(root)
