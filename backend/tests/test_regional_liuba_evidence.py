"""Exact-locality integration tests; original workbook is private."""
from hashlib import sha256
from io import BytesIO
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, skipUnless
from unittest.mock import patch
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from fastapi import FastAPI
from fastapi.testclient import TestClient

from regional_directory import DirectoryStore
from regional_guides import RegionalStore
from regional_hanzhong_guides import staged_guide
from routes import regional_guides as routes

ROOT = Path(__file__).resolve().parents[2]
SCOPE = {"province":"shaanxi","city":"汉中市","district":"留坝县"}
TEMPLATE_ID = "hanzhong-610729-evidence"
LAYOUT = Path("templates/_docx/_regional/shaanxi/liuba-610729-private-source.xlsx")
FORMAT = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


class LiubaXlsxApiTests(TestCase):
    def setUp(self):
        self.work = self.enterContext(TemporaryDirectory())
        self.root = Path(self.work)
        self.layout = self.root / LAYOUT
        self.layout.parent.mkdir(parents=True)
        self.store = RegionalStore(self.root / "guides.sqlite")
        self.dir = DirectoryStore(self.root / "areas.sqlite")
        self.guide = self.store.put_guide(staged_guide("610729", ROOT))
        self.store.put_guide(staged_guide("610730", ROOT))
        entries = json.loads((ROOT / "data/public-regions/directory.json").read_bytes())
        self.dir.put_area(next(row for row in entries if row["code"] == "610729"))
        self.source = {**SCOPE,"source_id":self.guide["source_id"],"version":self.guide["version"],
                       "kind":"evidence","template_id":TEMPLATE_ID}
        app = FastAPI()
        app.include_router(routes.router, prefix="/regional")
        self.enterContext(patch.object(routes, "ROOT", self.root))
        self.enterContext(patch.object(routes, "store", return_value=self.store))
        self.enterContext(patch.object(routes, "directory_store", return_value=self.dir))
        self.enterContext(patch.dict(os.environ, {"LABOURLAWYER_DATA_DIR": str(self.root / "data")}))
        self.client = self.enterContext(TestClient(app))

    def install(self):
        self.layout.write_bytes(Path(os.environ["LIUBA_OWN_SOURCE"]).read_bytes())

    def test_missing_or_changed_xlsx_remains_guide_only(self):
        def assert_guide_only():
            data = self.client.get("/regional/lookup", params={**SCOPE,"xlsx":True}).json()
            self.assertEqual(data["source_id"], self.guide["source_id"])
            self.assertFalse(data["can_generate"])
            self.assertEqual(self.client.get(
                "/regional/form-contract", params={**self.source,"xlsx":True},
            ).status_code,409)
        assert_guide_only()
        self.layout.write_bytes(b"edited source")
        assert_guide_only()

    @skipUnless(os.environ.get("LIUBA_OWN_SOURCE"), "official blank workbook available only in private evidence")
    def test_xlsx_opt_in_exact_region_and_request_does_not_change_legacy_docx_support(self):
        self.install()
        old = self.client.get("/regional/lookup", params=SCOPE).json()
        self.assertFalse(old["can_generate"])
        new = self.client.get("/regional/lookup", params={**SCOPE,"xlsx":True}).json()
        self.assertTrue(new["can_generate"])
        self.assertEqual([entry["id"] for entry in new["templates"] if entry["can_generate"]], [TEMPLATE_ID])
        for opt in (False,True):
            areas = self.client.get("/regional/areas",params={"province":"shaanxi","city":"汉中市","xlsx":opt}).json()
            entry = next(row for row in areas["items"] if row["district"]=="留坝县")
            self.assertIs(entry["can_generate"], opt)
        self.assertEqual(self.client.get("/regional/form-contract",params=self.source).status_code,409)
        response = self.client.get("/regional/form-contract",params={**self.source,"xlsx":True})
        self.assertEqual(response.status_code,200,response.text)
        contract = response.json()
        self.assertEqual(contract["context"]["output_format"],"xlsx")
        self.assertEqual(contract["fields"][0]["fields"][2]["label"],"页数")
        payload = {**self.source,"mode":"blank","contract_id":contract["contract_id"],
                   "data":{"items":[{"name":"虚构材料","purpose":"核对工时","page_count":"12"}]}}
        self.assertEqual(self.client.post("/regional/generate", json=payload).status_code,409)
        self.assertEqual(self.client.post("/regional/generate?xlsx=true", json={**payload,"contract_id":None}).status_code,409)
        self.assertEqual(self.client.post("/regional/generate?xlsx=true", json={**payload,"contract_id":"0"*64}).status_code,409)
        self.assertEqual(self.client.post("/regional/generate?xlsx=true", json={**payload,"version":self.source["version"]+1}).status_code,409)
        self.assertEqual(self.client.post("/regional/generate?xlsx=true", json={**payload,"mode":"reference_adaptation"}).status_code,409)
        self.assertEqual(self.client.post("/regional/generate?xlsx=true", json={**payload,"district":"佛坪县"}).status_code,409)
        bad = {**payload,"data":{"items":[{"name":"虚构","page_count":"2-4"}]}}
        self.assertEqual(self.client.post("/regional/generate?xlsx=true",json=bad).status_code,422)
        result = self.client.post("/regional/generate?xlsx=true",json=payload)
        self.assertEqual(result.status_code,200,result.text if result.status_code!=200 else "")
        self.assertEqual(result.headers["content-type"],FORMAT)
        self.assertIn(".xlsx",result.headers["content-disposition"])
        self.assertEqual(result.headers["x-form-contract-id"],contract["contract_id"])
        self.assertEqual(result.headers["x-guide-source-id"],self.guide["source_id"])
        self.assertEqual(result.headers["x-document-origin"],"official-blank-filled")
        self.assertEqual(result.headers["cache-control"],"no-store")
        with ZipFile(BytesIO(result.content)) as book:
            self.assertIsNone(book.testzip())
            ns = {"m":"http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
            sheet = ET.fromstring(book.read("xl/worksheets/sheet1.xml"))
            self.assertEqual(sheet.findtext(".//m:c[@r='E3']/m:v",namespaces=ns),"12")
        self.assertEqual(list((self.root/"data/generated").glob("*")),[])
        self.assertEqual(sha256(self.layout.read_bytes()).hexdigest(),contract["context"]["template_sha256"])
        self.assertEqual(self.client.get(f"/regional/templates/{TEMPLATE_ID}", params=self.source).status_code,404)
