"""Read-only contract / temporary HTTP fixtures; no project database access."""
from copy import deepcopy
import importlib.util
import json
import hashlib
from pathlib import Path
import sys
import tempfile
from io import BytesIO
import time
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
import zipfile

from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi import Response

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
from regional_guides import digest
from routes import regional_guides as route
from regional_guides import RegionalStore
from fastapi.responses import FileResponse


class RegionalFormContractTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('regional_form_contracts'),'Source-bound field contract module is required')
        import regional_form_contracts as contracts
        self.c=contracts
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve()
        local_route_root=patch.object(route,'ROOT',self.root);local_route_root.start();self.addCleanup(local_route_root.stop)
        self.check=patch.object(contracts,'checked_reference_adapter',side_effect=lambda g,t,k,**kw:t['adapter'])
        self.check.start();self.addCleanup(self.check.stop)
        self.proof=patch.object(contracts,'public_evidence',return_value={'fixture':True},create=True)
        self.proof.start();self.addCleanup(self.proof.stop)

    def guide(self,adapter='jiangsu_own_blank_oct29e_v1',kind='application',blank=True):
        original=self.root/'fixtures/own.docx';original.parent.mkdir(parents=True,exist_ok=True)
        original.write_bytes(b'own synthetic original')
        template={'id':'own-template','region_code':'320507','adapter':adapter,'can_generate':True,
                  'official_kind':'blank' if blank else 'sample','document_types':[kind],
                  'file':'fixtures/own.docx','sha256':hashlib.sha256(original.read_bytes()).hexdigest()}
        return {'province':'jiangsu','city':'苏州市','district':'相城区','region_code':'320507',
                'source_url':'https://fixture.gov.cn/own','source_id':digest('https://fixture.gov.cn/own')[:24],
                'version':207,'verification_status':'verified','templates':[template]}

    def build(self,adapter='jiangsu_own_blank_oct29e_v1',kind='application',blank=True):
        g=self.guide(adapter,kind,blank);return self.c.build_form_contract(g,g['templates'][0],kind,root=self.root)

    def field(self,contract,key):return next(f for f in contract['fields'] if f['key']==key)

    def test_exact_ejs_application_and_evidence_slots_without_wide_model_leak(self):
        app=self.build();self.assertEqual(len(app['fields']),28)
        self.assertIn('otherDocumentType',app['defaults']);self.assertNotIn('occupation',app['defaults'])
        self.assertEqual(self.field(app,'applicantName')['maxLength'],300)
        ev=self.build(kind='evidence');self.assertEqual(set(ev['defaults']),{'committeeName','caseNumber','submitDate','evidenceList'})
        self.assertEqual(len(self.field(ev,'evidenceList')['fields']),5);self.assertNotIn('copyCount',ev['defaults'])

    def test_zhejiang_worker_23_5_4_with_blank_defaults_and_ambiguous_choice_excluded(self):
        for adapter in ['zhejiang_own_worker_oct29d_v1','zhejiang_own_worker_oct29e_v1']:
            app=self.build(adapter);ev=self.build(adapter,'evidence')
            self.assertEqual(len(app['fields']),23);self.assertEqual(len(ev['fields']),5)
            self.assertEqual(len(self.field(ev,'evidenceList')['fields']),4)
            self.assertEqual(app['defaults']['birthDate'],'');self.assertEqual(app['defaults']['copyCount'],'')
            self.assertNotIn('外省非农业户口',self.field(app,'householdType')['choices'])

    def test_hunan_embedded_evidence_and_free_copy_slot(self):
        c=self.build('hunan_own_legacy_worker_oct29c_v1')
        self.assertEqual(len(c['fields']),27);self.assertNotIn('idNumber',c['defaults'])
        self.assertEqual(self.field(c,'factsReason')['maxLength'],1800)
        self.assertEqual(self.field(c,'requests')['maxItems'],8)
        self.assertEqual(self.field(c,'evidenceList')['maxItems'],10)
        self.assertEqual(len(self.field(c,'evidenceList')['fields']),3)
        data=self.c.validate_contract_data(c,{'copyCount':'按实际份数','requests':['  请求保留  ']})
        self.assertEqual(data['copyCount'],'按实际份数');self.assertEqual(data['requests'],['  请求保留  '])
        with self.assertRaises(ValueError):self.c.validate_contract_data(c,{'idNumber':''})

    def test_sichuan_reference_only_publishes_consumed_slots(self):
        c=self.build('sichuan_combined_reference_v1',blank=False)
        self.assertEqual(c['context']['mode'],'reference_adaptation')
        self.assertEqual(len(c['fields']),18);self.assertNotIn('copyCount',c['defaults']);self.assertNotIn('socialCreditCode',c['defaults'])
        ev=self.build('tianfu_reference_v1','evidence',False)
        self.assertEqual(set(ev['defaults']),{'evidenceList'})
        self.assertEqual({f['key'] for f in self.field(ev,'evidenceList')['fields']},{'name','itemCount','pageCount','originalType','purpose','notes'})

    def test_feidong_party_lines_and_display_width_capacity(self):
        c=self.build('anhui-feidong-official-application-20261029')
        self.assertEqual(set(c['defaults']),{'applicant_lines','agent_lines','respondent_lines','representative_lines','requests','facts'})
        self.assertEqual(self.field(c,'applicant_lines')['maxItems'],2)
        with self.assertRaises(ValueError):self.c.validate_contract_data(c,{'applicant_lines':['中'*21]})
        with self.assertRaises(ValueError):self.c.validate_contract_data(c,{'facts':'中'*281})

    def test_integer_copy_rules_and_legacy_blank_null(self):
        e=self.build();self.assertIsNone(self.c.validate_contract_data(e,{'copyCount':''})['copyCount'])
        for value in ['03',True,1.5,31]:
            with self.assertRaises(ValueError):self.c.validate_contract_data(e,{'copyCount':value})
        z=self.build('zhejiang_own_worker_oct29e_v1')
        self.assertEqual(self.c.validate_contract_data(z,{'copyCount':'03'})['copyCount'],'03')
        old=self.build('jiangsu_xishan_blank_v1')
        self.assertIsNone(self.c.validate_contract_data(old,{'copyCount':''})['copyCount'])
        self.assertNotIn('copyCount',self.build('jiangsu_xishan_blank_v1','evidence')['defaults'])

    def test_only_ejs_dates_are_iso_validated(self):
        c=self.build()
        self.assertEqual(self.field(c,'birthDate')['format'],'iso-date')
        for value in ['2025-02-29','1991/5/9','２０２６-01-01']:
            with self.assertRaises(ValueError):self.c.validate_contract_data(c,{'birthDate':value})
        self.assertEqual(self.c.validate_contract_data(c,{'birthDate':'2000-02-29'})['birthDate'],'2000-02-29')
        legacy=self.build('zhejiang_own_worker_oct29e_v1')
        self.assertNotIn('format',self.field(legacy,'birthDate'))

    def test_unknown_empty_fields_nested_unknown_xml_and_capacities_rejected(self):
        c=self.build(kind='evidence')
        for data in [{'unbound':''},{'evidenceList':[{'name':'ok','unbound':''}]},{'evidenceList':[{'name':'x\x00'}]},
                     {'evidenceList':[{'name':'x'*301}]},{'evidenceList':[{}]*41}]:
            with self.assertRaises(ValueError):self.c.validate_contract_data(c,data)
        value={'evidenceList':[{'name':'  中🙂  ','purpose':''}]}
        self.assertEqual(self.c.validate_contract_data(c,value),value)

    def test_context_hash_changes_with_scope_source_version_template_and_schema(self):
        g=self.guide();t=g['templates'][0];base=self.c.build_form_contract(g,t,'application',root=self.root)
        self.assertEqual(base['contract_id'],self.c.build_form_contract(deepcopy(g),deepcopy(t),'application',root=self.root)['contract_id'])
        for field,value in [('district','邻区'),('version',208),('source_id','different')]:
            changed=deepcopy(g);changed[field]=value
            self.assertNotEqual(base['contract_id'],self.c.build_form_contract(changed,t,'application',root=self.root)['contract_id'])
        changed=deepcopy(base);changed['fields'][0]['label']='Changed'
        with self.assertRaises(ValueError):self.c.validate_contract_data(changed,{})

    def test_no_data_unknown_adapter_and_failed_own_check_failclosed(self):
        for field,value in [('verification_status','unverified'),('version',None),('source_id','')]:
            g=self.guide();g[field]=value
            with self.assertRaises(ValueError):self.c.build_form_contract(g,g['templates'][0],'application',root=self.root)
        with self.assertRaises(ValueError):self.build('future_unknown_adapter')
        g=self.guide();g['templates'][0]['can_generate']=False
        with self.assertRaises(ValueError):self.c.build_form_contract(g,g['templates'][0],'application',root=self.root)
        with patch.object(self.c,'checked_reference_adapter',side_effect=ValueError('wrong own source')):
            with self.assertRaises(ValueError):self.build()

    def test_root_forwarded_and_explicit_empty_root_rejected(self):
        c=self.build();self.assertTrue(all(x.kwargs['root']==self.root for x in self.c.checked_reference_adapter.call_args_list))
        g=self.guide()
        for root in ['', '  ',self.root/'missing']:
            with self.assertRaises(ValueError):self.c.build_form_contract(g,g['templates'][0],'application',root=root)
        self.assertFalse(c['policy']['capacity_is_official_requirement'])
        self.assertEqual(c['policy']['unknown_fields'],'reject')

    def test_inventory_all_185_regions_364_document_pairs_have_explicit_profiles(self):
        rows=json.loads((ROOT/'data/public-regions/guides.json').read_text(encoding='utf8'))
        active=[g for g in rows if any(t.get('can_generate') for t in g['templates'])]
        adapters={t['adapter'] for g in active for t in g['templates'] if t.get('can_generate')}
        self.assertEqual(len(active),185)
        self.assertTrue(adapters.issubset(self.c.SUPPORTED_ADAPTERS))
        self.assertEqual(sum(len(t['document_types']) for g in active for t in g['templates'] if t.get('can_generate')),364)

    def test_http_contract_source_version_and_missing_template_failclosed(self):
        app=FastAPI();app.include_router(route.router,prefix='/api/regional-guides');client=TestClient(app);g=self.guide()
        query={k:g[k] for k in ['province','city','district','source_id','version']};query.update(template_id='own-template',kind='application')
        with patch.object(route,'store',return_value=type('Store',(),{'lookup':lambda s,*a:deepcopy(g)})()):
            response=client.get('/api/regional-guides/form-contract',params=query);self.assertEqual(response.status_code,200)
            for delta in [{'source_id':'wrong'},{'version':208},{'template_id':'other'},{'kind':'evidence'},{'district':'邻区'}]:
                self.assertEqual(client.get('/api/regional-guides/form-contract',params={**query,**delta}).status_code,409)

    def test_optional_bound_download_and_legacy_scope_only_return_own_bytes(self):
        app=FastAPI();app.include_router(route.router,prefix='/api/regional-guides');client=TestClient(app);g=self.guide();g['templates'][0].update(original_name='own.docx')
        original=self.root/g['templates'][0]['file'];own_sha=hashlib.sha256(original.read_bytes()).hexdigest()
        query={k:g[k] for k in ['province','city','district']}
        with patch.object(route,'store',return_value=type('Store',(),{'lookup':lambda s,*a:deepcopy(g)})()),patch('regional_public_provenance.approved_report_attachment',return_value=True):
            for extra in [{},{'source_id':g['source_id'],'version':207}]:
                response=client.get('/api/regional-guides/templates/own-template',params={**query,**extra})
                self.assertEqual(response.status_code,200);self.assertEqual(response.content,original.read_bytes())
                self.assertEqual(response.headers['x-guide-version'],'207');self.assertEqual(response.headers['x-template-sha256'],own_sha)
            for extra in [{'source_id':g['source_id']},{'version':207},{'source_id':'stale','version':207},{'source_id':g['source_id'],'version':208}]:
                self.assertEqual(client.get('/api/regional-guides/templates/own-template',params={**query,**extra}).status_code,409)
            original.write_bytes(b'changed original')
            self.assertEqual(client.get('/api/regional-guides/templates/own-template',params=query).status_code,409)

    def test_contract_id_generation_is_strict_without_changing_legacy_payloads(self):
        app=FastAPI();app.include_router(route.router,prefix='/api/regional-guides');client=TestClient(app)
        g=self.guide('tianfu_reference_v1',blank=False);t=g['templates'][0]
        contract=self.c.build_form_contract(g,t,'application',root=self.root)
        payload={k:g[k] for k in ['province','city','district','source_id','version']}
        payload.update(template_id=t['id'],kind='application',mode='reference_adaptation',data={'applicantName':'  虚构姓名  '})
        with patch.object(route,'store',return_value=type('Store',(),{'lookup':lambda s,*a:deepcopy(g)})()), \
             patch.object(route,'checked_reference_adapter',return_value='tianfu_reference_v1'), \
             patch.object(route,'checked_path',return_value=self.root/'fixture.docx'), \
             patch.object(route,'fill_tianfu_reference',return_value=object()) as fill, \
             patch.object(route,'_response',side_effect=lambda *a,**kw:Response(content=b'fixture generated')):
            response=client.post('/api/regional-guides/generate',json={**payload,'contract_id':contract['contract_id']})
            self.assertEqual(response.status_code,200);self.assertEqual(response.headers['x-guide-version'],'207')
            self.assertEqual(response.headers.get('x-form-contract-id'),contract['contract_id'])
            self.assertEqual(fill.call_args.args[2]['applicantName'],'虚构姓名')
            for delta,status in [({'contract_id':'0'*64},409),({'data':{'unbound':''}},422),({'data':{'applicantName':'x\x00'}},422)]:
                bad={**payload,'contract_id':contract['contract_id'],**delta}
                before=fill.call_count;rejected=client.post('/api/regional-guides/generate',json=bad)
                self.assertEqual(rejected.status_code,status);self.assertNotIn('x-form-contract-id',rejected.headers)
                self.assertEqual(fill.call_count,before)
            # Old unbound generic keys remain ignored on the old path.
            legacy=client.post('/api/regional-guides/generate',json={**payload,'data':{'unbound':''}})
            self.assertEqual(legacy.status_code,200);self.assertNotIn('x-form-contract-id',legacy.headers)

    def test_response_contract_binding_rejects_other_kind_same_source_version(self):
        app=FastAPI();app.include_router(route.router,prefix='/api/regional-guides');client=TestClient(app)
        g=self.guide('tianfu_reference_v1',blank=False);t=g['templates'][0];t['document_types']=['application','evidence']
        application=self.c.build_form_contract(g,t,'application',root=self.root)
        evidence=self.c.build_form_contract(g,t,'evidence',root=self.root)
        self.assertEqual(application['context']['source_id'],evidence['context']['source_id'])
        self.assertEqual(application['context']['version'],evidence['context']['version'])
        self.assertNotEqual(application['contract_id'],evidence['contract_id'])
        payload={k:g[k] for k in ['province','city','district','source_id','version']}
        payload.update(template_id=t['id'],kind='application',mode='reference_adaptation',data=application['defaults'])
        with patch.object(route,'store',return_value=type('Store',(),{'lookup':lambda s,*a:deepcopy(g)})()), \
             patch.object(route,'checked_reference_adapter',return_value='tianfu_reference_v1'), \
             patch.object(route,'checked_path',return_value=self.root/'fixture.docx'), \
             patch.object(route,'fill_tianfu_reference',return_value=object()) as fill, \
             patch.object(route,'_response',side_effect=lambda *a,**kw:Response(content=b'fixture generated')):
            wrong=client.post('/api/regional-guides/generate',json={**payload,'contract_id':evidence['contract_id']})
            self.assertEqual(wrong.status_code,409);self.assertNotIn('x-form-contract-id',wrong.headers);fill.assert_not_called()
            correct=client.post('/api/regional-guides/generate',json={**payload,'contract_id':application['contract_id']})
            self.assertEqual(correct.status_code,200)
            self.assertEqual(correct.headers.get('x-form-contract-id'),application['contract_id'])
            self.assertNotEqual(correct.headers.get('x-form-contract-id'),evidence['contract_id'])

    def test_feidong_unicode_layout_policy_matches_existing_width_for_raw_codepoints(self):
        c=self.build('anhui-feidong-official-application-20261029');layout=c['policy']['layout_limits']
        import unicodedata
        self.assertIn('unicode_version',layout)
        self.assertEqual(layout['unicode_version'],unicodedata.unidata_version)
        self.assertEqual(c['policy']['text_controls'],'newline_only')
        ranges=layout['wide_ranges'];self.assertTrue(all(a<=b and (i==0 or ranges[i-1][1]<a) for i,(a,b) in enumerate(ranges)))
        samples=['中','a','🙂','\u0301','\u0378','\U00031350']
        for sample in samples:
            width=2 if any(start<=ord(sample)<=end for start,end in ranges) else 1
            self.assertEqual(width,2 if unicodedata.east_asian_width(sample) in ('W','F') else 1)
        self.assertEqual(layout['fields']['applicant_lines']['line_widths'],[40,50])
        self.assertEqual(layout['fields']['requests']['max_lines'],9)
        for value in ['a\tb','a\rb']:
            with self.assertRaises(ValueError):self.c.validate_contract_data(c,{'facts':value})

    def test_malformed_contract_rejected_as_validation_error(self):
        for value in [{},{'schema_version':1}, {'schema_version':True}]:
            with self.assertRaises((ValueError,KeyError)) as caught:self.c.validate_contract_data(value,{})
            self.assertIsInstance(caught.exception,ValueError)

    def test_explicit_root_original_and_public_proof_cannot_fall_back(self):
        g=self.guide();t=g['templates'][0];empty=self.root/'empty';empty.mkdir()
        self.c.checked_reference_adapter.reset_mock()
        with self.assertRaises(ValueError):self.c.build_form_contract(g,t,'application',root=empty)
        self.assertEqual(self.c.checked_reference_adapter.call_count,0,'Do not read a historical implicit-root checker before root evidence exists')
        (self.root/t['file']).write_bytes(b'changed own original')
        with self.assertRaises(ValueError):self.c.build_form_contract(g,t,'application',root=self.root)
        g=self.guide();g['templates'][0]['file']='../outside.docx'
        with self.assertRaises(ValueError):self.c.build_form_contract(g,g['templates'][0],'application',root=self.root)
        g=self.guide()
        with patch.object(self.c,'public_evidence',return_value=None,create=True):
            with self.assertRaises(ValueError):self.c.build_form_contract(g,g['templates'][0],'application',root=self.root)

    def test_hunan_huge_numeric_copy_is_controlled_422_not_overflow_500(self):
        g=self.guide('hunan_own_legacy_worker_oct29c_v1');contract=self.c.build_form_contract(g,g['templates'][0],'application',root=self.root)
        app=FastAPI();app.include_router(route.router,prefix='/api/regional-guides');client=TestClient(app,raise_server_exceptions=False)
        payload={k:g[k] for k in ['province','city','district','source_id','version']}
        payload.update(template_id='own-template',kind='application',mode='blank',contract_id=contract['contract_id'],data={'copyCount':10**1000})
        self.assertLess(len(json.dumps(payload)),1800)
        with patch.object(route,'store',return_value=type('Store',(),{'lookup':lambda s,*a:deepcopy(g)})()),patch.object(route,'checked_reference_adapter',return_value='hunan_own_legacy_worker_oct29c_v1'):
            self.assertEqual(client.post('/api/regional-guides/generate',json=payload).status_code,422)


class RegionalFormRealSourceAcceptanceTests(unittest.TestCase):
    def test_all_185_regions_364_contract_bound_generations_from_temporary_store(self):
        """Real fillers/own proofs; only the DB and response staging are local fixtures."""
        runtime=(ROOT/'.runtime').resolve();runtime.mkdir(exist_ok=True)
        started=time.perf_counter();records=[]
        snapshot=json.loads((ROOT/'data/public-regions/guides.json').read_text(encoding='utf8'))
        active=[g for g in snapshot if any(t.get('can_generate') for t in g['templates'])]
        self.assertEqual(len(active),185)
        with tempfile.TemporaryDirectory(prefix='form-contract-http-',dir=runtime) as directory:
            temp_root=Path(directory).resolve();self.assertTrue(temp_root.is_relative_to(runtime))
            store=RegionalStore(temp_root/'regional-guides.sqlite')
            for g in active:store.put_guide(g)
            cases=[]
            for raw in active:
                g=store.lookup(raw['province'],raw['city'],raw['district'])
                for t in g['templates']:
                    if t.get('can_generate'):
                        cases.extend((g,t,kind) for kind in t['document_types'])
            typical=[];remaining=[];seen=set()
            for row in cases:
                key=(row[1]['adapter'],row[2])
                if key not in seen:typical.append(row);seen.add(key)
                else:remaining.append(row)
            self.assertEqual(len(typical),23);self.assertEqual(len(cases),364)
            app=FastAPI();app.include_router(route.router,prefix='/api/regional-guides');client=TestClient(app)
            def stage_response(document,filename,background_tasks):
                path=temp_root/('generated-'+str(len(records))+'.docx');document.save(path)
                background_tasks.add_task(path.unlink)
                return FileResponse(path,filename=filename,media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
            with patch.object(route,'store',return_value=store),patch.object(route,'_response',side_effect=stage_response), \
                 patch('socket.create_connection',side_effect=AssertionError('No network or model connection is allowed')):
                for g,t,kind in typical+remaining:
                    query={k:g[k] for k in ['province','city','district','source_id','version']}
                    query.update(template_id=t['id'],kind=kind)
                    contract_response=client.get('/api/regional-guides/form-contract',params=query)
                    self.assertEqual(contract_response.status_code,200,(g['region_code'],kind,contract_response.text))
                    contract=contract_response.json();payload={**query,'mode':contract['context']['mode'],
                        'contract_id':contract['contract_id'],'data':contract['defaults']}
                    response=client.post('/api/regional-guides/generate',json=payload)
                    self.assertEqual(response.status_code,200,(g['region_code'],kind,response.text[:300] if response.status_code!=200 else ''))
                    self.assertEqual(response.headers['x-guide-source-id'],g['source_id'])
                    self.assertEqual(response.headers['x-guide-version'],str(g['version']))
                    self.assertEqual(response.headers.get('x-form-contract-id'),contract['contract_id'])
                    with zipfile.ZipFile(BytesIO(response.content)) as archive:
                        self.assertIsNone(archive.testzip());xml=ET.fromstring(archive.read('word/document.xml'))
                        self.assertIsNotNone(xml.find('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}body'))
                    records.append({'region_code':g['region_code'],'kind':kind,'adapter':t['adapter'],'template_id':t['id'],
                        'source_id':g['source_id'],'temporary_store_version':g['version'],'contract_id':contract['contract_id'],
                        'x_form_contract_id':response.headers.get('x-form-contract-id'),
                        'http_status':200,'zip_integrity':'PASS','document_xml':'PASS','bytes':len(response.content),
                        'sha256':hashlib.sha256(response.content).hexdigest()})
        report={'status':'PASS','method':'in-process ASGI, real own-source checks and real document fillers',
            'regions':185,'document_pairs':364,'typical_profiles_first':23,'seconds':round(time.perf_counter()-started,3),
            'version_scope':'Sequences belong only to a new temporary SQLite fixture, not live source versions.',
            'main_database_opened':False,'model_network_connections_allowed':False,'word_rendering':'NOT_RUN',
            'native_browser_generation':False,'records':records}
        (runtime/'regional-form-contracts-asgi-acceptance.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')


if __name__=='__main__':unittest.main()
