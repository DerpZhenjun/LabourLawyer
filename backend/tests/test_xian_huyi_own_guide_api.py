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
AREA = {**CITY, "district": "鄠邑区"}
WORKER_SOURCE = "https://zwfw.xa.gov.cn/huyi/bmbs/abmfl/hyqrsj14e6/1570511497392656386.html"


class XianHuyiOwnGuideTests(TestCase):
    def test_worker_only_guide_preserves_copies_and_receiving_authority_conflict(self):
        from regional_xian_huyi_guide import staged_guide

        guide = staged_guide(ROOT)
        self.assertEqual((guide["region_code"], guide["district"]), ("610118", "鄠邑区"))
        self.assertEqual(guide["role_sources"], {"劳动者": WORKER_SOURCE})
        self.assertEqual(guide["fields"]["办理形式"], "窗口办理")
        self.assertEqual(guide["channel"]["online_status"], "unverified")
        self.assertEqual(guide["verification_status"], "conflict")
        rows = guide["materials"]
        self.assertEqual([row["official_name"] for row in rows], [
            "劳动人事争议仲裁申请书", "劳动合同", "身份证",
        ])
        self.assertTrue(all(row["service_object"] == "劳动者" and row["source_url"] == WORKER_SOURCE for row in rows))
        self.assertEqual(rows[0]["copies"], "原件3份")
        self.assertEqual(rows[1]["copies"], "原件1份、复印件1份")
        self.assertIn("证据材料清单", rows[1]["instructions"])
        self.assertEqual(rows[2]["copies"], "原件1份、复印件1份")
        self.assertIn("西安市劳动人事争议仲裁委员会", guide["sections"]["官网附件核验"])
        self.assertIn("周至县劳动人事争议仲裁委", guide["sections"]["办理机关核验"])
        self.assertEqual(guide["templates"], [])
        self.assertFalse(guide["published"])
        self.assertFalse(guide["can_generate"])

    def test_no_neighbor_source_and_no_download_or_generation_contract(self):
        from regional_xian_huyi_guide import staged_guide

        root = Path(self.enterContext(TemporaryDirectory()))
        directory = DirectoryStore(root / "directory.sqlite")
        for area in json.loads((ROOT / "data/public-regions/directory.json").read_bytes()):
            if area["code"] in {"610100", "610117", "610118", "610124", "610158"}:
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
        self.assertEqual(own["role_sources"], {"劳动者": WORKER_SOURCE})
        self.assertEqual(len(own["materials"]), 3)
        self.assertEqual(own["templates"], [])
        for district in ("", "市本级", "高陵区", "周至县", "西安浐灞国际港"):
            with self.subTest(district=district):
                other = client.get("/regional/lookup", params={**CITY, "district": district}).json()
                self.assertIsNone(other["source_id"])
                self.assertEqual(other["templates"], [])
        params = {**AREA, "source_id": item["source_id"], "version": item["version"],
                  "kind": "application", "template_id": "xian-huyi-worker-application"}
        self.assertEqual(client.get("/regional/form-contract", params=params).status_code, 409)
        self.assertEqual(client.post("/regional/generate", json={**params, "mode": "blank", "data": {}}).status_code, 409)

    def test_closed_when_proof_bytes_change(self):
        from regional_xian_huyi_guide import SOURCE, staged_guide

        root = Path(self.enterContext(TemporaryDirectory()))
        target = root / SOURCE
        target.parent.mkdir(parents=True)
        with self.assertRaises(ValueError):
            staged_guide(root)
        original = (ROOT / SOURCE).read_bytes()
        target.write_bytes(original)
        self.assertEqual(staged_guide(root)["district"], "鄠邑区")
        target.write_bytes(original + b" ")
        with self.assertRaises(ValueError):
            staged_guide(root)
