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
CITY = {"province": "ningxia", "city": "石嘴山市"}
AREA = {**CITY, "district": "平罗县"}
NOTICE = "https://www.pingluo.gov.cn/xxgk/bmxxgk/plxrlzyhshbzj/fdzdgknr_69639/yjsgk_69647/bmys_69648/202602/t20260202_5156809.html"


class PingluReceptionTests(TestCase):
    def adapter(self):
        name = "regional_shizuishan_pinglu_reception"
        self.assertIsNotNone(importlib.util.find_spec(name), "平罗县立案室候选尚未接入")
        return importlib.import_module(name)

    def test_guide_records_only_the_county_reception_function(self):
        guide = self.adapter().staged_guide(ROOT)
        self.assertEqual((guide["region_code"], guide["district"], guide["scope_level"]), ("640221", "平罗县", "district"))
        self.assertEqual(guide["source_url"], NOTICE)
        self.assertEqual(guide["verification_status"], "partial")
        self.assertEqual(guide["authority"], "平罗县劳动人事争议仲裁院")
        self.assertIn("仲裁立案室负责接收、初步审查", guide["sections"]["立案室职责"])
        for field in ("办理地点", "咨询方式", "办理形式"):
            self.assertNotIn(field, guide["fields"])
        self.assertEqual(guide["channel"]["online_status"], "unverified")
        self.assertIsNone(guide["channel"]["entry_url"])
        self.assertFalse(guide["channel"]["submission_verified"])
        self.assertNotIn("role_sources", guide)
        self.assertEqual((guide["materials"], guide["templates"]), ([], []))
        self.assertFalse(guide["published"])
        self.assertFalse(guide["can_generate"])

    def test_lookup_never_inherits_to_other_scopes(self):
        guide = self.adapter().staged_guide(ROOT)
        root = Path(self.enterContext(TemporaryDirectory()))
        directory = DirectoryStore(root / "directory.sqlite")
        for row in json.loads((ROOT / "data/public-regions/directory.json").read_bytes()):
            if row["code"] in {"640200", "640202", "640205", "640221"}:
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
        self.assertEqual([item["district"] for item in items if item.get("source_id")], ["平罗县"])
        for district in ("", "市本级", "大武口区", "惠农区", "石嘴山高新区", "石嘴山经开区"):
            with self.subTest(district=district):
                other = client.get("/regional/lookup", params={**CITY, "district": district}).json()
                self.assertIsNone(other["source_id"])
                self.assertEqual((other["materials"], other["templates"]), ([], []))

    def test_missing_and_changed_proof_are_rejected(self):
        adapter = self.adapter()
        root = Path(self.enterContext(TemporaryDirectory()))
        with self.assertRaises(ValueError):
            adapter.staged_guide(root)
        proof = root / adapter.SOURCE
        proof.parent.mkdir(parents=True)
        proof.write_bytes((ROOT / adapter.SOURCE).read_bytes() + b" ")
        with self.assertRaises(ValueError):
            adapter.staged_guide(root)
