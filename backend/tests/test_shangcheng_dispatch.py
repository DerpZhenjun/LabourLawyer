"""An own-source candidate reaches real filling routes only in an isolated test DB."""
import copy,io,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from docx import Document
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'backend'))
from regional_adapters import with_reference_capabilities
from regional_zhejiang_more import parse_shangcheng_capture
from regional_guides import RegionalStore
from routes import regional_guides as routes
REPORT=ROOT/'reports/nationwide-localization-20261028-next/zhejiang'

@unittest.skipUnless((REPORT/'SOURCE-MANIFEST.json').is_file(),'Local sealed login-flow capture is not distributed publicly')
class ShangchengDispatchTests(unittest.TestCase):
    def test_only_own_source_is_enabled_and_actual_route_keeps_blank_origins(self):
        g=with_reference_capabilities(parse_shangcheng_capture(REPORT,REPORT/'SOURCE-MANIFEST.json'))
        self.assertEqual(sum(bool(t.get('can_generate')) for t in g['templates']),2)
        bad=copy.deepcopy(g);bad['district']='滨江区'
        self.assertFalse(any(t.get('can_generate') for t in with_reference_capabilities(bad)['templates']))
        with tempfile.TemporaryDirectory() as tmp:
            store=RegionalStore(Path(tmp)/'public-test.sqlite');g=store.put_guide(g)
            app=FastAPI();app.include_router(routes.router,prefix='/regional')
            with patch.object(routes,'store',return_value=store),TestClient(app) as client:
                for kind,data in [('application',{'applicantName':'上城虚构测试','requests':['测试请求'],'copyCount':''}),('evidence',{'caseNumber':'仅用于软件验证','evidenceList':[{'name':'独立来源材料','purpose':'软件验证','source':'虚构','pageCount':'3'}]})]:
                    t=next(t for t in g['templates'] if t['document_types']==[kind])
                    payload={k:g[k] for k in ['province','city','district','source_id','version']}
                    payload.update(template_id=t['id'],kind=kind,mode='blank',data=data)
                    r=client.post('/regional/generate',json=payload)
                    self.assertEqual(r.status_code,200,r.text[:200] if r.status_code!=200 else '')
                    self.assertEqual(r.headers['X-Document-Origin'],'official-blank-filled')
                    self.assertEqual(r.headers['X-Guide-Source-ID'],g['source_id'])
                    text=''.join(c.text for table in Document(io.BytesIO(r.content)).tables for row in table.rows for c in row.cells)
                    self.assertIn(data.get('applicantName','独立来源材料'),text)
