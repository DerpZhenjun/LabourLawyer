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
CITY = {"province": "shaanxi", "city": "杨凌示范区"}
MUNICIPAL = {**CITY, "district": "市本级"}
DISTRICT = {**CITY, "district": "杨陵区"}
WORKER = "https://zwfw.shaanxi.gov.cn/pc//#/c/service-guide?matterId=1111818134236&siteCode=611100000000"
EMPLOYER = "https://zwfw.shaanxi.gov.cn/pc//#/c/service-guide?matterId=1114008126299&siteCode=611100000000"
RELOCATION = "https://www.ylq.gov.cn/zfxxgk/fdzdgknr/tzgg/2120407598296608770.html"


class YanglingOwnGuideTests(TestCase):
    def test_municipal_role_sources_and_attachments(self):
        from regional_yangling_guides import staged_municipal_guide

        guide = staged_municipal_guide(ROOT)
        self.assertEqual((guide["region_code"], guide["scope_level"], guide["district"]),
                         ("611100", "municipal", "市本级"))
        self.assertEqual(guide["role_sources"], {"劳动者": WORKER, "用人单位": EMPLOYER})
        self.assertIn("政务大厦502室", guide["fields"]["办理地点"])
        self.assertIn("新桥路6号", guide["fields"]["办理地点"])
        self.assertNotIn("C203", guide["fields"]["办理地点"])
        self.assertEqual(guide["fields"]["咨询方式"], "029-87033786")
        self.assertEqual(guide["channel"]["online_status"], "unavailable")
        self.assertIsNone(guide["channel"]["entry_url"])
        self.assertFalse(guide["channel"]["submission_verified"])
        self.assertIn("自然人填写示例", guide["sections"]["官网附件核验"])
        rows = guide["materials"]
        self.assertEqual(len(rows), 7)
        self.assertEqual((rows[0]["copies"], rows[0]["source_url"]), ("原件2份", WORKER))
        self.assertEqual((rows[4]["copies"], rows[4]["source_url"]), ("原件1份 复印件2份", EMPLOYER))
        self.assertEqual((rows[6]["official_name"], rows[6]["required"]), ("授权委托书", "非必要"))
        self.assertEqual(guide["templates"], [])
        self.assertFalse(guide["can_generate"])

    def test_district_uses_its_new_address_and_keeps_materials_unverified(self):
        from regional_yangling_guides import staged_district_notice

        guide = staged_district_notice(ROOT)
        self.assertEqual((guide["region_code"], guide["district"], guide["verification_status"]),
                         ("611101", "杨陵区", "partial"))
        self.assertEqual(guide["source_url"], RELOCATION)
        self.assertIn("综治中心C203室", guide["fields"]["办理地点"])
        self.assertEqual(guide["fields"]["咨询方式"], "029-87013966")
        self.assertIn("2026年11月12日", guide["sections"]["搬迁公告"])
        self.assertIn("原人力资源市场3楼", guide["sections"]["搬迁公告"])
        self.assertEqual(guide.get("role_sources", {}), {})
        self.assertEqual((guide["materials"], guide["templates"]), ([], []))
        self.assertFalse(guide["can_generate"])

    def test_directory_exposes_only_scoped_verified_records(self):
        from regional_yangling_guides import staged_district_notice, staged_municipal_guide

        root = Path(self.enterContext(TemporaryDirectory()))
        directory = DirectoryStore(root / "directory.sqlite")
        for area in json.loads((ROOT / "data/public-regions/directory.json").read_bytes()):
            if area["code"] in {"611100", "611101"}:
                directory.put_area(area)
        store = RegionalStore(root / "guides.sqlite")
        self.enterContext(patch.object(routes, "ROOT", root))
        self.enterContext(patch.object(routes, "store", return_value=store))
        self.enterContext(patch.object(routes, "directory_store", return_value=directory))
        app = FastAPI()
        app.include_router(routes.router, prefix="/regional")
        client = self.enterContext(TestClient(app))
        municipal = staged_municipal_guide(ROOT)
        store.put_guide({**municipal, "source_version": "0" * 64})
        self.assertNotIn("市本级", {r["district"] for r in client.get("/regional/areas", params=CITY).json()["items"]})
        city = store.put_guide(municipal)
        district = store.put_guide(staged_district_notice(ROOT))
        actual = {r["district"]: r["source_id"] for r in client.get("/regional/areas", params=CITY).json()["items"]}
        self.assertEqual(actual, {"市本级": city["source_id"], "杨陵区": district["source_id"]})
        self.assertEqual(client.get("/regional/lookup", params=MUNICIPAL).json(), city)
        self.assertEqual(client.get("/regional/lookup", params=DISTRICT).json(), district)
        for scope in ({**CITY, "district": ""}, {**DISTRICT, "city": "咸阳市"}):
            self.assertIsNone(client.get("/regional/lookup", params=scope).json()["source_id"])

    def test_rejects_changed_or_absent_proof(self):
        from regional_yangling_guides import DISTRICT_SOURCE, MUNICIPAL_SOURCE, staged_district_notice, staged_municipal_guide

        for proof, adapter in ((MUNICIPAL_SOURCE, staged_municipal_guide), (DISTRICT_SOURCE, staged_district_notice)):
            with self.subTest(proof=proof):
                root = Path(self.enterContext(TemporaryDirectory()))
                with self.assertRaises(ValueError):
                    adapter(root)
                target = root / proof
                target.parent.mkdir(parents=True)
                target.write_bytes((ROOT / proof).read_bytes() + b" ")
                with self.assertRaises(ValueError):
                    adapter(root)
