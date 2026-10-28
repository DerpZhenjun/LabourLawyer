import json
import sys
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'backend'));sys.path.insert(0,str(ROOT/'scripts'))
from province_experience import choose_guide,plain_guide,service_kind,valid_guide,portal_source,guide_rank
import importlib.util
spec=importlib.util.spec_from_file_location('refresh',ROOT/'scripts/refresh-province-experiences.py');refresh=importlib.util.module_from_spec(spec);spec.loader.exec_module(refresh)

class ProvinceExperienceTests(unittest.TestCase):
    def test_official_material_response_survives_visual_footer_guess(self):
        spec=importlib.util.spec_from_file_location('final_materials',ROOT/'scripts/finalize-province-experiences.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
        materials=[{'name':'劳动仲裁申请书','quantity':'原件2份'},{'name':'身份证样表','quantity':'复印件2份'},{'name':'证据目录','quantity':'复印件2份'}]
        guide={'materials':materials,'materials_complete':True}
        mod.retain_material_evidence(guide,['材料规范清晰有效,一经提交申请人对申报材料实质内容的真实性负责。窗口办理...'],True)
        self.assertEqual(guide['materials'],materials)
        self.assertTrue(guide['materials_complete'])
        pdf={'materials':['申请书','身份证'],'materials_complete':False}
        mod.retain_material_evidence(pdf,[],False)
        self.assertEqual(pdf['materials'],['申请书','身份证']);self.assertFalse(pdf['materials_complete'])

    def test_receipt_and_combined_hearing_mediation_have_distinct_plain_steps(self):
        p=plain_guide({'steps':[{'name':'申请'},{'name':'收件'},{'name':'开庭、调解'}]},'hubei')
        self.assertEqual([s['title'] for s in p['steps']],['先交材料','留意材料接收','留意开庭、调解通知'])
        self.assertEqual(p['steps'][-1]['official_name'],'开庭、调解')

    def test_no_fillable_template_does_not_claim_an_online_form(self):
        p=plain_guide({'service_name':'劳动仲裁'},'hebei','河北省')
        self.assertFalse(any('在线表格' in n for n in p['notes']))

    def test_portal_preferred_then_capital_then_visible_order(self):
        base={'service_name':'劳动人事争议仲裁申请','steps':[{'name':'受理'}]}
        local={**base,'guide_url':'https://rsj.example.gov.cn/a','region_name':'南京市'}
        other={**base,'guide_url':'https://www.jszwfw.gov.cn/b','region_name':'无锡市'}
        capital={**base,'guide_url':'https://www.jszwfw.gov.cn/c','region_name':'南京市'}
        second={**capital,'guide_url':'https://www.jszwfw.gov.cn/d'}
        self.assertIs(choose_guide([local,other,capital,second],'jiangsu'),capital)
    def test_foreign_portal_does_not_count_as_this_provinces_portal(self):
        self.assertFalse(portal_source('https://zwfw.hunan.gov.cn/a','zhejiang'))
        self.assertTrue(portal_source('https://banshi.beijing.gov.cn/a','beijing'))
    def test_mediation_is_supported_but_not_arbitration(self):
        self.assertEqual(service_kind('工会劳动争议调解'),'mediation')
        self.assertEqual(service_kind('仲裁委员会设立登记'),'other')
        p=plain_guide({'service_name':'工会劳动争议调解','steps':[{'name':'调解','description':'双方参加调解。'}]},'shanghai')
        self.assertIn('需要申请仲裁',p['notes'][0])
        self.assertIn('签字',p['steps'][0]['text'])
        self.assertEqual(p['steps'][0]['source_text'],'双方参加调解。')
    def test_search_results_are_never_claimed_to_be_guides(self):
        for url in ('https://zwfw.yn.gov.cn/portal/#/search/x','https://www.ahzwfw.gov.cn/pages/search-results.do','https://12345.jszwfw.gov.cn/a?searchValue=x'):
            g={'guide_url':url,'service_name':'劳动仲裁','workflow_text':'申请'}
            self.assertFalse(valid_guide(g));self.assertIsNone(choose_guide([g],'yunnan'))
    def test_capital_code_from_actual_query(self):
        self.assertFalse(guide_rank({'guide_url':'https://zwfw.guizhou.gov.cn/guide?areacode=520100'},'guizhou')[1])
        self.assertTrue(guide_rank({'guide_url':'https://zwfw.guizhou.gov.cn/guide?areacode=520300'},'guizhou')[1])
    def test_response_cannot_leak_another_districts_steps(self):
        url='https://zwfw.tj.gov.cn/#/operatingInstruction?taskCode=abc123456789'
        self.assertTrue(refresh.response_matches({'url':'https://zwfw.tj.gov.cn/get-regulation-info?taskCode=abc123456789'},url))
        self.assertFalse(refresh.response_matches({'url':'https://zwfw.tj.gov.cn/get-regulation-info?taskCode=OTHER123456'},url))
    def test_metadata_is_not_presented_as_bureaucratic_steps(self):
        p=plain_guide({'service_name':'劳动仲裁','workflow_text':'更多信息\n在线办理\n申请书\n到现场次数\n承诺办结期限'},'zhejiang')
        self.assertEqual(p['steps'],[]);self.assertFalse(p['workflow_detected'])
    def test_hunan_chain_keeps_real_order_with_plain_instructions(self):
        p=plain_guide({'service_name':'劳动仲裁','workflow_text':'接待登记-立案登记-案件组庭排庭-案件审理-结案处理'},'hunan')
        self.assertEqual(len(p['steps']),5);self.assertEqual(p['steps'][0]['title'],'先登记你的问题')
    def test_zhejiang_fullwidth_chain_and_liaoning_table(self):
        p=plain_guide({'service_name':'劳动仲裁','workflow_text':'更多信息\n在线办理\n申报材料\n申请书\n办理流程\n申请－受理－审理－出具结案文书－送达－办结\n更多信息\n在线办理'},'zhejiang')
        self.assertEqual([s['official_name'] for s in p['steps']],['申请','受理','审理','出具结案文书','送达','办结'])
        p=plain_guide({'service_name':'劳动仲裁','workflow_text':'办理环节\n接收申请\t辽宁某中心\n审核申请\t辽宁某中心\n办结\t辽宁某中心\n审批结果\n受理结果公示'},'liaoning')
        self.assertEqual(len(p['steps']),3)
    def test_shared_snapshot_has_31_distinct_art_and_honest_sources(self):
        web=json.loads((ROOT/'frontend/src/data/provinceExperiences.json').read_text(encoding='utf8'))
        mini=json.loads((ROOT/'miniprogram/data/provinceExperiences.json').read_text(encoding='utf8'))
        self.assertEqual(web,mini);self.assertEqual(len(web['provinces']),31)
        themes=json.loads((ROOT/'config/province_themes.json').read_text(encoding='utf8'))
        self.assertEqual(len({p['art'] for p in themes.values()}),31)
        for slug,p in web['provinces'].items():
            self.assertTrue(p['steps']);self.assertTrue((ROOT/'frontend/public'/themes[slug]['art'].lstrip('/')).is_file())
            self.assertTrue((ROOT/'miniprogram'/themes[slug]['miniArt'].lstrip('/')).is_file())
            if p['state']=='fresh':self.assertTrue(p['source_url'].startswith(('http://','https://')))
    def test_api_unknown_region_and_snapshot_consistency(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from routes.portal_reports import router
        app=FastAPI();app.include_router(router,prefix='/reports');client=TestClient(app)
        self.assertEqual(client.get('/reports/experiences/missing').status_code,404)
        result=client.get('/reports/experiences/shanghai');self.assertEqual(result.status_code,200)
        self.assertEqual(result.json()['slug'],'shanghai')
        self.assertNotIn('selected_guide',result.json())
        self.assertEqual(client.get('/reports/experience-reports/latest/missing').status_code,404)
    def test_material_footer_and_download_labels_are_not_extra_materials(self):
        p=plain_guide({'materials':['仲裁申请书','信息真实、准确，材料齐全，符合法规规定要求。','仲裁申请书 仲裁申请书（示范文本）.pdf[示范文本下载]仲裁申请书格式.docx[格式文本下载]']},'beijing')
        self.assertEqual(p['materials'],['仲裁申请书'])

    def test_unambiguous_material_rows_and_tile_names(self):
        spec=importlib.util.spec_from_file_location('finalize',ROOT/'scripts/finalize-province-experiences.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
        names=mod.material_names('<table><tr><th>序号</th><th>材料名称</th><th>要求</th></tr><tr><td>1</td><td>居民身份证</td><td>原件</td></tr><tr><td>2</td><td>劳动仲裁申请书</td><td>3份</td></tr></table>')
        self.assertEqual(names,['居民身份证','劳动仲裁申请书'])
        self.assertEqual(mod.names_from_text('必要\n居民身份证\n来源渠道\n必要\n证据材料'),['居民身份证','证据材料'])

if __name__=='__main__':unittest.main()
