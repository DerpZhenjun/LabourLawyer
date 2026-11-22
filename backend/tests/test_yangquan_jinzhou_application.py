from io import BytesIO
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from docx import Document
from fastapi import FastAPI
from fastapi.testclient import TestClient

from regional_guides import RegionalStore
from routes import regional_guides as routes


class MunicipalApplicationTests(TestCase):
    def test_official_blank_application_only_and_exact_location(self):
        from regional_yangquan_jinzhou import PROFILES, staged_guide

        temp = Path(self.enterContext(TemporaryDirectory()))
        store = RegionalStore(temp / 'guides.sqlite')
        app = FastAPI()
        app.include_router(routes.router, prefix='/regional')
        self.enterContext(patch.object(routes, 'store', return_value=store))
        self.enterContext(patch.dict(os.environ, {'LABOURLAWYER_DATA_DIR': str(temp / 'private')}))
        client = self.enterContext(TestClient(app))
        for code, profile in PROFILES.items():
            with self.subTest(code=code):
                guide = store.put_guide(staged_guide(code))
                self.assertFalse(guide['published'])
                self.assertFalse(guide['materials_complete'])
                template, = guide['templates']
                bound = {key: guide[key] for key in ('province', 'city', 'district', 'source_id', 'version')}
                bound.update(kind='application', template_id=template['id'])
                contract_response = client.get('/regional/form-contract', params=bound)
                self.assertEqual(contract_response.status_code, 200, contract_response.text)
                contract = contract_response.json()
                payload = {
                    **bound, 'contract_id': contract['contract_id'], 'mode': 'blank',
                    'data': {'applicantName': '测试甲', 'respondentName': '测试乙',
                             'requests': ['合成请求'], 'facts': ['合成事实']},
                }
                response = client.post('/regional/generate', json=payload)
                self.assertEqual(response.status_code, 200, response.text[:100] if response.status_code != 200 else '')
                self.assertEqual(response.headers['x-document-origin'], profile['origin'])
                self.assertEqual(response.headers['x-form-contract-id'], contract['contract_id'])
                doc = Document(BytesIO(response.content))
                content = doc.element.body.xml
                for value in ('测试甲', '测试乙', '合成请求', '合成事实', guide['city']):
                    self.assertIn(value, content)
                for updates in ({'district': '其他区'}, {'kind': 'evidence'}, {'contract_id': None},
                                {'mode': 'reference_adaptation'}, {'version': guide['version'] + 1}):
                    self.assertEqual(client.post('/regional/generate', json={**payload, **updates}).status_code, 409)
                for invalid in ({'signature': '禁止代签'}, {'facts': ['甲\n乙']}, {'requests': ['甲' * 60]}):
                    self.assertEqual(client.post('/regional/generate', json={**payload, 'data': invalid}).status_code, 422)

    def test_origin_binding_rejects_changed_guide_or_file(self):
        from regional_yangquan_jinzhou import PROFILES, ROOT, checked_adapter, staged_guide

        for code, profile in PROFILES.items():
            root = Path(self.enterContext(TemporaryDirectory()))
            for name in ('source', 'original', 'layout'):
                file = profile[name]
                dest = root / file
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes((ROOT / file).read_bytes())
            guide = staged_guide(code, root)
            template, = guide['templates']
            self.assertEqual(checked_adapter(guide, template, 'application', root), profile['adapter'])
            with self.assertRaises(ValueError):
                checked_adapter({**guide, 'authority': '其他机构'}, template, 'application', root)
            (root / profile['original']).write_bytes(b'tampered')
            with self.assertRaises(ValueError):
                checked_adapter(guide, template, 'application', root)
