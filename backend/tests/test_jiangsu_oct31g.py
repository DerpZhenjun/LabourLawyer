"""Kunshan integration gates, real contracts/routes, isolated approvals and DB only."""
from copy import deepcopy
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))


class GIntegrationTests(unittest.TestCase):
    def setUp(self):
        import regional_jiangsu_oct31g as own
        self.own=own

    def approved_root(self):
        own=self.own;temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);root=Path(temp.name).resolve()
        paths=set(own.source_files(ROOT))|{own.SOURCE_FREEZE,own.WORD_MANIFEST}
        manifest=json.loads((ROOT/own.WORD_MANIFEST).read_bytes())
        paths.update(r['path'] for r in manifest['files'])
        for relative in paths:
            target=root/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/relative,target)
        proposal=json.loads((ROOT/own.STAGE_PROPOSAL).read_bytes())
        receipt={**proposal,'status':'approved_for_isolated_candidate_only','approved_by':'independent_root',
                 'visual_review':'PASS','can_publish':False}
        raw=(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n').encode()
        (root/own.STAGE_RECEIPT).write_bytes(raw)
        return root,sha256(raw).hexdigest()

    def assert_typescript(self,mode,payload):
        # Execute the existing production parser/presentation, without replacing
        # its validation or asserting network JSON into a TypeScript type.
        fixture=ROOT/'scripts/test-kunshan-guide-wire.mjs'
        run=subprocess.run(['node',str(fixture)],input=json.dumps({**payload,'mode':mode},ensure_ascii=False),
            cwd=ROOT,capture_output=True,text=True,encoding='utf-8',timeout=30)
        self.assertEqual(run.returncode,0,run.stderr)

    def test_lookup_inventory_and_forms_pass_unchanged_typescript_wire_parser(self):
        own=self.own;root,pin=self.approved_root()
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from regional_guides import RegionalStore
        from routes import regional_guides as routes
        with patch.object(own,'STAGE_SHA256',pin),patch.object(own,'ROOT',root),patch.object(routes,'ROOT',root):
            store=RegionalStore(root/'wire.sqlite');g=store.put_guide(own.prepare_candidate(root=root))
            app=FastAPI();app.include_router(routes.router,prefix='/regional')
            with patch.object(routes,'store',return_value=store),TestClient(app) as client:
                region={k:g[k] for k in ['province','city','district']}
                lookup=client.get('/regional/lookup',params=region);inventory=client.get('/regional/inventory')
                self.assertEqual(lookup.status_code,200);self.assertEqual(inventory.status_code,200)
                forms=[]
                for kind in ['application','evidence']:
                    query={**region,'source_id':g['source_id'],'version':g['version'],'template_id':own.ANNEX[kind],'kind':kind}
                    response=client.get('/regional/form-contract',params=query);self.assertEqual(response.status_code,200)
                    forms.append(response.json())
                self.assert_typescript('wire',{'lookup':lookup.json(),'inventory':inventory.json(),'region':region,'forms':forms})

    def test_own_fact_projection_passes_actual_display_without_hiding_copies(self):
        own=self.own;guide=own.parse_capture(root=ROOT);source=own._source_guide(ROOT)
        expected_copies=[int(m['details']['纸质材料份数']) for m in source['materials']]
        self.assert_typescript('display',{'guide':guide,'fields':source['fields'],'copies':expected_copies,
            'originals':[m['details']['材料类型'] for m in source['materials']],
            'required':[m['details']['材料必要性'] for m in source['materials']],
            'formats':[m['details']['材料形式'] for m in source['materials']]})
        for name,value in source['fields'].items():
            self.assertEqual(guide['fields'][name],{'raw_value':value,'normalized_value':value.strip(),
                'source_url':guide['source_url'],'region_code':'320583','collected_at':guide['collected_at'],
                'verified_at':guide['verified_at'],'verification_status':'verified'})
        capture=json.loads((ROOT/own.FOLDER.rsplit('/',1)[0]/'own-guide.json').read_bytes())
        self.assertEqual(guide['sections'],{'本区公开办事指南原文':capture['text']})

    def test_raw_source_false_no_implicit_stage_or_publication(self):
        own=self.own
        from regional_adapters import with_reference_capabilities
        from regional_public_provenance import public_evidence
        raw=own.parse_capture(root=ROOT)
        self.assertFalse(raw['can_generate']);self.assertFalse(raw['published'])
        self.assertTrue(all(not t['can_generate'] for t in raw['templates']))
        self.assertEqual(with_reference_capabilities(raw,ROOT),raw)
        self.assertIsNotNone(public_evidence(raw,ROOT))
        if own.STAGE_SHA256 is not None:
            staged=own.prepare_candidate(root=ROOT)
            self.assertTrue(staged['can_generate']);self.assertFalse(staged['published'])
            self.assertFalse(own.with_capabilities(raw,root=ROOT)['can_generate'])
        with patch.object(own,'STAGE_SHA256',None),patch.object(own,'PUBLICATION_SHA256',None):
            self.assertEqual(own.with_capabilities(raw,root=ROOT),raw)
            with self.assertRaises(ValueError):own.prepare_candidate(root=ROOT)
            with self.assertRaises(ValueError):own.with_publication_evidence(raw,root=ROOT)

    def test_sealed_word_functions_keep_reviewed_outputs_identical(self):
        own=self.own
        fixtures=json.loads((ROOT/own.QA_REPORT/'word/fictional-fixtures.json').read_bytes())
        for name,data in fixtures.items():
            kind='application' if name.startswith('application') else 'evidence'
            actual=own.fill_offline(kind,data,root=ROOT);buf=BytesIO();actual.save(buf)
            with ZipFile(buf) as result,ZipFile(ROOT/own.QA_REPORT/'word'/f'{name}.docx') as reviewed:
                self.assertEqual(result.namelist(),reviewed.namelist())
                for member in reviewed.namelist():self.assertEqual(result.read(member),reviewed.read(member),name+' '+member)

    def test_receipt_and_source_tamper_fail_closed_without_private_fallback(self):
        own=self.own;root,pin=self.approved_root()
        from regional_public_provenance import public_evidence
        with patch.object(own,'STAGE_SHA256',pin):
            g=own.prepare_candidate(root=root);self.assertIsNotNone(public_evidence(g,root))
            for absent in [None,'',' ']:self.assertIsNone(public_evidence(g,absent))
            receipt=(root/own.STAGE_RECEIPT).read_bytes()
            (root/own.STAGE_RECEIPT).write_text('{}')
            self.assertIsNone(public_evidence(g,root))
            with self.assertRaises(ValueError):own.prepare_candidate(root=root)
            (root/own.STAGE_RECEIPT).write_bytes(receipt)
            original=root/next(t['file'] for t in g['templates'] if t.get('document_types')==['application'])
            original.write_bytes(original.read_bytes()+b'tamper')
            self.assertIsNone(public_evidence(g,root))
            with self.assertRaises(ValueError):own.prepare_candidate(root=root)

    def test_candidate_bindings_reject_source_fields_annex_samples_flags_and_version_types(self):
        own=self.own;root,pin=self.approved_root()
        with patch.object(own,'STAGE_SHA256',pin):
            g=own.prepare_candidate(root=root)
            for key,value in [('region_code','320581'),('district','常熟市'),('source_id','wrong'),
                              ('authority','邻区机关'),('can_generate',1),('version',True)]:
                bad=deepcopy(g);bad[key]=value
                with self.subTest(key=key),self.assertRaises(ValueError):own.with_capabilities(bad,root=root)
            t=next(t for t in g['templates'] if t.get('document_types')==['application'])
            for key,value in [('id','foreign'),('sha256','0'*64),('official_kind','sample'),('region_code','320582')]:
                bad=deepcopy(t);bad[key]=value
                with self.subTest(key=key),self.assertRaises(ValueError):own.checked_adapter(g,bad,'application',root=root)
            with self.assertRaises((ValueError,OSError)):own.with_publication_evidence(g,root=root)

    def test_marker_preserves_existing_release_and_f_pins(self):
        from routes.regional_guides import release_capabilities
        import regional_jiangsu_oct30f as f
        marker=release_capabilities()
        self.assertEqual(marker['release_id'],'oct30night-own-localities-v1')
        self.assertIn(f.ADAPTER,marker['adapters'])
        self.assertEqual(marker['candidate_stage_receipts'][f.ADAPTER],f.STAGE_SHA256)
        self.assertEqual(marker['publication_receipts'][f.ADAPTER],f.PUBLICATION_SHA256)
        self.assertIn(self.own.ADAPTER,marker['adapters'])
        self.assertEqual(marker['candidate_stage_receipts'][self.own.ADAPTER],self.own.STAGE_SHA256)
        self.assertEqual(marker['publication_receipts'][self.own.ADAPTER],self.own.PUBLICATION_SHA256)

    def test_own_request_version_is_not_coerced(self):
        from routes.regional_guides import GenerateRequest
        from pydantic import ValidationError
        raw={'province':'jiangsu','city':'苏州市','district':'昆山市','source_id':self.own.SOURCE_ID,
             'version':1,'template_id':self.own.ANNEX['application'],'kind':'application','mode':'blank','data':{}}
        self.assertEqual(GenerateRequest.model_validate(raw).version,1)
        for version in [True,'1',1.0,0,-1]:
            with self.subTest(version=version),self.assertRaises(ValidationError):
                GenerateRequest.model_validate({**raw,'version':version})
        self.assertEqual(GenerateRequest.model_validate({**raw,'source_id':'legacy','version':'1'}).version,1)

    def test_real_contract_routes_and_all_negative_contexts_in_temporary_store(self):
        own=self.own;root,pin=self.approved_root()
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from regional_guides import RegionalStore
        from routes import regional_guides as routes
        from regional_form_contracts import SUPPORTED_ADAPTERS,PUBLIC_PROOF_ADAPTERS
        self.assertIn(own.ADAPTER,SUPPORTED_ADAPTERS);self.assertIn(own.ADAPTER,PUBLIC_PROOF_ADAPTERS)
        with patch.object(own,'STAGE_SHA256',pin),patch.object(own,'ROOT',root),patch.object(routes,'ROOT',root):
            store=RegionalStore(root/'candidate.sqlite');g=store.put_guide(own.prepare_candidate(root=root))
            app=FastAPI();app.include_router(routes.router,prefix='/regional')
            with patch.object(routes,'store',return_value=store),TestClient(app) as client:
                for kind in ['application','evidence']:
                    t=next(t for t in g['templates'] if t.get('document_types')==[kind])
                    query={k:g[k] for k in ['province','city','district','source_id','version']}
                    query.update(template_id=t['id'],kind=kind)
                    response=client.get('/regional/form-contract',params=query)
                    self.assertEqual(response.status_code,200,response.text)
                    contract=response.json();self.assertEqual(len(contract['fields']),28 if kind=='application' else 4)
                    self.assertIs(contract['policy']['trim_text'],True)
                    if kind=='evidence':
                        self.assertEqual(len(contract['defaults']['evidenceList']),1)
                        items=next(f for f in contract['fields'] if f['key']=='evidenceList')['fields']
                        self.assertEqual(next(f for f in items if f['key']=='originalType')['choices'],['原件','复印件'])
                    payload={**query,'mode':'blank','contract_id':contract['contract_id'],'data':{}}
                    data={'applicantName':'虚构甲','respondentName':'虚构单位','requests':['虚构请求'],'factsReason':'仅供测试。'} if kind=='application' else {'evidenceList':[{'name':'虚构证据','purpose':'仅供测试'}]}
                    for draft in [{},contract['defaults'],data]:
                        response=client.post('/regional/generate',json={**payload,'data':draft})
                        self.assertEqual(response.status_code,200,response.text if response.status_code!=200 else '')
                        self.assertEqual(response.headers['X-Document-Origin'],'official-blank-filled')
                        self.assertEqual(response.headers['X-Form-Contract-ID'],contract['contract_id'])
                        with ZipFile(BytesIO(response.content)) as archive:self.assertIsNone(archive.testzip())
                    for change in [{'source_id':'foreign'},{'version':g['version']+10},{'district':'常熟市'},
                                   {'template_id':'foreign'},{'contract_id':'0'*64},{'mode':'reference_adaptation'}]:
                        self.assertEqual(client.post('/regional/generate',json={**payload,**change}).status_code,409)
                    invalids=[{'unknown':''},{'copyCount':True},{'applicationDate':'2026-02-30'},{'acceptMediation':'自动同意'}] if kind=='application' else [{'evidenceList':[{}]*41},{'evidenceList':[{'unknown':''}]},{'evidenceList':[{'originalType':'自动认定'}]}]
                    for invalid in invalids:self.assertEqual(client.post('/regional/generate',json={**payload,'data':invalid}).status_code,422)
                    download=client.get('/regional/templates/'+t['id'],params={k:g[k] for k in ['province','city','district','source_id','version']})
                    self.assertEqual(download.status_code,200)
                    self.assertEqual(sha256(download.content).hexdigest(),t['sha256'])
                heading=next(t for t in g['templates'] if t['content_role']=='heading_only_copy_placeholder')
                self.assertEqual(client.post('/regional/generate',json={**payload,'template_id':heading['id']}).status_code,409)


if __name__=='__main__':unittest.main()
