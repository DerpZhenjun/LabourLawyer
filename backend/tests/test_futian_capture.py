"""Futian's own old material FAQ must not become current province-wide requirements."""
import copy,importlib.util,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'backend'))
from regional_guides import RegionalStore
from routes.regional_guides import router
BASE=ROOT/'reports/nationwide-localization-20261023-night/cross-province/guangdong-futian'
class FutianCaptureTests(unittest.TestCase):
    def setUp(self):
        paths={'materials':'materials-channel-round25/materials/dom.json','jurisdiction':'articles-round25/jurisdiction/dom.json','query':'articles-round25/query/dom.json','channel':'channel-recovery-round25/channel/dom.json','entry':'online-boundary-round25/public-page.json','apply':'apply-click-round25/public-page.json'}
        self.raw={k:json.loads((BASE/p).read_text('utf8')) for k,p in paths.items()}
    def parse(self):
        self.assertIsNotNone(importlib.util.find_spec('regional_futian'),'Missing own multi-source Futian parser')
        from regional_futian import parse_futian_capture
        return parse_futian_capture(self.raw)
    def test_worker_materials_separate_employer_and_conditionals_keep_old_source_scope(self):
        g=self.parse();self.assertEqual((g['city'],g['district'],g['region_code']),('深圳市','福田区','440304'))
        self.assertEqual(len(g['materials']),8)
        self.assertEqual(g['materials'][1]['copies'],'按被申请人人数提供副本')
        self.assertEqual(g['materials'][3]['required'],'按情形提交')
        self.assertIn('委托',g['materials'][3]['applicable_conditions'])
        self.assertEqual([x['required'] for x in g['materials'][-2:]],['按情形提交','按情形提交'])
        self.assertTrue(all(x['verification_status']=='partial' and x['publication_date']=='2018-02-08' for x in g['materials']))
        self.assertTrue(all(x['source_url']==self.raw['materials']['url'] for x in g['materials']))
        self.assertNotIn('法定代表人或主要负责人身份证明书',[m['name'] for m in g['materials']])
        self.assertIn('申请人是用人单位',g['sections']['官方材料原文（含单位申请情形）'])
        self.assertEqual(g['fields']['办理地点']['verification_status'],'missing')
        self.assertIsNone(g['fields']['办理地点']['normalized_value'])
        self.assertEqual(g['templates'],[]);self.assertEqual(g['verification_status'],'partial')
        self.assertIn('2018', ' '.join(g['warnings']))
    def test_url_heading_source_or_row_identity_changes_fail_closed_not_footer_fallback(self):
        original=copy.deepcopy(self.raw)
        for key,field,old,new in [('materials','url','www.szft.gov.cn','www.by.gov.cn'),('materials','html','申请劳动人事争议仲裁须提交什么材料？','劳动争议调解材料'),('jurisdiction','html','福田区人力资源局','其他区人力资源局'),('materials','html','6</span>','7</span>')]:
            self.raw=copy.deepcopy(original);self.assertIn(old,self.raw[key][field]);self.raw[key][field]=self.raw[key][field].replace(old,new)
            with self.assertRaises(ValueError):self.parse()
        self.raw=copy.deepcopy(original);self.raw['materials']['html']=self.raw['materials']['html'].replace('</body>','<p>窗口地址：深圳市福田区福民路123号1409室；材料份数99份</p></body>')
        g=self.parse();self.assertIsNone(g['fields']['办理地点']['normalized_value']);self.assertNotIn('99份',str(g['materials']))
    def test_query_is_not_application_and_actual_error_never_becomes_verified_online_entry(self):
        g=self.parse();self.assertEqual(g['channel']['online_status'],'unverified');self.assertIsNone(g['channel']['entry_url'])
        self.assertEqual(g['fields']['办理形式']['verification_status'],'missing')
        self.assertTrue(g['online_evidence']['official_claim_includes_futian'])
        self.assertEqual(g['online_evidence']['actual_apply_result'],'ERR_EMPTY_RESPONSE')
        self.assertIn('福田区',g['sections']['网上办理来源与本次访问结果'])
        original=copy.deepcopy(self.raw)
        self.raw['channel']=copy.deepcopy(self.raw['query'])
        with self.assertRaises(ValueError):self.parse()
        self.raw=copy.deepcopy(original);self.raw['channel']['html']=self.raw['channel']['html'].replace('福田区、罗湖区','罗湖区');self.raw['channel']['html']=self.raw['channel']['html'].replace('</body>','<p>福田区</p></body>')
        with self.assertRaises(ValueError):self.parse()
        self.raw=copy.deepcopy(original);self.raw['entry']['url']='https://example.com/login'
        with self.assertRaises(ValueError):self.parse()
    def test_isolated_api_no_material_or_template_inheritance_to_neighbour(self):
        with tempfile.TemporaryDirectory() as d:
            s=RegionalStore(Path(d)/'public.sqlite');g=s.put_guide(self.parse())
            n=s.put_guide(json.loads((BASE.parent/'guangdong-nansha/guide.json').read_text('utf8')))
            self.assertNotEqual(g['source_id'],n['source_id']);self.assertNotEqual(g['materials'],n['materials'])
            app=FastAPI();app.include_router(router,prefix='/api/regional-guides')
            with patch('routes.regional_guides.store',return_value=s),TestClient(app) as client:
                params={k:g[k] for k in ['province','city','district']}
                own=client.get('/api/regional-guides/lookup',params=params).json();self.assertEqual(len(own['materials']),8)
                unknown=client.get('/api/regional-guides/lookup',params={**params,'district':'罗湖区'}).json();self.assertIsNone(unknown['source_id']);self.assertEqual(unknown['materials'],[])
                self.assertEqual(client.get('/api/regional-guides/templates/'+n['templates'][0]['id'],params=params).status_code,404)
                payload={k:g[k] for k in ['province','city','district','source_id','version']};payload.update(template_id=n['templates'][0]['id'],kind='application',mode='blank',data={})
                self.assertEqual(client.post('/api/regional-guides/generate',json=payload).status_code,409)
    def test_rechecking_clocks_alone_does_not_create_fake_requirement_revision(self):
        before=self.parse()
        for page in self.raw.values():page['captured_at']='2026-10-23T23:10:00.000Z'
        after=self.parse()
        with tempfile.TemporaryDirectory() as d:
            s=RegionalStore(Path(d)/'public.sqlite');a=s.put_guide(before);b=s.put_guide(after)
            self.assertEqual(a['version'],b['version'])
            self.assertEqual(b['verified_at'],'2026-10-23T23:10:00.000Z')
    def test_requirement_change_versions_without_replacing_original_material_clock(self):
        before=self.parse();self.raw['materials']['html']=self.raw['materials']['html'].replace('按被申请人人数提供副本','按被申请人人数提供副本，并提交电子版')
        self.raw['materials']['captured_at']='2026-10-23T23:00:00.000Z';after=self.parse()
        with tempfile.TemporaryDirectory() as d:
            s=RegionalStore(Path(d)/'public.sqlite');a=s.put_guide(before);b=s.put_guide(after)
            self.assertEqual(a['source_id'],b['source_id']);self.assertNotEqual(a['version'],b['version'])
            previous=s.versions('guangdong','深圳市','福田区')[1]
            self.assertNotIn('电子版',previous['materials'][1]['details']['官方原文'])
            self.assertEqual(previous['materials'][1]['collected_at'],before['materials'][1]['collected_at'])
            self.assertIn('电子版',b['materials'][1]['details']['官方原文'])
if __name__=='__main__':unittest.main()
