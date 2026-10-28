"""A local adapter must reach the actual API without becoming a Sichuan sample."""
import copy,io,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from docx import Document
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'backend'))
from regional_adapters import with_reference_capabilities,checked_reference_adapter
from regional_guides import RegionalStore
from routes import regional_guides as routes

@unittest.skipUnless((ROOT / 'reports/nationwide-localization-20261028/zhejiang/SHA256-MANIFEST.json').is_file(),
                     'Local sealed capture contains login-flow context; not distributed in public checkout')
class ZhejiangDispatchTests(unittest.TestCase):
    def guide(self,code):return json.loads((ROOT/f'reports/nationwide-localization-20261028/zhejiang/staging-candidate/{code}-guide.json').read_text('utf8'))

    def test_shared_dispatch_recognizes_two_own_sources_and_clears_foreign_locality(self):
        for code in ['330110','330106']:
            guide=with_reference_capabilities(self.guide(code))
            for t in guide['templates']:
                if t.get('can_generate'):
                    self.assertEqual(checked_reference_adapter(guide,t,t['document_types'][0]),'zhejiang_own_blank_v1')
            swapped=copy.deepcopy(guide);swapped['district']='外地';changed=with_reference_capabilities(swapped)
            self.assertFalse(any(t.get('can_generate') for t in changed['templates']))
            swapped=copy.deepcopy(guide);swapped['province']='jiangsu'
            self.assertFalse(any(t.get('can_generate') for t in with_reference_capabilities(swapped)['templates']))

    def test_actual_route_fills_blank_and_rejects_sample_mode_and_wrong_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            store=RegionalStore(Path(temporary)/'isolated-public.sqlite')
            g=store.put_guide(with_reference_capabilities(self.guide('330110')))
            t=next(t for t in g['templates'] if t.get('document_types')==['evidence'])
            app=FastAPI();app.include_router(routes.router,prefix='/regional')
            payload={k:g[k] for k in ['province','city','district','source_id','version']}
            payload.update(template_id=t['id'],kind='evidence',mode='blank',data={'committeeName':'排版测试委员会','evidenceList':[{'name':'测试材料','purpose':'软件集成验证','pageCount':'3'}]})
            with patch.object(routes,'store',return_value=store),TestClient(app) as client:
                sample=next(t for t in g['templates'] if t['official_kind']=='sample')
                original=client.get('/regional/templates/'+sample['id'],params={k:g[k] for k in ['province','city','district']})
                self.assertEqual(original.status_code,200,original.text[:100] if original.status_code!=200 else '')
                self.assertTrue(original.content.startswith(b'\xff\xd8'))
                result=client.post('/regional/generate',json=payload)
                self.assertEqual(result.status_code,200,result.text[:250] if result.status_code!=200 else '')
                self.assertEqual(result.headers['X-Document-Origin'],'official-blank-filled')
                doc=Document(io.BytesIO(result.content));self.assertIn('测试材料',''.join(c.text for row in doc.tables[0].rows for c in row.cells))
                self.assertEqual(client.post('/regional/generate',json={**payload,'mode':'reference_adaptation'}).status_code,409)
                self.assertEqual(client.post('/regional/generate',json={**payload,'source_id':'foreign-source'}).status_code,409)
                app_template=next(t for t in g['templates'] if t.get('document_types')==['application'])
                result=client.post('/regional/generate',json={**payload,'template_id':app_template['id'],'kind':'application',
                    'data':{'applicantName':'测试','copyCount':'','evidenceCopyCount':''}})
                self.assertEqual(result.status_code,200,result.text[:200] if result.status_code!=200 else '')

if __name__=='__main__':unittest.main()
