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
CITY = {"province": "shaanxi", "city": "西安市"}
DISTRICT = {**CITY, "district": "高新区管委会"}


class XianHighTechOwnGuideTests(TestCase):
    def test_preserves_local_guide_and_conditional_materials(self):
        from regional_xian_high_tech_guide import staged_guide

        guide = staged_guide(ROOT)
        self.assertEqual((guide["city"], guide["district"], guide["region_code"]),
                         ("西安市", "高新区管委会", "610152"))
        self.assertEqual(guide["authority"], "西安市劳动人事争议仲裁委员会高新派出庭")
        self.assertIn("都市之门A座1601室", guide["fields"]["办理地点"])
        self.assertEqual(guide["fields"]["咨询方式"], "029-88333687")
        self.assertEqual(guide["fields"]["收费标准"], "不收费")
        self.assertEqual(guide["role_sources"], {})
        self.assertEqual(guide["channel"]["online_status"], "unverified")
        materials = guide["materials"]
        self.assertEqual([row["id"].split("-", 1)[0] for row in materials], ["610152"] * 6)
        self.assertEqual(materials[0]["copies"], "被申请人人数 + 1")
        self.assertIn("身份证原件及复印件", materials[1]["instructions"])
        self.assertIn("法定代表人身份证明书", materials[1]["instructions"])
        self.assertIn("有委托代理人", materials[2]["required"])
        self.assertIn("被申请人为企业", materials[4]["required"])
        self.assertFalse(guide["published"])
        self.assertFalse(guide["can_generate"])
        self.assertEqual(guide["templates"], [])

    def test_local_candidate_has_no_download_or_inherited_scope(self):
        from regional_xian_high_tech_guide import staged_guide

        root = Path(self.enterContext(TemporaryDirectory()))
        directory = DirectoryStore(root / "directory.sqlite")
        for row in json.loads((ROOT / "data/public-regions/directory.json").read_bytes()):
            if row["code"] in {"610100", "610102", "610152"}:
                directory.put_area(row)
        store = RegionalStore(root / "guides.sqlite")
        guide = store.put_guide(staged_guide(ROOT))
        app = FastAPI()
        app.include_router(routes.router, prefix="/regional")
        from regional_xian_high_tech_guide import SOURCE
        (root / SOURCE).parent.mkdir(parents=True)
        (root / SOURCE).write_bytes((ROOT / SOURCE).read_bytes())
        self.enterContext(patch.object(routes, "ROOT", root))
        self.enterContext(patch.object(routes, "store", return_value=store))
        self.enterContext(patch.object(routes, "directory_store", return_value=directory))
        client = self.enterContext(TestClient(app))
        area = next(row for row in client.get("/regional/areas", params=CITY).json()["items"]
                    if row["district"] == DISTRICT["district"])
        self.assertEqual(area["source_id"], guide["source_id"])
        self.assertFalse(area["can_generate"])
        for district in ("", "市本级", "新城区", "经开区管委会", "高新区"):
            other = client.get("/regional/lookup", params={**CITY, "district": district}).json()
            self.assertIsNone(other["source_id"])
            self.assertEqual(other["templates"], [])
        result = client.get("/regional/lookup", params=DISTRICT).json()
        self.assertEqual(result["source_id"], guide["source_id"])
        self.assertEqual(len(result["materials"]), 6)
        self.assertEqual(result["templates"], [])
        params = {**DISTRICT, "source_id": guide["source_id"], "version": guide["version"],
                  "kind": "application", "template_id": "xian-high-tech-application"}
        self.assertEqual(client.get("/regional/form-contract", params=params).status_code, 409)
        self.assertEqual(client.post("/regional/generate", json={**params, "mode": "blank", "data": {}}).status_code, 409)

    def test_rejects_changed_source_proof(self):
        from regional_xian_high_tech_guide import SOURCE, staged_guide

        root = Path(self.enterContext(TemporaryDirectory()))
        with self.assertRaises(ValueError):
            staged_guide(root)
        target = root / SOURCE
        target.parent.mkdir(parents=True)
        proof = (ROOT / SOURCE).read_bytes()
        target.write_bytes(proof)
        self.assertEqual(staged_guide(root)["region_code"], "610152")
        target.write_bytes(proof + b" ")
        with self.assertRaises(ValueError):
            staged_guide(root)
