"""C4 shared routes use each own source, including after publication."""
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile
from fastapi import FastAPI
from fastapi.testclient import TestClient
from regional_guides import RegionalStore
from regional_adapters import with_reference_capabilities
from regional_hunan_oct29c import parse_capture as hunan,ROOT
from regional_jiangsu_oct29c import parse_capture as jiangsu
from routes import regional_guides as routes


class CDispatchTests(unittest.TestCase):
    def test_hunan_request_strings_are_not_limited_by_ordinary_field_capacity(self):
        text='虚构请求'*50
        data=routes.HunanApplicationRequest.model_validate({'requests':[text]})
        self.assertEqual(data.requests,[text])
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            routes.HunanApplicationRequest.model_validate({'applicantName':'文'*161})

    def test_four_own_guides_six_generation_routes_and_cross_source_rejection(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.runtime') as folder:
            store=RegionalStore(Path(folder)/'guides.sqlite')
            originals=[hunan('yuhua'),hunan('wangcheng'),jiangsu('xinbei'),jiangsu('wujin')]
            guides=[store.put_guide(with_reference_capabilities(g)) for g in originals]
            self.assertEqual(len({g['source_id'] for g in guides}),4)
            app=FastAPI();app.include_router(routes.router,prefix='/regional');generated=0
            with patch.object(routes,'store',return_value=store),TestClient(app) as client:
                for g in guides:
                    self.assertEqual(sum(t.get('can_generate') is True for t in g['templates']),1 if g['province']=='hunan' else 2)
                    for t in g['templates']:
                        if not t.get('can_generate'):continue
                        for kind in t['document_types']:
                            data={'applicantName':'虚构C区验收劳动者','requests':['请求支付虚构工资。'],'factsReason':'虚构C区软件验收事实。'} if kind=='application' else {'evidenceList':[{'name':'虚构C区证据','source':'虚构来源','purpose':'虚构证明事项'}]}
                            payload={k:g[k] for k in ['province','city','district','source_id','version']};payload.update(template_id=t['id'],kind=kind,mode='blank',data=data)
                            r=client.post('/regional/generate',json=payload);self.assertEqual(r.status_code,200,r.text[:150] if r.status_code!=200 else '')
                            with ZipFile(io.BytesIO(r.content)) as z:self.assertIsNone(z.testzip())
                            self.assertEqual(r.headers['X-Guide-Source-ID'],g['source_id']);generated+=1
                            original=client.get('/regional/templates/'+t['id'],params={k:g[k] for k in ['province','city','district']})
                            self.assertEqual(original.status_code,200);self.assertEqual(original.content,(ROOT/t['file']).read_bytes())
                            payload['source_id']=next(x['source_id'] for x in guides if x['source_id']!=g['source_id'])
                            self.assertEqual(client.post('/regional/generate',json=payload).status_code,409)
                            if g['province']=='hunan':
                                payload['source_id']=g['source_id'];payload['data']['idNumber']='没有原件槽的字段不能丢弃'
                                self.assertEqual(client.post('/regional/generate',json=payload).status_code,422)
                self.assertEqual(generated,6)
            for g in guides:
                g.update(published=True,publication_status='published',candidate_web_qa='PASS')
                self.assertEqual(sum(t.get('can_generate') is True for t in with_reference_capabilities(g)['templates']),1 if g['province']=='hunan' else 2)


if __name__=='__main__':unittest.main()
