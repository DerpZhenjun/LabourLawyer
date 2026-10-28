"""Independently captured Binhai/Xiangshui identity and original binding boundaries."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'backend'))
import regional_jiangsu
from regional_blank_documents import blank_binding
BASE=ROOT/'reports/nationwide-localization-20261028-next/jiangsu'
OWN={
 '320922':dict(parser='parse_binhai_capture',district='滨海县',host='ycbh.jszwfw.gov.cn',web='96',
  task='11320922014374388A400201430200201',agency='滨海县人力资源和社会保障局',
  address='滨海县人民路64号1-5楼;水务大厦304室综合窗口',phone='0515-84193055',complaint='0515-12333',visits='3',
  application='a0b76715-d491-4a89-8d3d-e08462f1f0f4',evidence='5008f178-fe89-4f89-9839-4b6b69eef95b'),
 '320921':dict(parser='parse_xiangshui_capture',district='响水县',host='ycxs.jszwfw.gov.cn',web='95',
  task='113209215754155300400201430200201',agency='响水县人力资源和社会保障局',
  address='江苏省盐城市响水县灌江路一号政务服务中心1楼12号窗口',phone='0515-86861920',complaint='0515-86862328',visits='0',
  application='cb2d28f4-a4d8-4633-9e89-238ebe8604ac',evidence='59d0356b-d251-4424-9a29-17f0491edc19')}
SHA={'application':'99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3',
     'evidence':'c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c'}

class BinhaiXiangshuiTests(unittest.TestCase):
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

    def test_own_fields_one_day_promise_and_different_visits_are_preserved(self):
        for code,spec in OWN.items():
            with self.subTest(code=code):
                g=self.parse(code)
                self.assertEqual((g['province'],g['city'],g['district'],g['region_code']),('jiangsu','盐城市',spec['district'],code))
                self.assertEqual((g['authority'],g['service_code']),(spec['agency'],spec['task']))
                for label,want in [('办理地点',spec['address']),('咨询方式',spec['phone']),('监督投诉方式',spec['complaint']),
                        ('法定办结时限','45个工作日'),('承诺办结时限','1个工作日'),('到办事现场次数',spec['visits'])]:
                    self.assertEqual(g['fields'][label]['raw_value'],want)
                self.assertIn('承诺办结时限原文为1个工作日',' '.join(g['warnings']))
                if code=='320921':self.assertNotIn('必须到现场原因',g['fields'])
                self.assertEqual([m['copies'] for m in g['materials']],['2','2','1','4'])
                self.assertEqual((len(g['sections']),len(g['templates'])),(12,8))
                self.assertEqual(g['channel']['online_status'],'unverified');self.assertIsNone(g['channel']['entry_url'])
                self.assertTrue(all(t['source_url']==g['source_url'] and t['region_code']==code and not t['can_generate'] for t in g['templates']))

    def test_foreign_host_task_item_web_kind_header_agency_and_cross_district_fail(self):
        for code,spec in OWN.items():
            self.parse(code)
            for key,old,new in [('url',spec['host'],'ycjh.jszwfw.gov.cn'),('url',spec['task'],'foreign-task'),
                ('url',spec['task'][:-2]+'&','foreign-item&'),('url','webId='+spec['web'],'webId=99'),
                ('url','ql_kind=20','ql_kind=01'),('html','class="area_local">'+spec['district'],'class="area_local">建湖县'),
                ('html',spec['task'],'foreign-task'),('html',spec['agency'],'建湖县人力资源和社会保障局')]:
                with self.subTest(code=code,key=key,old=old):
                    raw=self.raw(code);self.assertIn(old,raw[key]);raw[key]=raw[key].replace(old,new)
                    with self.assertRaises(ValueError):self.parse(code,raw)
            other='320921' if code=='320922' else '320922'
            with self.assertRaises(ValueError):self.parse(code,self.raw(other))

    def test_only_own_two_blank_originals_match_and_canonical_bytes_agree(self):
        for code,spec in OWN.items():
            g=self.downloaded(code)
            self.assertEqual({t['id']:blank_binding(g,t) for t in g['templates'] if blank_binding(g,t)},
                             {spec['application']:'application',spec['evidence']:'evidence'})
            for kind in ['application','evidence']:
                t=next(t for t in g['templates'] if t['id']==spec[kind])
                self.assertEqual(t['sha256'],SHA[kind]);self.assertEqual(hashlib.sha256((ROOT/t['file']).read_bytes()).hexdigest(),SHA[kind])

    def test_same_bytes_never_authorize_foreign_guide_or_annex(self):
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
