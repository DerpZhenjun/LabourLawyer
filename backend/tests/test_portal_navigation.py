import asyncio,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'backend'))
from portal_interactions import material_controls,activate_section,confirm_search_region,scan_scroll,focus_material_download
from portal_workflows import section_text,parse_public_record,FLOW_LABELS,service_title,arbitration_service,official_region_names
from portal_attachment_downloads import file_type

class BrowserRegressionTests(unittest.IsolatedAsyncioTestCase):
    async def test_vertical_material_table_expands_and_keeps_its_own_downloads(self):
        from portal_interactions import visible_material_names
        await self.page.set_content('''<style>tr.detail{display:none}</style><table><tr class="gray_line" onclick="this.parentElement.querySelectorAll('.detail').forEach(n=>n.style.display='table-row')"><th colspan="2"><span class="lcmc">仲裁申请书（劳动者申请仲裁）</span><span class="gray_jt_icon">展开</span></th></tr><tr class="detail"><td>材料分类</td><td>申请表</td></tr><tr class="detail"><td colspan="2"><a href="https://example.gov.cn/sample.docx">查看示例</a><a href="https://example.gov.cn/blank.doc">空表下载</a></td></tr></table><table><tr><th><span class="lcmc">身份证件</span></th></tr><tr><td>材料分类</td><td>其他</td></tr><tr><td><a href="https://example.gov.cn/id.jpg">查看示例</a></td></tr></table>''')
        self.assertEqual(await material_controls(self.page.main_frame),[])
        result=await focus_material_download(self.page)
        self.assertTrue(result['control_in_viewport'])
        controls=await material_controls(self.page.main_frame)
        self.assertEqual([c['control_text'] for c in controls],['查看示例','空表下载'])
        self.assertEqual(controls[0]['material_name'],'仲裁申请书（劳动者申请仲裁）')
        self.assertEqual(await visible_material_names(self.page.main_frame),['仲裁申请书（劳动者申请仲裁）','身份证件'])

    async def test_material_without_download_is_focused_instead_of_bottom_evaluation(self):
        await self.page.set_content('<p>常见问题：仲裁申请书如何填写</p><div style="height:1000px"></div><div>1仲裁申请书（劳动者申请仲裁）</div><div style="height:1800px"></div><div>非常满意 非常不满意</div>')
        await self.page.evaluate('window.scrollTo(0,document.body.scrollHeight)')
        result=await focus_material_download(self.page)
        self.assertTrue(result['material_row_in_viewport'])
        self.assertEqual(result['control'],'')
        self.assertEqual(await material_controls(self.page.main_frame),[])
        box=await self.page.get_by_text('1仲裁申请书（劳动者申请仲裁）',exact=True).bounding_box()
        self.assertLess(box['y'],600)

    async def test_static_table_container_does_not_count_as_template_download(self):
        await self.page.set_content('<div id="blcl">序号 材料名称 材料份数 来源渠道 材料类型 材料形式 表格下载<table><tr><td>劳动人事争议仲裁申请书</td><td>2份</td><td>申请人自备</td><td>提交纸质文件</td></tr></table></div>')
        self.assertEqual(await material_controls(self.page.main_frame),[])

    async def test_material_table_retains_id_and_excludes_hidden_rows_and_footer(self):
        from portal_interactions import visible_material_names
        await self.page.set_content('<table><tr><th>序号</th><th>材料名称</th></tr><tr><td>1</td><td>仲裁申请书</td></tr><tr><td>2</td><td>身份证件<button>已关联电子证照</button></td></tr><tr><td>3</td><td>证据目录</td></tr><tr><td colspan="2">申请材料总要求 信息真实</td></tr></table><table hidden><tr><th>材料名称</th></tr><tr><td>隐藏材料</td></tr></table>')
        self.assertEqual(await visible_material_names(self.page.main_frame),['仲裁申请书','身份证件','证据目录'])

    async def test_material_anchor_is_clicked_instead_of_its_inert_list_parent(self):
        await self.page.set_content('<li><a href="javascript:void(0)" onclick="document.querySelector(\'#material\').hidden=false">申请材料</a></li><div id="material" hidden>仲裁申请书</div>')
        self.assertTrue(await activate_section(self.page,('申请材料',)))
        self.assertTrue(await self.page.locator('#material').is_visible())

    async def asyncSetUp(self):
        from playwright.async_api import async_playwright
        self.pw=await async_playwright().start()
        self.browser=await self.pw.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True,chromium_sandbox=True)
        self.page=await self.browser.new_page()
    async def asyncTearDown(self):
        await self.browser.close();await self.pw.stop()
    async def test_beijing_sample_row_and_unrelated_downloads(self):
        await self.page.set_content('''<button>APP下载</button><table><tr><td>仲裁申请书</td><td><a doc_name="仲裁申请书(样表).docx" doc_id="example">样例下载</a></td></tr><tr><td>身份证件</td><td><a doc_name="身份证件.docx">样例下载</a></td></tr></table>''')
        controls=await material_controls(self.page.main_frame)
        self.assertEqual(len(controls),1);self.assertEqual(controls[0]['kind'],'sample');self.assertEqual(controls[0]['doc_id'],'example')
    async def test_whole_guide_download_is_not_evidence_template(self):
        await self.page.set_content('<div class="item"><h1>劳动人事争议仲裁申请</h1><button>下载</button><table><tr><td>相关证据及证据目录</td><td>无</td></tr><tr><td>仲裁申请书</td><td><a href="https://test.gov.cn/application.docx">仲裁申请书.docx</a></td></tr></table></div>')
        controls=await material_controls(self.page.main_frame)
        self.assertEqual(len(controls),1);self.assertEqual(controls[0]['control_text'],'仲裁申请书.docx')
        await self.page.set_content('<div><p>常见问题：仲裁申请书需要哪些内容？</p><h2>指南下载与分享</h2><a href="https://test.gov.cn/get-regulation-zip?catalogcode=1">下载至本地</a></div>')
        self.assertEqual(await material_controls(self.page.main_frame),[])
    async def test_nested_hunan_materials_and_blank_control(self):
        await self.page.set_content('<div>必要<span>劳动仲裁申请书</span><div><span>示例</span><span>模板</span></div></div>')
        controls=await material_controls(self.page.main_frame)
        self.assertEqual({c['kind'] for c in controls},{'sample','blank'})
        self.assertTrue(all(c['material_name']=='劳动仲裁申请书' for c in controls))
    async def test_spa_material_anchor_does_not_destroy_guide_query(self):
        await self.page.goto('about:blank#/work-service/guide-detail?id=real&matterId=real')
        await self.page.set_content('<a href="#material">申请材料</a><div style="height:1000px"></div><div id="material">仲裁申请书</div>')
        before=self.page.url;self.assertTrue(await activate_section(self.page,('申请材料',)));self.assertEqual(self.page.url,before)
    async def test_only_public_location_prompt_is_confirmed(self):
        await self.page.set_content('''<div role="dialog">当前IP所在地为长沙市，是否搜索IP所在地结果？<button onclick="this.parentElement.remove()">确定</button></div><div role="dialog">确定提交仲裁申请吗？<button>确定</button></div>''')
        actions=await confirm_search_region(self.page)
        self.assertEqual(len(actions),1);self.assertEqual(actions[0]['scope'],'长沙市')
        self.assertIn('提交仲裁申请',await self.page.inner_text('body'))
    async def test_capital_then_first_visible_district_then_public_guide(self):
        from portal_guide_navigation import follow_public_guide
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)/'jiangsu';folder.mkdir()
            await self.page.set_content('''<div id="city">选择办理区域<button onclick="document.querySelector('#city').remove();document.querySelector('#district').hidden=false">苏州市</button><button onclick="document.querySelector('#city').remove();document.querySelector('#district').hidden=false">南京市</button></div><div id="district" hidden>请选择地区<button onclick="document.querySelector('#district').remove();document.querySelector('#guides').hidden=false">玄武区</button><button>秦淮区</button></div><div id="guides" hidden>区/县<table><tr><td>第一个机构</td><td><button onclick="document.body.innerHTML='劳动人事争议仲裁申请 基本信息 申请材料 办理流程'">查看指南</button></td></tr><tr><td>第二个机构</td><td><button>查看指南</button></td></tr></table></div>''')
            page,selected,actions=await follow_public_guide(self.page,'苏州市',folder)
            self.assertEqual(selected[:2],['南京市','玄武区'])
            self.assertEqual(next(a for a in actions if a['action']=='select_first_visible_district')['name'],'玄武区')
            self.assertIn('第一个机构',next(a for a in actions if a['action']=='open_public_guide')['row'])
    async def test_public_capital_picker_selects_capital_not_old_district(self):
        from portal_interactions import select_capital
        await self.page.set_content('''<button onclick="document.querySelector('#cities').hidden=false">切换区域</button><div id="cities" hidden><button>苏州市</button><button onclick="document.body.innerHTML='南京市已选择'">南京市</button></div>''')
        actions=await select_capital(self.page,'南京市')
        self.assertEqual(actions[-1]['name'],'南京市');self.assertIn('南京市已选择',await self.page.inner_text('body'))
    async def test_lazy_result_below_fold_is_loaded_and_focused(self):
        await self.page.set_content('''<div style="height:1800px"></div><script>window.addEventListener('scroll',()=>{if(scrollY>700&&!document.querySelector('a')){let a=document.createElement('a');a.innerText='劳动人事争议仲裁申请';document.body.append(a)}})</script>''')
        scan=await scan_scroll(self.page)
        self.assertTrue(scan[0]['results']);self.assertIn('仲裁申请',scan[0]['focused'])
    async def test_actual_download_row_is_focused_instead_of_faq(self):
        await self.page.set_content('<p>常见问题：仲裁申请书如何填写</p><div style="height:1600px"></div><table><tr><td>仲裁申请书</td><td><a doc_name="仲裁申请书.docx">样例下载</a></td></tr></table><div style="height:500px"></div>')
        result=await focus_material_download(self.page);self.assertEqual(result['control'],'样例下载')
        y=await self.page.locator('a').evaluate('n=>n.getBoundingClientRect().top');self.assertTrue(0<=y<600)
    async def test_real_tab_is_activated_before_sidebar_scroll_link(self):
        await self.page.set_content('<a href="#tabs">办理流程</a><div id="tabs"><span onclick="document.querySelector(\'#flow\').hidden=false">办理流程</span></div><div id="flow" hidden>受理 审查 决定</div>')
        await activate_section(self.page,('办理流程',));self.assertTrue(await self.page.locator('#flow').is_visible())

    async def test_tall_material_row_and_smooth_scroll_keep_control_visible(self):
        await self.page.set_content('<style>html{scroll-behavior:smooth}</style><div style="height:1800px"></div><table><tr><td>仲裁申请书</td><td><div style="height:1200px"></div><a>模板下载.docx</a></td></tr></table><div style="height:500px"></div>')
        result=await focus_material_download(self.page)
        self.assertTrue(result['control_in_viewport'])
        y=await self.page.locator('a').evaluate('n=>n.getBoundingClientRect().top')
        self.assertTrue(0<=y<600)

    async def test_view_attachment_is_detected_and_receipt_is_excluded(self):
        await self.page.set_content('<table><tr><td>仲裁申请书及副本</td><td><p onclick="void(0)">查看附件</p></td></tr><tr><td>劳动人事争议仲裁申请书收件回执</td><td><a href="https://example.gov.cn/receipt.jpg">下载1</a></td></tr></table>')
        controls=await material_controls(self.page.main_frame)
        self.assertEqual(len(controls),1)
        self.assertEqual(controls[0]['control_text'],'查看附件')
        self.assertNotIn('回执',controls[0]['material_name'])

    async def test_details_viewer_uses_material_name_and_distinguishes_sample(self):
        await self.page.set_content('<form class="materialinfo-detail"><table><tr><td>材料名称</td><td>证据清单及证据材料</td></tr><tr><td>空白表格下载</td><td><a href="https://example.gov.cn/a.doc">下载查看</a></td><td>示例样表下载</td><td><a href="https://example.gov.cn/b.docx">下载查看</a></td></tr></table></form>')
        controls=await material_controls(self.page.main_frame)
        self.assertEqual({c['material_name'] for c in controls},{'证据清单及证据材料'})
        self.assertEqual([c['kind'] for c in controls],['blank','sample'])

    async def test_material_group_is_not_a_download_and_id_example_is_excluded(self):
        await self.page.set_content('<div class="option-list"><div class="item">身份证<div>示例</div></div><div class="item">仲裁申请书<div class="operation"><div class="download">下载</div></div></div><div class="item">证据清单<div class="download">下载</div></div></div>')
        controls=await material_controls(self.page.main_frame)
        self.assertEqual(len(controls),2)
        self.assertEqual({c['material_name'] for c in controls},{'仲裁申请书','证据清单'})
        self.assertTrue(all(c['control_text']=='下载' for c in controls))

class DataRegressionTests(unittest.TestCase):
    def test_hainan_public_response_preserves_order_scope_and_special_phase(self):
        data={'sxImplBasic':{'rowguid':'actual-row','taskname':'劳动人事争议仲裁申请','xzqhcodeing':'460108','xzqhcodename':'海口市美兰区','deptname':'海口市美兰区人力资源和社会保障局'},'materials':[{'materialname':'劳动仲裁申请书','pagenum':1}], 'flowHjs':[{'hjNum':4,'hjName':'特殊环节','hjType':2,'hjTbcxname':'开庭、调解','hjSm':'开庭、调解；'},{'hjNum':1,'hjName':'受理','hjType':1,'hjSm':'材料审查'}]}
        record={'url':'https://wssp.hainan.gov.cn/wssp3/bszn/exempt/allInfo','body':json.dumps({'data':data}),'sha256':'actual-response'}
        result=parse_public_record(record)
        self.assertEqual(result['region_name'],'海口市美兰区')
        self.assertEqual([s['name'] for s in result['steps']],['受理','开庭、调解'])
        self.assertTrue(result['steps'][1]['special'])
        self.assertEqual(result['materials'][0]['name'],'劳动仲裁申请书')

    def test_hubei_employee_subservice_is_arbitration_but_case_lookup_is_not(self):
        parent='实施清单名称：劳动人事争议仲裁申请\n事项名称\n'
        title=service_title(parent+'劳动者申请立案')
        self.assertEqual(title,'劳动人事争议仲裁申请（劳动者申请立案）')
        self.assertTrue(arbitration_service(title))
        self.assertFalse(arbitration_service(service_title(parent+'案件进度查询')))

    def test_parenthesized_authority_label_does_not_become_authority_value(self):
        from portal_workflows import guide_record
        item=guide_record({'slug':'qinghai','name':'青海省'},{'final_url':'https://ywtb.qhzwfw.gov.cn/matterbszndetail.html','stage':'actual'},'劳动人事争议仲裁申请\n办理部门(实施主体)\t西宁市城东区人力资源和社会保障局')
        self.assertEqual(item['authority'],'西宁市城东区人力资源和社会保障局')

    def test_anhui_public_schema_keeps_all_materials_and_real_step_order(self):
        data={'ssqdName':'劳动人事争议仲裁申请','ssqdZoneCode':'340102000000','ssqdZoneName':'瑶海区','ssqdDeptName':'合肥市瑶海区人力资源和社会保障局','clJson':[{'materialName':'仲裁申请书','json':{'ggfs':'原件2份'}},{'materialName':'身份证样表','json':{'ggfs':'复印件2份'}},{'materialName':'证据目录'}],'blhjJson':[{'sort':'2','ywhjName':'审查','postResponse':'核对材料'},{'sort':'1','ywhjName':'受理','postResponse':'接收申请'}]}
        parsed=parse_public_record({'url':'https://hf.ahzwfw.gov.cn/bog-bsdt/implement/queryImplementInfo.do','body':json.dumps({'data':data}),'sha256':'source-proof'})
        self.assertEqual(parsed['region_code'],'340102000000')
        self.assertEqual([s['name'] for s in parsed['steps']],['受理','审查'])
        self.assertEqual([m['name'] for m in parsed['materials']],['仲裁申请书','身份证样表','证据目录'])
        self.assertEqual(parsed['materials'][0]['quantity'],'原件2份')
        self.assertEqual(parsed['source_response_sha256'],'source-proof')

    def test_navigation_label_alone_is_not_an_acquired_guide(self):
        from province_experience import valid_guide
        self.assertFalse(valid_guide({'guide_url':'https://hf.ahzwfw.gov.cn/guide','service_name':'劳动人事争议仲裁申请','workflow_text':'中介服务','steps':[],'materials':[],'templates':[]}))

    def test_legacy_attachment_is_reused_by_url_without_missing_fields(self):
        from portal_material_evidence import cached_attachment
        legacy={'text':'申请书','url':'https://example.gov.cn/a.docx','file':'attachments/real.docx'}
        current={'material_name':'仲裁申请书','control_text':'下载','kind':'blank','url':legacy['url']}
        self.assertEqual(cached_attachment([legacy],current)['file'],'attachments/real.docx')
        self.assertEqual(cached_attachment([{'text':'申请书','click':True}],current),{})
        self.assertEqual(cached_attachment([legacy,dict(legacy,file='different.docx')],current),{})

    def test_attachment_label_cannot_override_distinct_urls(self):
        from portal_material_evidence import cached_attachment
        old={'material_name':'仲裁申请书','control_text':'下载','kind':'blank','url':'https://example.gov.cn/a.docx','file':'attachments/a.docx'}
        current=dict(old,url='https://example.gov.cn/b.docx');current.pop('file')
        self.assertEqual(cached_attachment([old],current),{})
        no_url=dict(current);no_url.pop('url')
        self.assertEqual(cached_attachment([old],no_url)['file'],'attachments/a.docx')
    def test_failed_url_with_error_remains_resumable(self):
        from portal_audit_enrich import pending_urls,guide_stage
        url='https://zwfw.tj.gov.cn/#/operatingInstruction?taskCode=real'
        self.assertEqual(pending_urls([url+' network timeout',url,'地区目录未完成']),[url])
        self.assertEqual(guide_stage(url),guide_stage(url));self.assertNotEqual(guide_stage(url),guide_stage(url+'2'))
    def test_non_labour_arbitration_breadcrumb_is_identified(self):
        title=service_title('当前位置： 首页 法人办事 仲裁委员会变更备案\n仲裁委员会变更备案\n在线办理\n基本信息\n办理流程')
        self.assertEqual(title,'仲裁委员会变更备案');self.assertFalse(arbitration_service(title))
    def test_statute_prose_is_not_used_as_region_name(self):
        from portal_workflows import guide_record
        record=guide_record({'slug':'hunan','name':'湖南省'},{'final_url':'https://zwfw.hunan.gov.cn/guide','stage':'test'},'不得按行政区划层层设立。\n办理部门\n湖南省司法厅')
        self.assertEqual(record['region_name'],'');self.assertEqual(record['authority'],'湖南省司法厅')
    def test_flow_section_stops_before_faq(self):
        text='基本信息\n劳动申请\n办理流程\n受理\n审查\n决定\n常见问题\n无关长文字'
        self.assertEqual(section_text(text,FLOW_LABELS,('常见问题',)),'受理\n审查\n决定')
    def test_official_yunnan_region_and_timing_are_preserved(self):
        body=dict(id='real',name='劳动人事争议仲裁申请',regncode='532530000000',orgName='金平县人社局',apply='网上或现场申请',checkup='管辖审查',checkupDay=1,legalDay=5,promiseDay=2)
        record=dict(url='https://zwfw.yn.gov.cn/portal/gml/web10002',body=json.dumps({'C-Response-Body':json.dumps(body)}),sha256='digest')
        data=parse_public_record(record);self.assertEqual(data['region_code'],'532530000000');self.assertEqual(data['durations'],{'legal':5,'promise':2});self.assertEqual(len(data['steps']),2)
    def test_html_error_does_not_count_as_downloaded_document(self):
        self.assertIsNone(file_type(b'<html>error</html>'));self.assertEqual(file_type(b'%PDF-test'),'.pdf')
    def test_unrelated_wage_fund_guide_is_excluded(self):
        title=service_title('基本信息\n事项名称\t欠薪保障金垫付申请\n常见问题劳动仲裁')
        self.assertFalse(arbitration_service(title));self.assertTrue(arbitration_service('劳动人事争议仲裁申请'))
    def test_official_region_directory_labels_are_preserved(self):
        record=dict(url='https://banshi.beijing.gov.cn/guideservice/serviceArea/getServiceAreaById?id=110000000000',body=json.dumps({'data':{'id':'110000000000','locationName':'北京市','childNode':[{'id':'110105000000','locationName':'朝阳区'}]}}))
        self.assertEqual(official_region_names([record])['110105000000'],'朝阳区')

if __name__=='__main__':unittest.main()
