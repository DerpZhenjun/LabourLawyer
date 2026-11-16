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
AREA = {**CITY, "district": "大武口区"}
CHECKLIST = "https://www.dwk.gov.cn/ztzl/zxzt/rsjzyk_/202303/t20230307_3987464.html"
PROCEDURE = "https://www.dwk.gov.cn/ztzl/zxzt/rsjzyk_/202303/t20230307_3987373.html"


class DawukouOwnGuideTests(TestCase):
    def adapter(self):
        name = "regional_shizuishan_dawukou_guide"
        self.assertIsNotNone(importlib.util.find_spec(name), "大武口区地区候选尚未接入")
        return importlib.import_module(name)

    def test_district_guide_lists_the_written_office_route_and_worker_materials_only(self):
        guide = self.adapter().staged_guide(ROOT)
        self.assertEqual((guide["region_code"], guide["scope_level"]), ("640202", "district"))
        self.assertEqual(guide["source_url"], CHECKLIST)
        self.assertEqual(guide["verification_status"], "partial")
        self.assertEqual(guide["fields"]["办理地点"], "大武口区劳动人事争议仲裁院办公室")
        self.assertEqual(guide["fields"]["办理形式"], "线下书面申请")
        self.assertNotIn("咨询方式", guide["fields"])
        self.assertEqual(guide["channel"]["online_status"], "unverified")
        self.assertIsNone(guide["channel"]["entry_url"])
        self.assertFalse(guide["channel"]["submission_verified"])
        self.assertEqual(guide["role_sources"], {"劳动者": PROCEDURE})
        self.assertEqual([material["official_name"] for material in guide["materials"]], [
            "劳动仲裁申请书", "本人身份证复印件", "劳动关系证据", "被申请人登记注册信息",
        ])
        self.assertTrue(all(
            row["service_object"] == "劳动者" and row["source_url"] == PROCEDURE
            for row in guide["materials"]
        ))
        self.assertEqual(guide["materials"][0]["copies"], "")
        self.assertIn("用人单位材料仍待核验", guide["sections"]["资料核验"])
        self.assertEqual(guide["templates"], [])
        self.assertFalse(guide["can_generate"])
        self.assertFalse(guide["published"])

    def test_candidate_isolated_to_the_district_and_no_document_contract(self):
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

        localities = client.get("/regional/areas", params=CITY).json()["items"]
        self.assertEqual([item["district"] for item in localities if item.get("source_id")], ["大武口区"])
        self.assertEqual(client.get("/regional/lookup", params=AREA).json(), saved)
        for district in ("", "市本级", "惠农区", "平罗县", "石嘴山高新区", "石嘴山经开区"):
            with self.subTest(district=district):
                other = client.get("/regional/lookup", params={**CITY, "district": district}).json()
                self.assertIsNone(other["source_id"])
                self.assertEqual((other["materials"], other["templates"]), ([], []))
        params = {**AREA, "source_id": saved["source_id"], "version": saved["version"],
                  "kind": "application", "template_id": "dawukou-worker-application"}
        self.assertEqual(client.get("/regional/form-contract", params=params).status_code, 409)
        self.assertEqual(client.post("/regional/generate", json={**params, "mode": "blank", "data": {}}).status_code, 409)

    def test_candidate_rejects_a_missing_or_modified_source_proof(self):
        adapter = self.adapter()
        root = Path(self.enterContext(TemporaryDirectory()))
        with self.assertRaises(ValueError):
            adapter.staged_guide(root)
        path = root / adapter.SOURCE
        path.parent.mkdir(parents=True)
        original = (ROOT / adapter.SOURCE).read_bytes()
        path.write_bytes(original)
        self.assertEqual(adapter.staged_guide(root)["district"], "大武口区")
        path.write_bytes(original + b" ")
        with self.assertRaises(ValueError):
            adapter.staged_guide(root)
