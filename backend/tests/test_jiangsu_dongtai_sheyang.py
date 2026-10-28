"""Own Dongtai/Sheyang source and blank provenance; no document generation."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'backend'))
import regional_jiangsu
from regional_blank_documents import blank_binding
BASE=ROOT/'reports/nationwide-localization-20261028/jiangsu'
OWN={
 '320981':dict(parser='parse_dongtai_capture',district='东台市',host='ycdt.jszwfw.gov.cn',web='100',
  task='11320981014396886W400201430200201',agency='盐城市东台市人力资源和社会保障局',
  address='东台市海陵南路32号;2号窗口',phone='0515-80960052',complaint='123333',
  application='d5a8d1f0-ba28-4fa3-8e0d-0c12fb5e8120',evidence='5d848c02-a62a-4686-9f25-2e320b1b32ae'),
 '320924':dict(parser='parse_sheyang_capture',district='射阳县',host='ycsy.jszwfw.gov.cn',web='98',
  task='11320924737070337G400201430200201',agency='射阳县人力资源和社会保障局',
  address='江苏省盐城市射阳县解放西路16号;射阳县解放西路16号2楼仲裁院办公室',phone='0515-82385486',complaint='0515-82310586',
  application='85e7e12b-18a8-458f-90f5-5a9ea44439a1',evidence='c3833b5a-b6ea-40aa-a3ff-905a50e83a4d')}
SHA={'application':'99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3',
     'evidence':'c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c'}

class DongtaiSheyangTests(unittest.TestCase):
    def raw(self,code):return json.loads((BASE/code/'formal-guide-final.json').read_text('utf8'))
    def parse(self,code,raw=None):
        parser=getattr(regional_jiangsu,OWN[code]['parser'],None)
        self.assertIsNotNone(parser,'Own district parser is missing: '+code)
        return parser(raw if raw is not None else self.raw(code))
    def downloaded(self,code):
        g=self.parse(code);ds={d['download_url']:d for d in json.loads((BASE/code/'downloads-manifest.json').read_text('utf8'))}
        for t in g['templates']:
            d=ds[t['download_url']];t.update(sha256=d['sha256'],download_status=d['download_status'],
                file=f"templates/_docx/_regional/{code}/{t['id']}-{d['original_name']}")
        return g

    # Prevent neighbour fallback and accidental correction of the own portal's 123333.
    def test_own_fields_materials_and_unverified_channel_are_preserved(self):
        for code,spec in OWN.items():
            with self.subTest(code=code):
                g=self.parse(code)
                self.assertEqual((g['province'],g['city'],g['district'],g['region_code']),('jiangsu','盐城市',spec['district'],code))
                self.assertEqual((g['authority'],g['service_code']),(spec['agency'],spec['task']))
                for label,want in [('办理地点',spec['address']),('咨询方式',spec['phone']),('监督投诉方式',spec['complaint']),('法定办结时限','45个工作日')]:
                    self.assertEqual(g['fields'][label]['raw_value'],want)
                self.assertEqual([m['copies'] for m in g['materials']],['2','2','1','4'])
                self.assertEqual((len(g['sections']),len(g['templates'])),(12,8))
                self.assertEqual(g['channel']['online_status'],'unverified');self.assertIsNone(g['channel']['entry_url'])
                self.assertTrue(all(t['source_url']==g['source_url'] and t['region_code']==code and not t['can_generate'] for t in g['templates']))

    # Reject a task-looking foreign URL or a foreign body behind an own URL.
    def test_changed_host_query_header_body_task_and_agency_are_rejected(self):
        for code,spec in OWN.items():
            self.parse(code)
            for key,old,new in [('url',spec['host'],'ycjh.jszwfw.gov.cn'),('url',spec['task'],'foreign-task'),
                ('url',spec['task'][:-2]+'&','foreign-item&'),('url','webId='+spec['web'],'webId=99'),
                ('url','ql_kind=20','ql_kind=01'),('html','class="area_local">'+spec['district'],'class="area_local">建湖县'),
                ('html',spec['task'],'foreign-task'),('html',spec['agency'],'建湖县人力资源和社会保障局')]:
                with self.subTest(code=code,key=key,old=old):
                    raw=self.raw(code);self.assertIn(old,raw[key]);raw[key]=raw[key].replace(old,new)
                    with self.assertRaises(ValueError):self.parse(code,raw)
            other='320924' if code=='320981' else '320981'
            with self.assertRaises(ValueError):self.parse(code,self.raw(other))

    # Portal blank labels must not authorize title-only evidence/ID placeholders.
    def test_only_own_application_and_evidence_blank_originals_match(self):
        for code,spec in OWN.items():
            g=self.downloaded(code)
            self.assertEqual({t['id']:blank_binding(g,t) for t in g['templates'] if blank_binding(g,t)},
                             {spec['application']:'application',spec['evidence']:'evidence'})
            for kind in ['application','evidence']:
                t=next(t for t in g['templates'] if t['id']==spec[kind])
                self.assertEqual(t['sha256'],SHA[kind]);self.assertEqual(hashlib.sha256((ROOT/t['file']).read_bytes()).hexdigest(),SHA[kind])

    # Reject equal bytes bound to a wrong region, source, task, agency or annex.
    def test_blank_binding_rejects_foreign_guide_and_template_provenance(self):
        for code,spec in OWN.items():
            g=self.downloaded(code);t=next(t for t in g['templates'] if t['id']==spec['application'])
            self.assertEqual(blank_binding(g,t),'application')
            for key,value in [('province','sichuan'),('city','南京市'),('district','建湖县'),('region_code','320925'),
                    ('source_url',g['source_url']+'&foreign=1'),('source_id','foreign'),('authority','foreign'),('service_code','foreign'),
                    ('verification_status','unverified')]:
                with self.subTest(code=code,guide=key):
                    changed=copy.deepcopy(g);changed[key]=value;self.assertIsNone(blank_binding(changed,t))
            for key,value in [('id','foreign'),('annex_id','foreign'),('region_code','320925'),('sha256','0'*64),
                    ('official_kind','sample'),('download_status','not_downloaded'),('source_url','https://foreign.example/'),
                    ('file',t['file'].replace('/'+code+'/','/320925/')),
                    ('download_url',t['download_url'].replace(t['id'],'00000000-0000-0000-0000-000000000000')),
                    ('download_url',t['download_url'].replace('sxgl.jszwfw.gov.cn:66','foreign.example'))]:
                with self.subTest(code=code,template=key):
                    changed=copy.deepcopy(t);changed[key]=value;self.assertIsNone(blank_binding(g,changed))

if __name__=='__main__':unittest.main()
