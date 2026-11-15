from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from regional_guides import RegionalStore
from routes import regional_guides as routes


ROOT = Path(__file__).resolve().parents[2]


class ZhenpingOfficialGuidesTests(TestCase):
    def test_preserves_role_material_origin_and_application_mismatch(self):
        from regional_zhenping_guides import staged_guide

        guide = staged_guide(ROOT)
        self.assertEqual((guide["city"], guide["district"], guide["region_code"]), ("安康市", "镇坪县", "610927"))
        self.assertIn("劳动者事项：1 个工作日", guide["fields"]["承诺办结时限"])
        self.assertIn("用人单位事项：3 个工作日", guide["fields"]["承诺办结时限"])
        self.assertEqual([row["service_object"] for row in guide["materials"]], ["劳动者"] * 4 + ["用人单位"] * 4)
        self.assertEqual([row["required"] for row in guide["materials"]], ["必要", "必要", "非必要", "必要"] + ["必要"] * 4)
        self.assertIn("劳动者申请仲裁确认劳动关系需准备的材料", guide["materials"][0]["instructions"])
        self.assertIn("被申请人", guide["materials"][4]["instructions"])
        self.assertIn("逐字节相同", guide["sections"]["官网附件核验"])
        self.assertFalse(guide["can_generate"])
        self.assertFalse(guide["published"])
        templates = guide["templates"]
        self.assertEqual(len(templates), 4)
        self.assertFalse(any("身份证" in row["original_name"] or "关系证明" in row["original_name"] for row in templates))
        self.assertEqual([t["service_object"] for t in templates], ["劳动者", "用人单位", "用人单位", "用人单位"])
        self.assertTrue(all(t["official_kind"] == "sample" and t["download_status"] == "official_link_only"
                            and t["official_attachment_entry"] == "material_tab" and "file" not in t for t in templates))
        employer_application = templates[1]
        self.assertIn("申请书提纲", employer_application["original_name"])
        self.assertEqual(employer_application["original_format"], "DOC")

    def test_api_never_promotes_guidance_or_samples_to_templates(self):
        from regional_zhenping_guides import staged_guide

        directory = self.enterContext(TemporaryDirectory())
        store = RegionalStore(Path(directory) / "guides.sqlite")
        guide = store.put_guide(staged_guide(ROOT))
        app = FastAPI()
        app.include_router(routes.router, prefix="/regional")
        self.enterContext(patch.object(routes, "ROOT", ROOT))
        self.enterContext(patch.object(routes, "store", return_value=store))
        client = self.enterContext(TestClient(app))
        bound = {key: guide[key] for key in ("province", "city", "district", "source_id", "version")}
        probes = [t["id"] for t in guide["templates"]] + ["ankang-610927-worker-application-sample"]
        for template_id in probes:
            self.assertEqual(client.get(f"/regional/templates/{template_id}", params=bound).status_code, 404)
            params = {**bound, "template_id": template_id, "kind": "application"}
            self.assertIn(client.get("/regional/form-contract", params=params).status_code, (404, 409))
            for mode in ("blank", "reference_adaptation"):
                self.assertIn(client.post("/regional/generate", json={**params, "mode": mode, "data": {}}).status_code, (404, 409))
        other = client.get("/regional/lookup", params={"province": "shaanxi", "city": "安康市", "district": "白河县"})
        self.assertEqual(other.status_code, 200, other.text)
        self.assertEqual(other.json()["templates"], [])

    def test_review_proof_is_byte_pinned(self):
        from regional_zhenping_guides import PROOF, staged_guide

        directory = Path(self.enterContext(TemporaryDirectory()))
        (directory / PROOF).parent.mkdir(parents=True)
        (directory / PROOF).write_bytes((ROOT / PROOF).read_bytes() + b"\n")
        with self.assertRaises(ValueError):
            staged_guide(directory)
