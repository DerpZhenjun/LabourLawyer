"""The own-source applications cannot borrow a county or an evidence template."""
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from docx import Document
from fastapi import FastAPI
from fastapi.testclient import TestClient

from regional_guides import RegionalStore
from routes import regional_guides as routes


ROOT = Path(__file__).resolve().parents[2]


class BaojiCountyApplicationAPITests(TestCase):
    def test_generation_and_download_are_source_bound(self):
        from regional_baoji_county_application import staged_guide

        with TemporaryDirectory() as work:
            store = RegionalStore(Path(work) / 'guide.sqlite')
            guides = {code: store.put_guide(staged_guide(code, ROOT)) for code in ('610323', '610326', '610327', '610329', '610303', '610331', '610302')}
            app = FastAPI()
            app.include_router(routes.router, prefix='/regional')
            with patch.object(routes, 'ROOT', ROOT), patch.object(routes, 'store', return_value=store), TestClient(app) as client:
                for code, guide in guides.items():
                    with self.subTest(code=code):
                        template, = guide['templates']
                        query = {key: guide[key] for key in ('province', 'city', 'district', 'source_id', 'version')}
                        query.update(template_id=template['id'], kind='application')
                        contract = client.get('/regional/form-contract', params=query)
                        self.assertEqual(contract.status_code, 200, contract.text)
                        self.assertEqual(contract.json()['policy']['signature_field'], 'manual_only')
                        blank = client.get(f"/regional/templates/{template['id']}", params=query)
                        self.assertEqual(blank.status_code, 200)
                        self.assertEqual(blank.headers['X-Template-SHA256'], template['sha256'])
                        if code in {'610329', '610303', '610331'}:
                            self.assertEqual(blank.headers['X-Document-Origin'], 'official-blank-converted-layout')
                            self.assertEqual(template['original_format'], 'DOC')
                        if code == '610302':
                            self.assertEqual(guide['authority'], '渭滨区人力资源和社会保障局')
                            self.assertIn('2d4627f40526c121783dd9a99196cc2a', template['source_url'])
                            application = next(m for m in guide['materials'] if '仲裁申请书' in m['name'])
                            self.assertIn('原件1份', application['copies'])
                        if code == '610303':
                            self.assertEqual(guide['authority'], '金台区人力资源和社会保障局')
                            self.assertIn('b98e034d881b2120f4e36b837c117c45', template['source_url'])
                        if code == '610331':
                            self.assertEqual(guide['authority'], '太白县人力资源和社会保障局')
                            self.assertIn('3b70d8828ceebd348910308ca34a8812', template['source_url'])
                            keys = {field['key'] for field in contract.json()['fields']}
                            self.assertIn('third_party_name', keys)
                            self.assertIn('evidence_copies', keys)
                            self.assertNotIn('signature', keys)
                            self.assertNotIn('id_number', keys)
                        if code == '610329':
                            keys = {field['key'] for field in contract.json()['fields']}
                            self.assertIn('applicant_work_unit', keys)
                            self.assertNotIn('id_number', keys)
                        payload = {**query, 'mode': 'blank', 'contract_id': contract.json()['contract_id'],
                                   'data': {'applicant_name': '测试劳动者'}}
                        response = client.post('/regional/generate', json=payload)
                        self.assertEqual(response.status_code, 200, response.text if not response.is_success else '')
                        self.assertEqual(response.headers['X-Document-Origin'], 'official-blank-filled')
                        self.assertIn('测试劳动者', ''.join(p.text for p in Document(BytesIO(response.content)).paragraphs))
                        self.assertEqual(client.post('/regional/generate', json={**payload, 'kind': 'evidence'}).status_code, 409)
                        self.assertEqual(client.post('/regional/generate', json={**payload, 'contract_id': None}).status_code, 409)
                wrong = guides['610327']
                self.assertIn(client.get('/regional/templates/baoji-610323-worker-application', params={
                    'province': wrong['province'], 'city': wrong['city'], 'district': wrong['district'],
                    'source_id': wrong['source_id'], 'version': wrong['version'],
                }).status_code, (404, 409))


    def test_fengxian_offers_a_source_bound_handwritten_blank_without_generation(self):
        from hashlib import sha256
        from regional_baoji_county_application import staged_fengxian_guide, staged_guide

        with TemporaryDirectory() as work:
            store = RegionalStore(Path(work) / 'guide.sqlite')
            guide = store.put_guide(staged_fengxian_guide(ROOT))
            neighbor = store.put_guide(staged_guide('610331', ROOT))
            template, = guide['templates']
            self.assertEqual(guide['region_code'], '610330')
            self.assertIs(guide['can_generate'], False)
            self.assertIs(template['can_generate'], False)
            keys = ('province', 'city', 'district', 'source_id', 'version')
            query = {key: guide[key] for key in keys}
            path = f"/regional/templates/{template['id']}"
            app = FastAPI()
            app.include_router(routes.router, prefix='/regional')
            with patch.object(routes, 'ROOT', ROOT), patch.object(routes, 'store', return_value=store), TestClient(app) as client:
                blank = client.get(path, params=query)
                self.assertEqual(blank.status_code, 200, blank.text if not blank.is_success else '')
                self.assertEqual(blank.headers['X-Document-Origin'], 'official-handwritten-blank-layout')
                self.assertEqual(sha256(blank.content).hexdigest(), template['sha256'])
                self.assertIn('必须用钢笔或黑色签字笔书写', '\n'.join(p.text for p in Document(BytesIO(blank.content)).paragraphs))
                self.assertEqual(client.get(path, params={**query, 'version': guide['version'] + 1}).status_code, 409)
                self.assertEqual(client.get(path, params={key: neighbor[key] for key in keys}).status_code, 404)
                generate_query = {**query, 'template_id': template['id'], 'kind': 'application'}
                self.assertEqual(client.get('/regional/form-contract', params=generate_query).status_code, 409)
                self.assertEqual(client.post('/regional/generate', json={**generate_query, 'mode': 'blank', 'data': {}}).status_code, 409)


    def test_fengxiang_exposes_its_official_sample_link_without_generation(self):
        from regional_baoji_county_application import staged_fengxiang_guide

        with TemporaryDirectory() as work:
            store = RegionalStore(Path(work) / 'guide.sqlite')
            guide = store.put_guide(staged_fengxiang_guide(ROOT))
            self.assertEqual(guide['region_code'], '610305')
            self.assertEqual(guide['authority'], '凤翔区人力资源和社会保障局')
            self.assertEqual(len(guide['materials']), 4)
            self.assertIs(guide['can_generate'], False)
            template, = guide['templates']
            self.assertEqual(template['official_kind'], 'sample')
            self.assertEqual(template['download_status'], 'official_link_only')
            self.assertIs(template['can_generate'], False)
            self.assertIn('e98532adcf9a3fdfbe2e5aa75271d289', template['source_url'])
            query = {key: guide[key] for key in ('province', 'city', 'district', 'source_id', 'version')}
            app = FastAPI()
            app.include_router(routes.router, prefix='/regional')
            with patch.object(routes, 'ROOT', ROOT), patch.object(routes, 'store', return_value=store), TestClient(app) as client:
                self.assertEqual(client.get(f"/regional/templates/{template['id']}", params=query).status_code, 404)
                query.update(template_id=template['id'], kind='application')
                self.assertEqual(client.get('/regional/form-contract', params=query).status_code, 409)
                self.assertEqual(client.post('/regional/generate', json={**query,'mode':'blank','data':{}}).status_code, 409)


    def test_additional_own_guides_keep_sample_assets_out_of_generation(self):
        from regional_baoji_county_application import staged_guide_without_generation

        with TemporaryDirectory() as work:
            store = RegionalStore(Path(work) / 'guide.sqlite')
            app = FastAPI()
            app.include_router(routes.router, prefix='/regional')
            with patch.object(routes, 'ROOT', ROOT), patch.object(routes, 'store', return_value=store), TestClient(app) as client:
                for code, district, count, source_code in (
                    ('610328', '千阳县', 4, '6f11d0a717c9718711197ed1e6aff2df'),
                    ('610304', '陈仓区', 4, 'ed4d601ac3dc1a52d00dc8eb45160799'),
                    ('610324', '扶风县', 5, 'e1dad0769f9b91085d75cda86abb6f85'),
                ):
                    with self.subTest(code=code):
                        guide = store.put_guide(staged_guide_without_generation(code, ROOT))
                        self.assertIs(guide['can_generate'], False)
                        self.assertEqual(guide['authority'], district + '人力资源和社会保障局')
                        self.assertIn(source_code, guide['source_url'])
                        self.assertEqual(len(guide['materials']), count)
                        self.assertTrue(all(m['region_code'] == code for m in guide['materials']))
                        template_id = f'baoji-{code}-worker-application-sample'
                        if code == '610328':
                            self.assertEqual(guide['templates'], [])
                            self.assertIn('未列申请书空表', guide['warnings'][0])
                        else:
                            template, = guide['templates']
                            self.assertEqual(template['id'], template_id)
                            self.assertEqual(template['official_kind'], 'sample')
                            self.assertEqual(template['download_status'], 'official_link_only')
                            self.assertIs(template['can_generate'], False)
                        scope = {key: guide[key] for key in ('province', 'city', 'district', 'source_id', 'version')}
                        query = {**scope, 'template_id': template_id, 'kind': 'application'}
                        self.assertEqual(client.get(f'/regional/templates/{template_id}', params=scope).status_code, 404)
                        self.assertEqual(client.get('/regional/form-contract', params=query).status_code, 409)
                        self.assertEqual(client.post('/regional/generate', json={**query,'mode':'blank','data':{}}).status_code, 409)


    def test_chencang_authorization_is_a_bound_download_only_blank(self):
        from regional_baoji_county_application import staged_chencang_authorization_guide, staged_guide_without_generation

        with TemporaryDirectory() as work:
            store = RegionalStore(Path(work) / 'guide.sqlite')
            previous = store.put_guide(staged_guide_without_generation('610304', ROOT))
            guide = store.put_guide(staged_chencang_authorization_guide(ROOT))
            self.assertGreater(guide['version'], previous['version'])
            self.assertEqual(guide['materials'], previous['materials'])
            self.assertFalse(guide['can_generate'])
            self.assertIn('受理通知书或应诉通知书', ' '.join(guide['warnings']))
            template, = [t for t in guide['templates'] if t['official_kind'] == 'blank']
            self.assertFalse(template['can_generate'])
            self.assertEqual(template['region_code'], '610304')
            self.assertEqual(template['source_url'], guide['source_url'])
            scope = {key: guide[key] for key in ('province', 'city', 'district', 'source_id', 'version')}
            app = FastAPI()
            app.include_router(routes.router, prefix='/regional')
            with patch.object(routes, 'ROOT', ROOT), patch.object(routes, 'store', return_value=store), TestClient(app) as client:
                path = f"/regional/templates/{template['id']}"
                response = client.get(path, params=scope)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(sha256(response.content).hexdigest(), template['sha256'])
                self.assertEqual(client.get(path, params={**scope,'version':previous['version']}).status_code, 409)
                self.assertEqual(client.get(path, params={'province':'shaanxi','city':'宝鸡市','district':'扶风县'}).status_code, 404)
                query = {**scope, 'template_id': template['id'], 'kind': 'application'}
                self.assertEqual(client.get('/regional/form-contract', params=query).status_code, 409)
                self.assertEqual(client.post('/regional/generate', json={**query,'mode':'blank','data':{}}).status_code, 409)
                with patch.object(store, 'lookup', return_value={**guide, 'warnings': []}):
                    self.assertEqual(client.get(path, params=scope).status_code, 409)


    def test_reviewed_own_materials_do_not_promote_samples(self):
        from regional_baoji_county_application import staged_baoji_material_review_guide, staged_guide_without_generation

        with TemporaryDirectory() as work:
            store = RegionalStore(Path(work) / 'guide.sqlite')
            app = FastAPI()
            app.include_router(routes.router, prefix='/regional')
            with patch.object(routes, 'ROOT', ROOT), patch.object(routes, 'store', return_value=store), TestClient(app) as client:
                for code, expected in (
                    ('610324', '空表与样表下载件相同'),
                    ('610328', '授权委托书仅列样表入口'),
                    ('610305', '申请书和授权委托书仅列样表入口'),
                ):
                    with self.subTest(code=code):
                        before = store.put_guide(staged_guide_without_generation(code, ROOT))
                        current = store.put_guide(staged_baoji_material_review_guide(code, ROOT))
                        self.assertGreater(current['version'], before['version'])
                        self.assertEqual(current['source_id'], before['source_id'])
                        self.assertEqual(current['templates'], before['templates'])
                        self.assertEqual(current['materials'], before['materials'])
                        self.assertIn(expected, ' '.join(current['warnings']))
                        self.assertIn('证据目录', ' '.join(current['warnings']))
                        self.assertFalse(current['can_generate'])
                        scope = {key: current[key] for key in ('province', 'city', 'district')}
                        response = client.get('/regional/lookup', params=scope)
                        self.assertEqual(response.status_code, 200)
                        self.assertIn(expected, ' '.join(response.json()['warnings']))
                        versioned_scope = {**scope, 'source_id': current['source_id'], 'version': current['version']}
                        ids = [t['id'] for t in current['templates']] + [f'baoji-{code}-authorization']
                        for template_id in ids:
                            self.assertEqual(client.get(f'/regional/templates/{template_id}', params=versioned_scope).status_code, 404)
                            for kind in ('application', 'evidence'):
                                query = {**versioned_scope, 'template_id': template_id, 'kind': kind}
                                self.assertEqual(client.get('/regional/form-contract', params=query).status_code, 409)
                                self.assertEqual(client.post('/regional/generate', json={**query, 'mode':'blank', 'data':{}}).status_code, 409)
