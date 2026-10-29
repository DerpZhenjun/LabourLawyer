"""New Jiangsu/Feidong own-source dispatch in a synthetic isolated test DB."""
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from docx import Document
from fastapi import FastAPI
from fastapi.testclient import TestClient
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'backend'))
from regional_guides import RegionalStore
from regional_adapters import with_reference_capabilities
from regional_anhui_oct29 import load_guide
from routes import regional_guides as routes


class OctoberDispatchTests(unittest.TestCase):
    def test_publication_metadata_does_not_change_official_source_authorization(self):
        from regional_zhejiang_oct29 import parse_capture
        cases=[parse_capture('haishu'),parse_capture('yinzhou'),load_guide('feidong')]
        for g in cases:
            g=with_reference_capabilities(g)
            expected=sum(t.get('can_generate') is True for t in g['templates'])
            g.update(published=True,publication_status='published',candidate_web_qa='PASS',can_generate=True)
            result=with_reference_capabilities(g)
            self.assertEqual(sum(t.get('can_generate') is True for t in result['templates']),expected,g['district'])
            changed=__import__('copy').deepcopy(g);changed['authority']='其他机关'
            self.assertFalse(any(t.get('can_generate') for t in with_reference_capabilities(changed)['templates']))

    def test_jiangsu_own_blanks_use_shared_route_and_download_without_cross_county_reuse(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.runtime') as folder:
            store=RegionalStore(Path(folder)/'guides.sqlite')
            guides=[store.put_guide(with_reference_capabilities(json.loads((ROOT/f'reports/nationwide-verification-20261029/jiangsu/{code}/guide.json').read_text('utf-8')))) for code in ['320281','320282']]
            self.assertNotEqual(guides[0]['source_id'],guides[1]['source_id'])
            app=FastAPI();app.include_router(routes.router,prefix='/regional')
            with patch.object(routes,'store',return_value=store),TestClient(app) as client:
                for g in guides:
                    self.assertEqual(sum(t.get('can_generate') is True for t in g['templates']),2)
                    for kind in ['application','evidence']:
                        t=next(t for t in g['templates'] if t.get('document_types')==[kind])
                        data={'applicantName':'虚构批次劳动者','requests':['请求支付虚构工资。'],'copyCount':'','evidenceCopyCount':''} if kind=='application' else {'evidenceList':[{'name':'虚构批次证据','source':'虚构来源','purpose':'测试来源绑定','pageCount':'2'}]}
                        payload={k:g[k] for k in ['province','city','district','source_id','version']};payload.update(template_id=t['id'],kind=kind,mode='blank',data=data)
                        r=client.post('/regional/generate',json=payload);self.assertEqual(r.status_code,200,r.text[:100] if r.status_code!=200 else '')
                        self.assertEqual(r.headers['X-Document-Origin'],'official-blank-filled')
                        r=client.get('/regional/templates/'+t['id'],params={k:g[k] for k in ['province','city','district']});self.assertEqual(r.status_code,200)
                        self.assertEqual(r.content,(ROOT/t['file']).read_bytes())
                        payload['source_id']=next(x['source_id'] for x in guides if x['source_id']!=g['source_id'])
                        self.assertEqual(client.post('/regional/generate',json=payload).status_code,409)

    def test_feidong_shared_route_has_own_form_contract_and_preserves_every_input_character(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.runtime') as folder:
            store=RegionalStore(Path(folder)/'guides.sqlite');g=store.put_guide(with_reference_capabilities(load_guide('feidong')))
            app=FastAPI();app.include_router(routes.router,prefix='/regional')
            with patch.object(routes,'store',return_value=store),TestClient(app) as client:
                self.assertEqual(sum(t.get('can_generate') is True for t in g['templates']),1)
                t=next(t for t in g['templates'] if t.get('can_generate'))
                payload={k:g[k] for k in ['province','city','district','source_id','version']}
                payload.update(template_id=t['id'],kind='application',mode='blank',data={'applicant_lines':['虚构劳动者，女，三十岁','肥东虚构路一号'], 'respondent_lines':['虚构单位','肥东虚构路二号'],'requests':['请求支付虚构工资。'],'facts':'虚构案情，用于本地软件验证。'})
                r=client.post('/regional/generate',json=payload);self.assertEqual(r.status_code,200,r.text[:200] if r.status_code!=200 else '')
                text='\n'.join(p.text for p in Document(io.BytesIO(r.content)).paragraphs)
                self.assertIn('虚构劳动者',text);self.assertIn('虚构案情，用于本地软件验证。',text)
                payload['data']['facts']='字'*281
                self.assertEqual(client.post('/regional/generate',json=payload).status_code,409)
                payload['data']={'applicantName':'不应被悄悄忽略的字段'}
                self.assertEqual(client.post('/regional/generate',json=payload).status_code,422)
                self.assertFalse(any(t.get('can_generate') for t in with_reference_capabilities(load_guide('yaohai'))['templates']))


if __name__=='__main__':unittest.main()
