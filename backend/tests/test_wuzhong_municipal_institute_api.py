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
SCOPE = {"province": "ningxia", "city": "吴忠市", "district": "市本级"}
ANNOUNCEMENT = "https://www.wuzhong.gov.cn/xxgk/jgzn/szfzcbm/rlzyhshbzj_42775/zsjg_42780/wzsldrszyzcy/jbxx_55710/"


class WuzhongMunicipalInstituteTests(TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec("regional_wuzhong_municipal_institute"),
                             "吴忠市本级办公信息候选尚未接入")

    def test_candidate_preserves_the_city_venue_and_unknown_application_requirements(self):
        from regional_wuzhong_municipal_institute import staged_guide

        guide = staged_guide(ROOT)
        self.assertEqual((guide["region_code"], guide["district"], guide["scope_level"]), ("640300", "市本级", "municipal"))
        self.assertEqual(guide["verification_status"], "partial")
        self.assertEqual(guide["source_url"], ANNOUNCEMENT)
        self.assertIn("开元大道544号", guide["fields"]["机构办公地址"])
        self.assertEqual(guide["fields"]["机构办公电话"], "0953-2272186")
        self.assertNotIn("办理地点", guide["fields"])
        self.assertIn("夏季", guide["fields"]["机构办公时间"])
        self.assertNotIn("咨询方式", guide["fields"])
        self.assertEqual(guide["channel"]["online_status"], "unverified")
        self.assertFalse(guide["channel"]["submission_verified"])
        self.assertNotIn("role_sources", guide)
        self.assertEqual((guide["materials"], guide["templates"]), ([], []))
        self.assertFalse(guide["published"])
        self.assertFalse(guide["can_generate"])

    def test_only_the_verified_explicit_city_option_exposes_the_notice(self):
        from regional_wuzhong_municipal_institute import staged_guide

        root = Path(self.enterContext(TemporaryDirectory()))
        directory = DirectoryStore(root / "directory.sqlite")
        for area in json.loads((ROOT / "data/public-regions/directory.json").read_bytes()):
            if area["code"] in {"640300", "640302", "640303", "640323", "640324", "640381"}:
                directory.put_area(area)
        store = RegionalStore(root / "guides.sqlite")
        self.enterContext(patch.object(routes, "ROOT", root))
        self.enterContext(patch.object(routes, "store", return_value=store))
        self.enterContext(patch.object(routes, "directory_store", return_value=directory))
        app = FastAPI()
        app.include_router(routes.router, prefix="/regional")
        client = self.enterContext(TestClient(app))
        guide = staged_guide(ROOT)
        params = {k: v for k, v in SCOPE.items() if k != "district"}
        store.put_guide({**guide, "source_version": "0" * 64})
        self.assertNotIn("市本级", {r["district"] for r in client.get("/regional/areas", params=params).json()["items"]})
        published_fixture = store.put_guide(guide)
        localities = client.get("/regional/areas", params=params).json()["items"]
        self.assertEqual(localities[0]["district"], "市本级")
        self.assertEqual(localities[0]["source_id"], published_fixture["source_id"])
        self.assertEqual(client.get("/regional/lookup", params=SCOPE).json(), published_fixture)
        for district in ("", "利通区", "红寺堡区", "盐池县", "同心县", "青铜峡市"):
            with self.subTest(district=district):
                data = client.get("/regional/lookup", params={**SCOPE, "district": district}).json()
                self.assertIsNone(data["source_id"])
                self.assertEqual((data["materials"], data["templates"]), ([], []))

    def test_missing_and_changed_proof_are_rejected(self):
        from regional_wuzhong_municipal_institute import SOURCE, staged_guide

        root = Path(self.enterContext(TemporaryDirectory()))
        with self.assertRaises(ValueError):
            staged_guide(root)
        proof = root / SOURCE
        proof.parent.mkdir(parents=True)
        proof.write_bytes((ROOT / SOURCE).read_bytes() + b" ")
        with self.assertRaises(ValueError):
            staged_guide(root)
