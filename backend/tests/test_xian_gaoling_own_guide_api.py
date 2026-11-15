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
AREA = {**CITY, "district": "高陵区"}
EMPLOYER_SOURCE = "https://zwfw.xa.gov.cn/gaoling/bmbs/abmfl/glqrsj7aa4/1570501207263301634.html"


class XianGaolingOwnGuideTests(TestCase):
    def test_employer_only_guide_preserves_exemption_and_attachment_conflict(self):
        from regional_xian_gaoling_guide import staged_guide

        guide = staged_guide(ROOT)
        self.assertEqual((guide["region_code"], guide["district"]), ("610117", "高陵区"))
        self.assertEqual(guide["role_sources"], {"用人单位": EMPLOYER_SOURCE})
        self.assertEqual(guide["fields"]["办理形式"], "窗口办理")
        self.assertEqual(guide["channel"]["online_status"], "unverified")
        self.assertEqual(guide["verification_status"], "conflict")
        rows = guide["materials"]
        self.assertEqual([row["official_name"] for row in rows], [
            "劳动人事争议仲裁申请书", "营业执照", "劳动合同", "授权委托书",
        ])
        self.assertTrue(all(row["service_object"] == "用人单位" and row["source_url"] == EMPLOYER_SOURCE for row in rows))
        self.assertEqual(rows[0]["copies"], "原件1份、复印件1份")
        self.assertEqual(rows[1]["required"], "必要，符合官网条件可免提交")
        self.assertIn("已有电子证照/共享数据", rows[1]["instructions"])
        self.assertEqual(rows[3]["copies"], "原件1份")
        self.assertIn("周至县劳动人事争议仲裁院", guide["sections"]["官网附件核验"])
        self.assertEqual(guide["templates"], [])
        self.assertFalse(guide["published"])
        self.assertFalse(guide["can_generate"])

    def test_no_neighbor_source_and_no_download_or_generation_contract(self):
        from regional_xian_gaoling_guide import staged_guide

        root = Path(self.enterContext(TemporaryDirectory()))
        directory = DirectoryStore(root / "directory.sqlite")
        for area in json.loads((ROOT / "data/public-regions/directory.json").read_bytes()):
            if area["code"] in {"610100", "610116", "610117", "610118", "610158"}:
                directory.put_area(area)
        store = RegionalStore(root / "guides.sqlite")
        item = store.put_guide(staged_guide(ROOT))
        self.enterContext(patch.object(routes, "ROOT", root))
        self.enterContext(patch.object(routes, "store", return_value=store))
        self.enterContext(patch.object(routes, "directory_store", return_value=directory))
        app = FastAPI()
        app.include_router(routes.router, prefix="/regional")
        client = self.enterContext(TestClient(app))

        own = client.get("/regional/lookup", params=AREA).json()
        self.assertEqual(own["role_sources"], {"用人单位": EMPLOYER_SOURCE})
        self.assertEqual(len(own["materials"]), 4)
        self.assertEqual(own["templates"], [])
        for district in ("", "市本级", "长安区", "鄠邑区", "西安浐灞国际港"):
            with self.subTest(district=district):
                other = client.get("/regional/lookup", params={**CITY, "district": district}).json()
                self.assertIsNone(other["source_id"])
                self.assertEqual(other["templates"], [])
        params = {**AREA, "source_id": item["source_id"], "version": item["version"],
                  "kind": "application", "template_id": "xian-gaoling-employer-application"}
        self.assertEqual(client.get("/regional/form-contract", params=params).status_code, 409)
        self.assertEqual(client.post("/regional/generate", json={**params, "mode": "blank", "data": {}}).status_code, 409)

    def test_closed_when_proof_bytes_change(self):
        from regional_xian_gaoling_guide import SOURCE, staged_guide

        root = Path(self.enterContext(TemporaryDirectory()))
        target = root / SOURCE
        target.parent.mkdir(parents=True)
        with self.assertRaises(ValueError):
            staged_guide(root)
        original = (ROOT / SOURCE).read_bytes()
        target.write_bytes(original)
        self.assertEqual(staged_guide(root)["district"], "高陵区")
        target.write_bytes(original + b" ")
        with self.assertRaises(ValueError):
            staged_guide(root)
