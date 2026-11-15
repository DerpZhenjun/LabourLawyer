from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from regional_guides import RegionalStore
from regional_xian_high_tech_guide import SOURCE, staged_guide
from routes import regional_guides as routes


ROOT = Path(__file__).resolve().parents[2]
PROOF = SOURCE.with_name("ATTACHMENT-LINKS-PROOF.json")
SCOPE = {"province": "shaanxi", "city": "西安市", "district": "高新区管委会"}
TEMPLATE = "xian-610152-delivery-address"
OFFICIAL = "https://xdz.xa.gov.cn/web_files/xdz/file/2023/10/16/202310161146024877498.docx"


class XianHighTechAttachmentsTests(TestCase):
    def test_pinned_blank_attachments_are_local_official_download_only(self):
        root = Path(self.enterContext(TemporaryDirectory()))
        (root / SOURCE).parent.mkdir(parents=True)
        (root / SOURCE).write_bytes((ROOT / SOURCE).read_bytes())
        store = RegionalStore(root / "guides.sqlite")
        guide = store.put_guide(staged_guide(root))
        app = FastAPI()
        app.include_router(routes.router, prefix="/regional")
        self.enterContext(patch.object(routes, "ROOT", root))
        self.enterContext(patch.object(routes, "store", return_value=store))
        client = self.enterContext(TestClient(app))

        def templates(params=SCOPE):
            response = client.get("/regional/lookup", params=params)
            self.assertEqual(response.status_code, 200)
            return response.json()["templates"]

        payload = {**SCOPE, "source_id": guide["source_id"], "version": guide["version"],
                   "kind": "application", "template_id": TEMPLATE}
        self.assertEqual(templates(), [])
        (root / PROOF).write_bytes((ROOT / PROOF).read_bytes())
        official_templates = templates()
        self.assertEqual(
            [row["id"] for row in official_templates],
            ["xian-610152-proxy-recommendation", "xian-610152-authorization", "xian-610152-representative-proof", TEMPLATE],
        )
        self.assertTrue(all(t["download_status"] == "official_link_only" and not t["can_generate"]
                            and t["document_types"] == [] for t in official_templates))
        self.assertEqual([t["original_format"] for t in official_templates], ["DOC", "DOC", "DOC", "DOCX"])
        result = official_templates[-1]
        self.assertEqual((result["id"], result["region_code"], result["source_url"]), (TEMPLATE, "610152", OFFICIAL))
        self.assertEqual(result["official_sha256"], "9bb9804def411d650c8efd3cc8e8b6b2cdf0fee35a0fb9722f25da90d5113dd4")
        self.assertIn("正反面打印", result["original_name"])
        self.assertEqual(result["download_status"], "official_link_only")
        self.assertEqual(result["document_types"], [])
        self.assertFalse(result["can_generate"])
        self.assertNotIn("file", result)
        self.assertEqual(templates({**SCOPE, "xlsx": True}), official_templates)
        self.assertEqual(templates({**SCOPE, "district": "新城区"}), [])
        self.assertEqual(client.get("/regional/form-contract", params=payload).status_code, 409)
        self.assertEqual(client.get(f"/regional/templates/{TEMPLATE}", params=payload).status_code, 404)
        self.assertEqual(client.post("/regional/generate", json={**payload, "mode": "blank", "data": {}}).status_code, 409)
        store.put_guide({**guide, "source_version": "different", "templates": []})
        self.assertEqual(templates(), [])
        store.put_guide(staged_guide(root))
        (root / PROOF).write_bytes(b"changed")
        self.assertEqual(templates(), [])
