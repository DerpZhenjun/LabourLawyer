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
CITY = {"province": "shaanxi", "city": "榆林市"}
MUNICIPAL = {**CITY, "district": "市本级"}


class YulinMunicipalOfficialGuidesTests(TestCase):
    def test_role_windows_and_source_links_are_preserved(self):
        from regional_yulin_municipal_guides import staged_guide

        guide = staged_guide(ROOT)
        self.assertEqual((guide["district"], guide["scope_level"], guide["region_code"], guide["authority"]),
                         ("市本级", "municipal", "610800", "榆林市人社局"))
        self.assertEqual(guide["fields"]["承诺办结时限"], "0 个工作日")
        self.assertIn("劳动保障大厦2楼205室", guide["fields"]["办理地点"])
        self.assertIn("明珠大道辅路", guide["fields"]["办理地点"])
        self.assertIn("0912-3859555", guide["fields"]["咨询方式"])
        self.assertEqual(len(guide["materials"]), 6)
        for role, matter, expected_names in (
            ("劳动者", "1114310220443", ["身份证", "劳动人事争议仲裁申请书", "授权委托书"]),
            ("用人单位", "1115339238904", ["劳动人事争议仲裁申请书", "授权委托书", "主体资格证明材料"]),
        ):
            source = f"https://zwfw.shaanxi.gov.cn/pc//#/c/service-guide?matterId={matter}&siteCode=610800000000"
            rows = [row for row in guide["materials"] if row["service_object"] == role]
            self.assertEqual([row["official_name"] for row in rows], expected_names)
            self.assertEqual({(row["region_code"], row["source_url"], row["required"]) for row in rows},
                             {("610800", source, "必要")})
            self.assertEqual(guide["role_sources"][role], source)
            quantities = {row["official_name"]: (row["original_copy"], row["format"], row["copies"]) for row in rows}
            self.assertEqual(quantities["劳动人事争议仲裁申请书"], ("原件", "纸质材料", 3))
            self.assertEqual(quantities["授权委托书"], ("原件", "纸质材料", 1))
            if role == "劳动者":
                self.assertEqual(quantities["身份证"], ("复印件", "纸质材料", 1))
            else:
                self.assertEqual(quantities["主体资格证明材料"], ("原件", "纸质材料", 1))
        self.assertIn("样表", guide["sections"]["官网附件核验"])
        self.assertEqual(guide["templates"], [])
        self.assertFalse(guide["published"])
        self.assertFalse(guide["can_generate"])

    def test_public_routes_expose_only_exact_municipal_candidate(self):
        from regional_yulin_municipal_guides import staged_guide

        root = Path(self.enterContext(TemporaryDirectory()))
        directory = DirectoryStore(root / "areas.sqlite")
        for row in json.loads((ROOT / "data/public-regions/directory.json").read_bytes()):
            if row["code"] in {"610800", "610802", "610803"}:
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
        for district in ("", "榆阳区", "横山区", "高新区"):
            result = client.get("/regional/lookup", params={**CITY, "district": district}).json()
            self.assertIsNone(result["source_id"])
            self.assertEqual(result["templates"], [])

        template_id = "yulin-610800-worker-application-sample"
        params = {**MUNICIPAL, "source_id": guide["source_id"], "version": guide["version"],
                  "kind": "application", "template_id": template_id}
        self.assertEqual(client.get(f"/regional/templates/{template_id}", params=params).status_code, 404)
        self.assertIn(client.get("/regional/form-contract", params=params).status_code, (404, 409))
        for mode in ("blank", "reference_adaptation"):
            self.assertIn(client.post("/regional/generate", json={**params, "mode": mode, "data": {}}).status_code,
                          (404, 409))

    def test_missing_or_modified_own_proof_is_rejected(self):
        from regional_yulin_municipal_guides import PROOF, staged_guide

        root = Path(self.enterContext(TemporaryDirectory()))
        with self.assertRaises(ValueError):
            staged_guide(root)
        (root / PROOF).parent.mkdir(parents=True)
        (root / PROOF).write_bytes((ROOT / PROOF).read_bytes() + b" ")
        with self.assertRaises(ValueError):
            staged_guide(root)
