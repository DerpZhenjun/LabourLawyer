"""Own Yandu/Tinghu boundaries: equal blank bytes never authorize a neighbour."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
import regional_jiangsu
from regional_blank_documents import blank_binding

BASE=ROOT/'reports/nationwide-localization-20261028/jiangsu'
OWN={
    '320903':{'parser':'parse_yandu_capture','district':'盐都区','host':'ycyd.jszwfw.gov.cn','web':'93',
              'agency':'盐城市盐都区人力资源与社会保障局','task':'11320928562941566D400201430200201',
              'address':'盐城市盐都区鹿鸣路449号，盐都区综治中心二楼，劳动保障维权窗口','phone':'0515—88332406',
              'application':'73bc8138-5dba-4b3f-ae15-9f8d3f90b717','evidence':'c99c9cba-a1f6-4107-9084-45adbb9002da'},
    '320902':{'parser':'parse_tinghu_capture','district':'亭湖区','host':'ycth.jszwfw.gov.cn','web':'92',
              'agency':'盐城市亭湖区人力资源和社会保障局','task':'11320902014360656E400201430200201',
              'address':'盐城市人民中路76号;案件审理室','phone':'0515-88243719',
              'application':'b2ef8a79-637b-4c49-bbbd-82f0082c2bbf','evidence':'103d2584-4128-49dc-a177-72bb3904afa2'},
}
SHA={'application':'99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3',
     'evidence':'c40d42c03b2881fa25144ba895132befbbd23c92b76469dc5a1bc7dd69eefe8c'}


class NewJiangsuLocalityTests(unittest.TestCase):
    def capture(self,code):return json.loads((BASE/code/'formal-guide-final.json').read_text('utf8'))

    def parse(self,code,raw=None):
        parser=getattr(regional_jiangsu,OWN[code]['parser'],None)
        self.assertIsNotNone(parser,'Own locality parser is missing: '+code)
        return parser(raw if raw is not None else self.capture(code))

    def downloaded_guide(self,code):
        g=self.parse(code)
        downloads=json.loads((BASE/code/'classified-annexes.json').read_text('utf8'))
        by_url={x['download_url']:x for x in downloads}
        for t in g['templates']:
            d=by_url[t['download_url']]
            t.update(sha256=d['sha256'],download_status=d['download_status'],original_name=d['original_name'],
                     classification=d['classification'],file=f"templates/_docx/_regional/{code}/{t['id']}-{d['original_name']}")
        return g

    # Break caught: accidental locality fallback or loss of own raw agency/address/copies.
    def test_each_parser_retains_own_requirements_and_unverified_online_status(self):
        for code,spec in OWN.items():
            with self.subTest(code=code):
                g=self.parse(code)
                self.assertEqual((g['province'],g['city'],g['district'],g['region_code']),('jiangsu','盐城市',spec['district'],code))
                self.assertEqual(g['authority'],spec['agency']);self.assertEqual(g['service_code'],spec['task'])
                self.assertEqual(g['fields']['办理地点']['raw_value'],spec['address'])
                self.assertEqual(g['fields']['咨询方式']['raw_value'],spec['phone'])
                self.assertEqual(g['fields']['法定办结时限']['raw_value'],'45个工作日')
                self.assertEqual([x['copies'] for x in g['materials']],['2','2','1','4'])
                self.assertEqual(len(g['templates']),8);self.assertEqual(len(g['sections']),12)
                self.assertEqual(g['channel']['online_status'],'unverified');self.assertIsNone(g['channel']['entry_url'])
                self.assertTrue(all(t['region_code']==code and t['source_url']==g['source_url'] and not t['can_generate'] for t in g['templates']))
                blanks={t['id'] for t in g['templates'] if t['official_kind']=='blank'}
                self.assertIn(spec['application'],blanks);self.assertIn(spec['evidence'],blanks)

    # Break caught: trusting a task-looking URL, neighbour header, or changed agency.
    def test_parser_rejects_wrong_host_task_item_webid_kind_header_and_agency(self):
        for code,spec in OWN.items():
            raw=self.capture(code);item=spec['task'][:-2]
            changes=[('url',spec['host'],'www.jszwfw.gov.cn'),('url',spec['task'],'foreign-task'),
                     ('url',item+'&','foreign-item&'),('url','webId='+spec['web'],'webId=99'),
                     ('url','ql_kind=20','ql_kind=01'),('html','class="area_local">'+spec['district'],'class="area_local">建湖县'),
                     ('html',spec['agency'],'盐城市人力资源和社会保障局')]
            for key,old,new in changes:
                with self.subTest(code=code,mutation=old):
                    self.assertIn(old,raw[key]);changed=copy.deepcopy(raw);changed[key]=changed[key].replace(old,new)
                    with self.assertRaises(ValueError):self.parse(code,changed)
            other='320902' if code=='320903' else '320903'
            with self.assertRaises(ValueError):self.parse(code,self.capture(other))

    # Break caught: fixed 45-day warning when the own portal value changes.
    def test_warning_uses_actual_own_time_value(self):
        for code in OWN:
            raw=self.capture(code);raw['html']=raw['html'].replace('45个工作日','30个工作日')
            g=self.parse(code,raw)
            self.assertEqual(g['fields']['法定办结时限']['raw_value'],'30个工作日')
            self.assertIn('30个工作日',' '.join(g['warnings']));self.assertNotIn('45个工作日',' '.join(g['warnings']))

    # Break caught: enabling all portal "blank" labels or examples through a shared SHA.
    def test_only_two_own_downloaded_blank_forms_bind_offline(self):
        for code,spec in OWN.items():
            g=self.downloaded_guide(code)
            bound={t['id']:blank_binding(g,t) for t in g['templates'] if blank_binding(g,t)}
            self.assertEqual(bound,{spec['application']:'application',spec['evidence']:'evidence'})
            for kind in ['application','evidence']:
                t=next(t for t in g['templates'] if t['id']==spec[kind])
                self.assertEqual(t['sha256'],SHA[kind])
                self.assertEqual(hashlib.sha256((ROOT/t['file']).read_bytes()).hexdigest(),SHA[kind])

    # Break caught: attaching own blank bytes to a foreign guide identity or source.
    def test_binding_rejects_changed_guide_identity(self):
        for code in OWN:
            g=self.downloaded_guide(code);t=next(t for t in g['templates'] if t['id']==OWN[code]['application'])
            self.assertEqual(blank_binding(g,t),'application')
            for key,value in [('province','sichuan'),('city','无锡市'),('district','建湖县'),('region_code','320925'),
                              ('source_url',g['source_url']+'&foreign=1'),('source_id','foreign'),
                              ('authority','盐城市人力资源和社会保障局'),('service_code','foreign-task'),('verification_status','unverified')]:
                with self.subTest(code=code,key=key):
                    changed=copy.deepcopy(g);changed[key]=value;self.assertIsNone(blank_binding(changed,t))

    # Break caught: accepting a forged checksum, annex URL, sample label or neighbouring file.
    def test_binding_rejects_changed_template_provenance(self):
        for code in OWN:
            g=self.downloaded_guide(code);t=next(t for t in g['templates'] if t['id']==OWN[code]['application'])
            self.assertEqual(blank_binding(g,t),'application')
            for key,value in [('sha256','0'*64),('id','foreign-annex'),('annex_id','foreign-annex'),('region_code','320925'),
                              ('source_url',g['source_url']+'&foreign=1'),('official_kind','sample'),('download_status','not_downloaded'),
                              ('file',t['file'].replace('/'+code+'/','/320925/')),
                              ('download_url',t['download_url'].replace(t['id'],'00000000-0000-0000-0000-000000000000')),
                              ('download_url',t['download_url'].replace('sxgl.jszwfw.gov.cn:66','foreign.example'))]:
                with self.subTest(code=code,key=key,value=value):
                    changed=copy.deepcopy(t);changed[key]=value;self.assertIsNone(blank_binding(g,changed))


if __name__=='__main__':unittest.main()
