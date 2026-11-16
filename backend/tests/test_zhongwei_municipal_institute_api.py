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
CITY = {"province": "ningxia", "city": "中卫市"}
SCOPE = {**CITY, "district": "市本级"}
NOTICE = "https://www.nxzw.gov.cn/zwgk/bmxxgkml/srlzyhshbzj/fdzdgknr_49501/gkxx_49502/zsdw_49505/202212/t20221203_3870615.html"


class ZhongweiMunicipalInstituteTests(TestCase):
    def adapter(self):
        name = "regional_zhongwei_municipal_institute"
        self.assertIsNotNone(importlib.util.find_spec(name), "中卫市本级仲裁候选尚未接入")
        return importlib.import_module(name)

    def test_own_institute_provides_reception_and_office_only(self):
        guide = self.adapter().staged_guide(ROOT)
        self.assertEqual((guide["region_code"], guide["district"], guide["scope_level"]),
                         ("640500", "市本级", "municipal"))
        self.assertEqual(guide["source_url"], NOTICE)
        self.assertEqual(guide["verification_status"], "partial")
        self.assertEqual(guide["authority"], "中卫市劳动人事争议仲裁院")
        self.assertEqual(guide["fields"], {
            "机构办公地址": "中卫市沙坡头区文昌镇文萃南路105号人社局大楼214、217办公室",
            "机构办公电话": "0955-7063912、0955-8598923",
        })
        self.assertIn("负责受理并初审劳动人事争议案件", guide["sections"]["受理职责"])
        self.assertIn("机构办公地址：" + guide["fields"]["机构办公地址"], guide["sections"]["机构办公信息"])
        self.assertIn("机构办公电话：" + guide["fields"]["机构办公电话"], guide["sections"]["机构办公信息"])
        self.assertNotIn("办理地点", guide["fields"])
        self.assertNotIn("咨询方式", guide["fields"])
        self.assertIn("专门立案窗口、网上提交入口、双方申请材料和空白表格仍待核验",
                      guide["sections"]["申请资料核验"])
        self.assertEqual(guide["channel"]["online_status"], "unverified")
        self.assertIsNone(guide["channel"]["entry_url"])
        self.assertFalse(guide["channel"]["submission_verified"])
        self.assertNotIn("role_sources", guide)
        self.assertEqual((guide["materials"], guide["templates"]), ([], []))
        self.assertFalse(guide["published"])
        self.assertFalse(guide["can_generate"])

    def test_area_options_require_exact_city_profile_and_do_not_inherit(self):
        guide = self.adapter().staged_guide(ROOT)
        root = Path(self.enterContext(TemporaryDirectory()))
        directory = DirectoryStore(root / "directory.sqlite")
        for row in json.loads((ROOT / "data/public-regions/directory.json").read_bytes()):
            if row["code"] in {"640500", "640502", "640521", "640522"}:
                directory.put_area(row)
        store = RegionalStore(root / "guides.sqlite")
        self.enterContext(patch.object(routes, "ROOT", root))
        self.enterContext(patch.object(routes, "store", return_value=store))
        self.enterContext(patch.object(routes, "directory_store", return_value=directory))
        app = FastAPI()
        app.include_router(routes.router, prefix="/regional")
        client = self.enterContext(TestClient(app))

        store.put_guide({**guide, "source_version": "0" * 64})
        stale_options = client.get("/regional/areas", params=CITY).json()["items"]
        self.assertNotIn("市本级", [item["district"] for item in stale_options])
        saved = store.put_guide(guide)
        options = client.get("/regional/areas", params=CITY).json()["items"]
        self.assertEqual([(r["district"], r["source_id"]) for r in options if r.get("source_id")],
                         [("市本级", saved["source_id"])])
        self.assertEqual(client.get("/regional/lookup", params=SCOPE).json(), saved)

        for district in ("", "沙坡头区", "中宁县", "海原县", "中卫工业园区"):
            with self.subTest(district=district):
                other = client.get("/regional/lookup", params={**CITY, "district": district}).json()
                self.assertIsNone(other["source_id"])
                self.assertEqual((other["materials"], other["templates"]), ([], []))

    def test_missing_and_altered_sources_are_rejected(self):
        adapter = self.adapter()
        root = Path(self.enterContext(TemporaryDirectory()))
        with self.assertRaises(ValueError):
            adapter.staged_guide(root)
        target = root / adapter.SOURCE
        target.parent.mkdir(parents=True)
        target.write_bytes((ROOT / adapter.SOURCE).read_bytes() + b" ")
        with self.assertRaises(ValueError):
            adapter.staged_guide(root)
