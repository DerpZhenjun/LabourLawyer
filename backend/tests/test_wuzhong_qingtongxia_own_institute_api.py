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
AREA = {**CITY, "district": "青铜峡市"}
SOURCE_URL = "https://www.qtx.gov.cn/xxgk/jgzn/szfzcbm/rlzyhshbzj/zsjg_65648/202206/t20220616_3574622.html"


class QingtongxiaOwnInstituteTests(TestCase):
    def adapter(self):
        name = "regional_wuzhong_qingtongxia_own_institute"
        self.assertIsNotNone(importlib.util.find_spec(name), "青铜峡市仲裁院候选尚未接入")
        return importlib.import_module(name)

    def test_local_reception_scope_has_no_unverified_channel_or_filing_documents(self):
        guide = self.adapter().staged_guide(ROOT)
        self.assertEqual((guide["region_code"], guide["district"], guide["scope_level"]),
                         ("640381", "青铜峡市", "district"))
        self.assertEqual(guide["source_url"], SOURCE_URL)
        self.assertEqual(guide["authority"], "青铜峡市劳动人事争议仲裁院")
        self.assertEqual(guide["verification_status"], "partial")
        self.assertEqual(guide["fields"], {"机构名称": "青铜峡市劳动人事争议仲裁院"})
        self.assertIn("劳动人事争议案件的受理、调解和仲裁", guide["sections"]["仲裁院职责"])
        self.assertIn("具体立案地址、联系电话、网上提交入口、双方申请材料和空白表格仍待核验",
                      guide["sections"]["申请资料核验"])
        self.assertEqual(guide["channel"]["online_status"], "unverified")
        self.assertIsNone(guide["channel"]["entry_url"])
        self.assertFalse(guide["channel"]["submission_verified"])
        self.assertEqual((guide["materials"], guide["templates"]), ([], []))
        self.assertNotIn("role_sources", guide)
        self.assertNotIn("3068523", json.dumps(guide, ensure_ascii=False))
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
        self.assertEqual([item["district"] for item in items if item.get("source_id")], ["青铜峡市"])
        for district in ("", "市本级", "利通区", "红寺堡区", "盐池县", "同心县", "青铜峡工业园区"):
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
