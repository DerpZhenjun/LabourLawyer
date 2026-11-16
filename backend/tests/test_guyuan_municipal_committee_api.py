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
SCOPE = {**CITY, "district": "市本级"}
NOTICE = "https://www.nxgy.gov.cn/zwgk/zcwj/qtwj/jgzn_35170/202509/t20250928_5041105.html"


class GuyuanMunicipalCommitteeTests(TestCase):
    def adapter(self):
        name = "regional_guyuan_municipal_committee"
        self.assertIsNotNone(importlib.util.find_spec(name), "固原市本级仲裁候选尚未接入")
        return importlib.import_module(name)

    def test_own_notice_provides_committee_and_office_only(self):
        guide = self.adapter().staged_guide(ROOT)
        self.assertEqual((guide["region_code"], guide["district"], guide["scope_level"]),
                         ("640400", "市本级", "municipal"))
        self.assertEqual(guide["source_url"], NOTICE)
        self.assertEqual(guide["verification_status"], "partial")
        self.assertEqual(guide["authority"], "固原市劳动人事争议仲裁委员会")
        self.assertEqual(guide["fields"], {
            "仲裁委员会": "固原市劳动人事争议仲裁委员会",
            "办事机构": "固原市劳动人事争议仲裁院",
        })
        self.assertIn("受理管辖范围内的劳动人事争议案件", guide["sections"]["受理职责"])
        self.assertIn("立案地址、联系电话、网上提交入口、双方申请材料和空白表格仍待核验",
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
            if row["code"] in {"640400", "640402", "640422", "640423", "640424", "640425"}:
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

        for district in ("", "原州区", "西吉县", "隆德县", "泾源县", "彭阳县", "固原经济开发区"):
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
