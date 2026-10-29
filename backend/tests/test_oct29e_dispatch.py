"""E exact own-source route dispatch; every SQLite store and applicant is synthetic."""
import io
from copy import deepcopy
from pathlib import Path
import tempfile,unittest
from unittest.mock import patch
from zipfile import ZipFile
from fastapi import FastAPI
from fastapi.testclient import TestClient
from regional_guides import RegionalStore
from regional_adapters import with_reference_capabilities
from regional_jiangsu_oct29e import parse_capture as js,ROOT
from regional_zhejiang_oct29e import parse_capture as zj,DATA_FIELDS
from regional_public_provenance import public_evidence,approved_report_attachment
from routes import regional_guides as routes

class EDispatchTests(unittest.TestCase):
    def test_four_own_regions_eight_routes_reject_cross_source_and_unpublished_material(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.runtime') as folder:
            store=RegionalStore(Path(folder)/'guides.sqlite')
            guides=[store.put_guide(with_reference_capabilities(g)) for g in [js('xiangcheng'),js('wujiang'),zj('fuyang'),zj('jiande')]]
            self.assertEqual([sum(t.get('can_generate') is True for t in g['templates']) for g in guides],[2,2,2,2])
            self.assertEqual(len({g['source_id'] for g in guides}),4)
            app=FastAPI();app.include_router(routes.router,prefix='/regional');count=0
            with patch.object(routes,'store',return_value=store),TestClient(app) as client:
                for g in guides:
                    self.assertIsNotNone(public_evidence(g,ROOT),g['district'])
                    for t in g['templates']:
                        if not t.get('can_generate'):continue
                        self.assertTrue(approved_report_attachment(g,t,ROOT))
                        kind=t['document_types'][0]
                        data={'applicantName':'虚构逐区验收人','requests':['请求支付虚构工资。'],'factsReason':'虚构逐区软件测试事实，非真实案件。'} if kind=='application' else {'evidenceList':[{'name':'虚构劳动合同','pageCount':'3','source':'虚构本人保存','purpose':'虚构说明关系。'}]}
                        payload={k:g[k] for k in ['province','city','district','source_id','version']};payload.update(template_id=t['id'],kind=kind,mode='blank',data=data)
                        response=client.post('/regional/generate',json=payload);self.assertEqual(response.status_code,200,response.text[:160] if response.status_code!=200 else '')
                        with ZipFile(io.BytesIO(response.content)) as archive:self.assertIsNone(archive.testzip())
                        self.assertEqual(response.headers['X-Guide-Source-ID'],g['source_id']);self.assertEqual(response.headers['X-Document-Origin'],'official-blank-filled');count+=1
                        wrong=deepcopy(payload);wrong['version']+=1;self.assertEqual(client.post('/regional/generate',json=wrong).status_code,409)
                        if g['province']=='jiangsu' and kind=='evidence':
                            wrong=deepcopy(payload);wrong['data']['copyCount']='';self.assertEqual(client.post('/regional/generate',json=wrong).status_code,422)
                        wrong=deepcopy(payload);wrong['source_id']=next(x['source_id'] for x in guides if x['source_id']!=g['source_id']);self.assertEqual(client.post('/regional/generate',json=wrong).status_code,409)
                        wrong=deepcopy(payload);wrong['data']['notInThisForm']='不应静默丢弃';self.assertEqual(client.post('/regional/generate',json=wrong).status_code,422)
                        original=client.get('/regional/templates/'+t['id'],params={k:g[k] for k in ['province','city','district']});self.assertEqual(original.status_code,200);self.assertEqual(original.content,(ROOT/t['file']).read_bytes())
            self.assertEqual(count,8)
            for g in guides:
                g.update(published=True,publication_status='published',candidate_web_qa='PASS')
                self.assertIsNotNone(public_evidence(g,ROOT))
                self.assertEqual(sum(t.get('can_generate') is True for t in with_reference_capabilities(g)['templates']),2)

    def test_exact_zhejiang_request_models_match_own_slots_and_limits(self):
        from regional_zhejiang_request import ApplicationRequest,EvidenceRequest,EvidenceItem
        self.assertEqual(set(ApplicationRequest.model_fields),set(DATA_FIELDS['application']))
        self.assertEqual(set(EvidenceRequest.model_fields),set(DATA_FIELDS['evidence']))
        self.assertEqual(set(EvidenceItem.model_fields),set(DATA_FIELDS['evidence_item']))
        self.assertEqual(ApplicationRequest.model_validate({'requests':['文'*1200]}).requests,['文'*1200])
        from pydantic import ValidationError
        for payload in [{'requests':['文'*1201]},{'applicantName':'文'*301},{'copyCount':31},{'unknown':''}]:
            with self.assertRaises(ValidationError):ApplicationRequest.model_validate(payload)
        self.assertEqual(ApplicationRequest.model_validate({'copyCount':''}).copyCount,'')

if __name__=='__main__':unittest.main()
