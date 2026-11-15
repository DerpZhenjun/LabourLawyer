import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from regional_directory import DirectoryStore
from regional_guides import RegionalStore
from regional_xianyang_sanyuan_guides import SOURCE as GUIDE_PROOF, staged_guide
from routes import regional_guides as routes


ROOT = Path(__file__).resolve().parents[2]
PROOF = GUIDE_PROOF.with_name("ATTACHMENT-LINKS-PROOF.json")
SCOPE = {"province": "shaanxi", "city": "咸阳市", "district": "三原县"}
WORKER = "xianyang-610422-worker-application"
EMPLOYER = "xianyang-610422-employer-application"
EVIDENCE = "xianyang-610422-worker-evidence-list"


class XianyangSanyuanOfficialAttachmentLinksTests(TestCase):
    def test_only_three_content_verified_blank_forms_are_exposed(self):
        root = Path(self.enterContext(TemporaryDirectory()))
        (root / PROOF).parent.mkdir(parents=True)
        directory = DirectoryStore(root / "directory.sqlite")
        for area in json.loads((ROOT / "data/public-regions/directory.json").read_bytes()):
            if area["code"] in {"610400", "610402", "610404", "610422", "610481"}:
                directory.put_area(area)
        self.enterContext(patch.object(routes, "directory_store", return_value=directory))
        store = RegionalStore(root / "guides.sqlite")
        guide = store.put_guide(staged_guide(ROOT))
        app = FastAPI()
        app.include_router(routes.router, prefix="/regional")
        self.enterContext(patch.object(routes, "ROOT", root))
        self.enterContext(patch.object(routes, "store", return_value=store))
        client = self.enterContext(TestClient(app))

        def templates(params=SCOPE):
            returned = client.get("/regional/lookup", params=params)
            self.assertEqual(returned.status_code, 200)
            return returned.json()["templates"]

        self.assertEqual(templates(), [])
        (root / PROOF).write_bytes((ROOT / PROOF).read_bytes())
        official = templates()
        self.assertEqual([item["id"] for item in official], [WORKER, EMPLOYER, EVIDENCE])
        expected = (
            ("劳动者", "b2781e80d301afa6b80b56ba1c7616741e0b94f2a8528980e7942700583052be"),
            ("用人单位", "b2781e80d301afa6b80b56ba1c7616741e0b94f2a8528980e7942700583052be"),
            ("证据清单", "e572247a5ec3c63bfd7b4d97e53c0324e1246f5b02523bca57ec95a31abf2bf1"),
        )
        for item, (role_label, sha) in zip(official, expected):
            self.assertIn(role_label, item["original_name"])
            self.assertEqual(item["official_sha256"], sha)
            self.assertEqual(item["region_code"], "610422")
            self.assertEqual(item["download_status"], "official_link_only")
            self.assertFalse(item["can_generate"])
            self.assertEqual(item["document_types"], [])
            self.assertNotIn("file", item)
        self.assertEqual(official[0]["guide_source_url"], guide["role_sources"]["劳动者"])
        self.assertEqual(official[1]["guide_source_url"], guide["role_sources"]["用人单位"])
        self.assertNotEqual(official[0]["source_url"], official[1]["source_url"])
        self.assertEqual(official[2]["guide_source_url"], guide["role_sources"]["劳动者"])
        self.assertEqual(official[0]["official_sha256"], official[1]["official_sha256"])
        self.assertNotEqual(official[0]["official_sha256"], official[2]["official_sha256"])
        self.assertEqual(templates({**SCOPE, "xlsx": True}), official)
        for district in ("", "市本级", "秦都区", "渭城区", "兴平市"):
            self.assertEqual(templates({**SCOPE, "district": district}), [])
        for item in (WORKER, EMPLOYER, EVIDENCE):
            params = {**SCOPE, "source_id": guide["source_id"], "version": guide["version"],
                      "kind": "application", "template_id": item}
            self.assertEqual(client.get("/regional/form-contract", params=params).status_code, 409)
            self.assertEqual(client.get(f"/regional/templates/{item}", params=params).status_code, 404)
            self.assertEqual(client.post("/regional/generate", json={**params, "mode": "blank", "data": {}}).status_code, 409)
        store.put_guide({**guide, "source_version": "0" * 64, "templates": []})
        self.assertEqual(templates(), [])
        store.put_guide(staged_guide(ROOT))
        (root / PROOF).write_bytes((root / PROOF).read_bytes() + b" ")
        self.assertEqual(templates(), [])
