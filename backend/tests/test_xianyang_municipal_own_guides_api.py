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
CITY = {"province": "shaanxi", "city": "咸阳市"}
MUNICIPAL = {**CITY, "district": "市本级"}


class XianyangMunicipalOfficialGuidesTests(TestCase):
    def test_role_windows_and_source_links_are_preserved(self):
        from regional_xianyang_municipal_guides import staged_guide

        guide = staged_guide(ROOT)
        self.assertEqual((guide["district"], guide["scope_level"], guide["region_code"], guide["authority"]),
                         ("市本级", "municipal", "610400", "市人社局"))
        self.assertEqual(guide["verification_status"], "conflict")
        self.assertEqual(guide["channel"]["online_status"], "conflict")
        self.assertIsNone(guide["channel"]["entry_url"])
        self.assertIn("玉泉东路5号", guide["fields"]["办理地点"])
        self.assertEqual(guide["fields"]["咨询方式"], "029-33553971")
        self.assertEqual(len(guide["materials"]), 7)
        for role, matter, expected in (
            ("劳动者", "1117369317238", {"劳动人事争议仲裁申请书": "原件2 份", "身份证": "原件1 份 复印件2 份",
                                         "劳动（人事）关系证明材料": "原件1 份", "授权委托书": "原件1 份"}),
            ("用人单位", "1114139245895", {"劳动人事争议仲裁申请书": "原件2 份",
                                          "劳动（人事）关系证明材料": "原件1 份 复印件2 份", "授权委托书": "原件1 份"}),
        ):
            url = f"https://zwfw.shaanxi.gov.cn/pc//#/c/service-guide?matterId={matter}&siteCode=610400000000"
            self.assertEqual(guide["role_sources"][role], url)
            rows = [row for row in guide["materials"] if row["service_object"] == role]
            self.assertEqual({row["official_name"]: row["copies"] for row in rows}, expected)
            self.assertTrue(all(row["source_url"] == url and row["region_code"] == "610400" for row in rows))
        self.assertIn("网上办理、快递申请", guide["sections"]["办理渠道核验"])
        self.assertIn("窗口办理、网上办理", guide["sections"]["办理渠道核验"])
        self.assertEqual(guide["templates"], [])
        self.assertFalse(guide["published"])
        self.assertFalse(guide["can_generate"])

    def test_public_routes_expose_only_exact_municipal_candidate(self):
        from regional_xianyang_municipal_guides import staged_guide

        root = Path(self.enterContext(TemporaryDirectory()))
        directory = DirectoryStore(root / "areas.sqlite")
        for row in json.loads((ROOT / "data/public-regions/directory.json").read_bytes()):
            if row["code"] in {"610400", "610402", "610404"}:
                directory.put_area(row)
        store = RegionalStore(root / "guides.sqlite")
        app = FastAPI()
        app.include_router(routes.router, prefix="/regional")
        self.enterContext(patch.object(routes, "ROOT", ROOT))
        self.enterContext(patch.object(routes, "store", return_value=store))
        self.enterContext(patch.object(routes, "directory_store", return_value=directory))
        client = self.enterContext(TestClient(app))

        candidate = staged_guide(ROOT)
        store.put_guide({**candidate, "source_version": "0" * 64})
        areas = client.get("/regional/areas", params=CITY).json()["items"]
        self.assertNotIn("市本级", {area["district"] for area in areas})

        guide = store.put_guide(candidate)
        areas = client.get("/regional/areas", params=CITY).json()["items"]
        municipal = next(area for area in areas if area["district"] == "市本级")
        self.assertEqual(municipal["source_id"], guide["source_id"])
        self.assertFalse(municipal["can_generate"])
        lookup = client.get("/regional/lookup", params=MUNICIPAL).json()
        self.assertEqual(lookup["role_sources"], guide["role_sources"])
        self.assertEqual(lookup["templates"], [])
        for district in ("", "秦都区", "渭城区", "高新区"):
            result = client.get("/regional/lookup", params={**CITY, "district": district}).json()
            self.assertIsNone(result["source_id"])
            self.assertEqual(result["templates"], [])

        template_id = "xianyang-610400-worker-application-sample"
        params = {**MUNICIPAL, "source_id": guide["source_id"], "version": guide["version"],
                  "kind": "application", "template_id": template_id}
        self.assertEqual(client.get(f"/regional/templates/{template_id}", params=params).status_code, 404)
        self.assertIn(client.get("/regional/form-contract", params=params).status_code, (404, 409))
        for mode in ("blank", "reference_adaptation"):
            self.assertIn(client.post("/regional/generate", json={**params, "mode": mode, "data": {}}).status_code,
                          (404, 409))

    def test_missing_or_modified_own_proof_is_rejected(self):
        from regional_xianyang_municipal_guides import PROOF, staged_guide

        root = Path(self.enterContext(TemporaryDirectory()))
        with self.assertRaises(ValueError):
            staged_guide(root)
        (root / PROOF).parent.mkdir(parents=True)
        (root / PROOF).write_bytes((ROOT / PROOF).read_bytes() + b" ")
        with self.assertRaises(ValueError):
            staged_guide(root)
