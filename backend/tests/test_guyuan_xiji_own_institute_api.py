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
CITY = {"province": "ningxia", "city": "固原市"}
AREA = {**CITY, "district": "西吉县"}
SOURCE_URL = "https://www.nxxj.gov.cn/xxgk_13648/zfxxgkml/jgzn/xzfbm_66893/xjxrlzyshbzj/202608/t20260826_5323021.html"


class XijiOwnInstituteTests(TestCase):
    def adapter(self):
        name = "regional_guyuan_xiji_own_institute"
        self.assertIsNotNone(importlib.util.find_spec(name), "西吉县仲裁院候选尚未接入")
        return importlib.import_module(name)

    def test_institute_affiliation_leaves_filing_authority_and_channel_unverified(self):
        guide = self.adapter().staged_guide(ROOT)
        self.assertEqual((guide["region_code"], guide["district"], guide["scope_level"]),
                         ("640422", "西吉县", "district"))
        self.assertEqual(guide["source_url"], SOURCE_URL)
        self.assertEqual(guide["authority"], "")
        self.assertEqual(guide["verification_status"], "partial")
        self.assertEqual(guide["fields"], {"县人社局直属机构": "西吉县劳动人事争议仲裁院"})
        self.assertIn("西吉县劳动人事争议仲裁院为西吉县人力资源和社会保障局的直属机构",
                      guide["sections"]["机构归属"])
        self.assertIn("立案受理机关、地址、联系电话、网上提交入口、双方申请材料和空白表格仍待核验",
                      guide["sections"]["申请资料核验"])
        self.assertEqual(guide["channel"]["online_status"], "unverified")
        self.assertIsNone(guide["channel"]["entry_url"])
        self.assertFalse(guide["channel"]["submission_verified"])
        self.assertEqual((guide["materials"], guide["templates"]), ([], []))
        self.assertNotIn("role_sources", guide)
        self.assertNotIn("办理地点", guide["fields"])
        self.assertNotIn("咨询方式", guide["fields"])
        self.assertFalse(guide["published"])
        self.assertFalse(guide["can_generate"])

    def test_exact_county_profile_does_not_inherit_to_other_areas(self):
        guide = self.adapter().staged_guide(ROOT)
        root = Path(self.enterContext(TemporaryDirectory()))
        directory = DirectoryStore(root / "directory.sqlite")
        for row in json.loads((ROOT / "data/public-regions/directory.json").read_bytes()):
            if row["code"] in {"640400", "640402", "640422", "640423", "640424", "640425"}:
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
        self.assertEqual([item["district"] for item in items if item.get("source_id")], ["西吉县"])
        for district in ("", "市本级", "原州区", "隆德县", "泾源县", "彭阳县", "固原经济开发区"):
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
