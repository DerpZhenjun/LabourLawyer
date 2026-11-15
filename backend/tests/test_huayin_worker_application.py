from io import BytesIO
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, skipUnless
from unittest.mock import patch

from docx import Document
from fastapi import FastAPI
from fastapi.testclient import TestClient

from regional_guides import RegionalStore
from routes import regional_guides as routes


ROOT = Path(__file__).resolve().parents[2]
PRIVATE = os.getenv("LABOURLAWYER_HUAYIN_WORKER_LAYOUT")
DATA = {"requests": ["合成请求甲", "合成请求乙"], "facts": ["合成事实一", "合成事实二"]}


class HuayinWorkerApplicationTests(TestCase):
    def test_body_row_limits_and_manual_fields(self):
        from regional_huayin_application import HuayinWorkerApplicationRequest

        self.assertEqual(HuayinWorkerApplicationRequest.model_validate(DATA).model_dump(), DATA)
        for data in (
            {"applicant_name": "示例"}, {"signature": "示例"}, {"requests": ["甲"]*6},
            {"facts": ["甲"]*13}, {"requests": ["甲\n乙"]}, {"facts": ["甲"*21]},
            {"requests": ["W"*21]}, {"requests": "示例"}, {"facts": [1]},
        ):
            with self.subTest(data=data), self.assertRaises(ValueError):
                HuayinWorkerApplicationRequest.model_validate(data)

    @skipUnless(PRIVATE, "Verified Word conversion retained in the local evidence")
    def test_body_only_filled_in_existing_rows_with_source_font(self):
        from regional_huayin_application import SLOTS, fill_application

        raw = Path(PRIVATE).read_bytes()
        baseline = Document(BytesIO(raw))
        output = fill_application(raw, DATA)
        changed = {17, 18, 24, 25}
        self.assertEqual(len(output.paragraphs), 44)
        for index in set(range(44)) - changed:
            self.assertEqual(output.paragraphs[index]._p.xml, baseline.paragraphs[index]._p.xml)
        for key, values in DATA.items():
            start, *_ = SLOTS[key]
            for index, value in enumerate(values, start):
                run, = output.paragraphs[index].runs
                self.assertEqual(run.text, value)
                self.assertEqual(run._r.rPr.xml, baseline.paragraphs[index]._p.xpath("./w:pPr/w:rPr")[0].xml)
        self.assertEqual([p._p.xml for p in fill_application(raw, {}).paragraphs],
                         [p._p.xml for p in baseline.paragraphs])
        with self.assertRaises(ValueError):
            fill_application(raw+b" ", DATA)

    @skipUnless(PRIVATE, "Verified Word conversion retained in the local evidence")
    def test_exact_worker_template_contract_and_native_download(self):
        from regional_huayin_application import LAYOUT, TEMPLATE_ID, staged_worker_candidate
        from regional_huayin_guides import SOURCE

        root = Path(self.enterContext(TemporaryDirectory()))
        for target, evidence in ((SOURCE, ROOT / SOURCE), (LAYOUT, Path(PRIVATE))):
            path = root / target
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(evidence.read_bytes())
        store = RegionalStore(root / "guides.sqlite")
        guide = store.put_guide(staged_worker_candidate(root))
        self.assertFalse(guide["published"])
        self.assertEqual([item["service_object"] for item in guide["templates"]], ["劳动者"])
        self.assertEqual(set(guide["role_sources"]), {"劳动者", "用人单位"})

        app = FastAPI()
        app.include_router(routes.router, prefix="/regional")
        self.enterContext(patch.object(routes, "ROOT", root))
        self.enterContext(patch.object(routes, "store", return_value=store))
        self.enterContext(patch.dict(os.environ, {"LABOURLAWYER_DATA_DIR": str(root / "private")}))
        client = self.enterContext(TestClient(app))
        bound = {key: guide[key] for key in ("province", "city", "district", "source_id", "version")}
        bound.update(kind="application", template_id=TEMPLATE_ID)
        contract = client.get("/regional/form-contract", params=bound).json()
        self.assertEqual({f["key"]:f["maxItems"] for f in contract["fields"]}, {"requests":5,"facts":12})
        payload = {**bound, "contract_id": contract["contract_id"], "mode": "blank", "data": DATA}
        response = client.post("/regional/generate", json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["x-document-origin"], "official-blank-converted-filled")
        self.assertEqual(response.headers["x-form-contract-id"], contract["contract_id"])
        self.assertEqual(Document(BytesIO(response.content)).paragraphs[25].text, DATA["facts"][1])
        for update in (
            {"contract_id": None}, {"mode": "reference_adaptation"}, {"district": "韩城市"},
            {"template_id": "weinan-610582-employer-application"},
        ):
            self.assertEqual(client.post("/regional/generate", json={**payload, **update}).status_code, 409)
        self.assertEqual(client.post("/regional/generate", json={**payload, "data":{"facts":["甲"*21]}}).status_code, 422)
        self.assertEqual(client.get(f"/regional/templates/{TEMPLATE_ID}", params=bound).status_code, 404)
        (root / LAYOUT).write_bytes(b"changed")
        self.assertEqual(client.get("/regional/form-contract", params=bound).status_code, 409)
