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
from regional_xian_high_tech_application import LAYOUT as APPLICATION_LAYOUT, TEMPLATE_ID as APPLICATION_ID, staged_application_candidate
from regional_xian_high_tech_guide import SOURCE, staged_guide
from routes import regional_guides as routes


ROOT = Path(__file__).resolve().parents[2]
SCOPE = {"province": "shaanxi", "city": "西安市", "district": "高新区管委会"}
TEMPLATE = "xian-610152-evidence"
WORKBOOK = os.getenv("LABOURLAWYER_XIAN_HIGH_TECH_WORKBOOK")
APPLICATION = os.getenv("LABOURLAWYER_XIAN_HIGH_TECH_LAYOUT")
SHEET = "xl/worksheets/sheet1.xml"
XML = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
MEDIA = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


class XianHighTechEvidenceTests(TestCase):
    @skipUnless(WORKBOOK and APPLICATION, "verified files are kept locally")
    def test_only_xlsx_clients_can_generate_the_local_evidence_workbook(self):
        root = Path(self.enterContext(TemporaryDirectory()))
        source = root / SOURCE
        source.parent.mkdir(parents=True)
        source.write_bytes((ROOT / SOURCE).read_bytes())
        layout = root / APPLICATION_LAYOUT
        layout.parent.mkdir(parents=True)
        layout.write_bytes(Path(APPLICATION).read_bytes())
        book = layout.with_name("xian-610152-evidence-private.xlsx")
        book.write_bytes(Path(WORKBOOK).read_bytes())
        raw_sha = sha256(book.read_bytes()).hexdigest()
        guide = staged_application_candidate(root)
        store = RegionalStore(root / "guides.sqlite")
        guide = store.put_guide(guide)
        directory = DirectoryStore(root / "areas.sqlite")
        areas = json.loads((ROOT / "data/public-regions/directory.json").read_bytes())
        directory.put_area(next(a for a in areas if a["code"] == "610152"))
        app = FastAPI()
        app.include_router(routes.router, prefix="/regional")
        self.enterContext(patch.object(routes, "ROOT", root))
        self.enterContext(patch.object(routes, "store", return_value=store))
        self.enterContext(patch.object(routes, "directory_store", return_value=directory))
        self.enterContext(patch.dict(os.environ, {"LABOURLAWYER_DATA_DIR": str(root / "data")}))
        client = self.enterContext(TestClient(app))

        def ids(params):
            return [t["id"] for t in client.get("/regional/lookup", params={**SCOPE, **params}).json()["templates"]]
        self.assertEqual(ids({}), [APPLICATION_ID])
        self.assertEqual(ids({"xlsx": True}), [APPLICATION_ID, TEMPLATE])
        for path in ("/regional/lookup", "/regional/areas"):
            other = client.get(path, params={"province": "shaanxi", "city": "西安市", "district": "新城区", "xlsx": True})
            self.assertEqual(other.status_code, 200)
            if "templates" in other.json():
                self.assertEqual(other.json()["templates"], [])

        binding = {**SCOPE, "source_id": guide["source_id"], "version": guide["version"], "kind": "evidence", "template_id": TEMPLATE}
        response = client.get("/regional/form-contract", params={**binding, "xlsx": True})
        self.assertEqual(response.status_code, 200, response.text)
        contract = response.json()
        self.assertEqual(contract["context"]["output_format"], "xlsx")
        self.assertEqual(contract["context"]["template_sha256"], raw_sha)
        self.assertEqual(contract["fields"][0]["maxItems"], 12)
        self.assertEqual([f["key"] for f in contract["fields"][0]["fields"]], ["name", "page_range", "source", "purpose"])
        item = {"name": "=2+3", "page_range": "01-03", "source": "本人留存", "purpose": "说明实际工时"}
        payload = {**binding, "mode": "blank", "contract_id": contract["contract_id"], "data": {"items": [item] * 12}}
        self.assertEqual(client.post("/regional/generate", json=payload).status_code, 409)
        for overrides in ({"contract_id": None}, {"district": "新城区"}, {"kind": "application"},
                          {"source_id": "different"}, {"version": guide["version"] + 1}, {"mode": "reference_adaptation"}):
            self.assertEqual(client.post("/regional/generate?xlsx=true", json={**payload, **overrides}).status_code, 409)
        for invalid in ([item] * 13, [{**item, "name": "超" * 8}], [{**item, "source": "换\n行"}], [{**item, "name": " "}]):
            self.assertEqual(client.post("/regional/generate?xlsx=true", json={**payload, "data": {"items": invalid}}).status_code, 422)
        output = client.post("/regional/generate?xlsx=true", json=payload)
        self.assertEqual(output.status_code, 200, output.text if output.status_code != 200 else "")
        self.assertEqual(output.headers["content-type"], MEDIA)
        self.assertEqual(output.headers["cache-control"], "no-store")
        self.assertEqual(output.headers["x-form-contract-id"], contract["contract_id"])
        self.assertEqual(output.headers["x-document-origin"], "official-blank-filled")
        with ZipFile(BytesIO(output.content)) as archive, ZipFile(book) as original:
            self.assertIsNone(archive.testzip())
            self.assertEqual(archive.namelist(), original.namelist())
            for part in set(archive.namelist()) - {SHEET, "docProps/core.xml", "docProps/custom.xml"}:
                self.assertEqual(archive.read(part), original.read(part), part)
            src = ET.fromstring(original.read(SHEET))
            filled = ET.fromstring(archive.read(SHEET))
            for row in (2, 4, 5, 18, 19):
                xpath = f".//m:row[@r='{row}']"
                self.assertEqual(ET.tostring(filled.find(xpath, XML)), ET.tostring(src.find(xpath, XML)))
            for row in range(6, 18):
                self.assertEqual(filled.findtext(f".//m:c[@r='A{row}']/m:v", namespaces=XML), str(row - 5))
                for col, key in zip("BCDE", ("name", "page_range", "source", "purpose"), strict=True):
                    cell = filled.find(f".//m:c[@r='{col}{row}']", XML)
                    self.assertEqual(cell.get("t"), "inlineStr")
                    self.assertIsNone(cell.find("m:f", XML))
                    self.assertEqual(cell.findtext("m:is/m:t", namespaces=XML), item[key])
        self.assertEqual(sha256(book.read_bytes()).hexdigest(), raw_sha)
        self.assertEqual(client.get(f"/regional/templates/{TEMPLATE}", params=binding).status_code, 404)
        layout.unlink()
        standalone = store.put_guide(staged_guide(root))
        self.assertEqual(ids({}), [])
        self.assertEqual(ids({"xlsx": True}), [TEMPLATE])
        stand_binding = {**binding, "version": standalone["version"]}
        self.assertEqual(client.get("/regional/form-contract", params={**stand_binding, "xlsx": True}).status_code, 200)
        self.assertEqual(client.post("/regional/generate?xlsx=true", json=payload).status_code, 409)
        book.write_bytes(b"changed")
        self.assertEqual(ids({"xlsx": True}), [])
        self.assertEqual(client.post("/regional/generate?xlsx=true", json=payload).status_code, 409)
