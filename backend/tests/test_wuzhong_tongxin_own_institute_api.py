import importlib
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
CITY = {"province": "ningxia", "city": "吴忠市"}
AREA = {**CITY, "district": "同心县"}
SOURCE_URL = (
    "https://www.tongxin.gov.cn/zwgk/jigouzhineng/xzfzcbm/rlzyhshbzj/"
    "zsjg_43604/202111/t20211125_3154178.html"
)


class TongxinOwnInstituteTests(TestCase):
    def adapter(self):
        name = "regional_wuzhong_tongxin_own_institute"
        self.assertIsNotNone(importlib.util.find_spec(name), "同心县仲裁院候选尚未接入")
        return importlib.import_module(name)

    def test_office_information_remains_distinct_from_filing_information(self):
        guide = self.adapter().staged_guide(ROOT)
        self.assertEqual((guide["region_code"], guide["district"], guide["scope_level"]),
                         ("640324", "同心县", "district"))
        self.assertEqual(guide["source_url"], SOURCE_URL)
        self.assertEqual(guide["authority"], "同心县劳动人事争议仲裁院")
        self.assertEqual(guide["verification_status"], "partial")
        self.assertEqual(guide["fields"], {
            "机构办公地址": "同心县新区罗山路5号人力资源和社会保障局大楼一楼",
            "机构办公电话/传真": "0953-8030350",
        })
        self.assertIn("县仲裁委员会管辖", guide["sections"]["仲裁院职责"])
        self.assertIn("专门立案窗口、网上提交入口、双方申请材料和空白表格仍待核验",
                      guide["sections"]["申请资料核验"])
        self.assertEqual(guide["channel"]["online_status"], "unverified")
        self.assertIsNone(guide["channel"]["entry_url"])
        self.assertFalse(guide["channel"]["submission_verified"])
        self.assertEqual((guide["materials"], guide["templates"]), ([], []))
        self.assertNotIn("role_sources", guide)
        self.assertNotIn("四楼", json.dumps(guide, ensure_ascii=False))
        self.assertNotIn("8022379", json.dumps(guide, ensure_ascii=False))
        self.assertFalse(guide["published"])
        self.assertFalse(guide["can_generate"])

    def test_exact_county_profile_does_not_inherit_to_other_areas(self):
        guide = self.adapter().staged_guide(ROOT)
        root = Path(self.enterContext(TemporaryDirectory()))
        directory = DirectoryStore(root / "directory.sqlite")
        for row in json.loads((ROOT / "data/public-regions/directory.json").read_bytes()):
            if row["code"] in {"640300", "640302", "640303", "640323", "640324", "640381"}:
                directory.put_area(row)
        store = RegionalStore(root / "guides.sqlite")
        saved = store.put_guide(guide)
        self.enterContext(patch.object(routes, "ROOT", root))
        self.enterContext(patch.object(routes, "store", return_value=store))
        self.enterContext(patch.object(routes, "directory_store", return_value=directory))
        app = FastAPI()
        app.include_router(routes.router, prefix="/regional")
        client = self.enterContext(TestClient(app))

        self.assertEqual(client.get("/regional/lookup", params=AREA).json(), saved)
        items = client.get("/regional/areas", params=CITY).json()["items"]
        self.assertEqual([item["district"] for item in items if item.get("source_id")], ["同心县"])
        for district in ("", "市本级", "利通区", "红寺堡区", "盐池县", "青铜峡市", "同心工业园区"):
            with self.subTest(district=district):
                other = client.get("/regional/lookup", params={**CITY, "district": district}).json()
                self.assertIsNone(other["source_id"])
                self.assertEqual((other["materials"], other["templates"]), ([], []))

    def test_missing_or_altered_evidence_is_rejected(self):
        adapter = self.adapter()
        root = Path(self.enterContext(TemporaryDirectory()))
        with self.assertRaises(ValueError):
            adapter.staged_guide(root)
        proof = root / adapter.SOURCE
        proof.parent.mkdir(parents=True)
        proof.write_bytes((ROOT / adapter.SOURCE).read_bytes() + b" ")
        with self.assertRaises(ValueError):
            adapter.staged_guide(root)
