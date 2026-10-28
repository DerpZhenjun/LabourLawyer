"""Export traceable reports from the real captures and durable regional database."""
import hashlib,json,os,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from regional_guides import RegionalStore,now,digest
REPORT=ROOT/'reports/government-guide-localization'

def read_capture(name):
    result=json.loads((REPORT/name).read_text(encoding='utf-8-sig'))
    return json.loads(result) if isinstance(result,str) else result

def run():
    store=RegionalStore(os.getenv('LABOURLAWYER_REGIONAL_DB',ROOT/'backend/data/regional-guides.sqlite'))
    def event(data):return store.record_event({'id':digest(data)[:32],**data})
    for name,screen in [('search-engine-captcha.json','00-search-engine-captcha.png'),('baidu-captcha.json','00-baidu-captcha.png')]:
        captured=read_capture(name)
        event({'province':'sichuan','service':'官方入口搜索','keyword':'四川政务服务网','url':captured['url'],'occurred_at':captured['captured_at'],'type':'CAPTCHA_REQUIRED','screenshot':screen,'reason':'实际搜索引擎要求人工验证，停止，不绕过验证码','attempts':1,'final_status':'manual_authorization','remediation':'官方域名已由用户提供，继续独立的官方站内搜索；不宣称搜索引擎结果访问验收通过'})
    source=store.lookup('sichuan','成都市','天府新区')
    event({'province':'sichuan','city':'成都市','district':'天府新区','region_code':source['region_code'],'service':source['service_name'],'url':source['source_url'],'type':'TEMPLATE_DOWNLOAD_FAILED','screenshot':'07-official-application-sample.png','reason':'真实浏览器 download 首次返回 Download was canceled；随后从已访问控件对应的公开官方附件接口下载成功并校验SHA256','attempts':2,'final_status':'resolved','remediation':'仅使用已定位的公开政府附件接口，保留原名/哈希，不替换省级模板'})
    zj=read_capture('zhejiang-cross-check.json');login=read_capture('zhejiang-login-check.json')
    expected=['劳动人事争议仲裁申请','省人力社保厅','44','2份','《证据清单》']
    if not all(x in zj['text'] for x in expected):raise ValueError('浙江真实页面字段不足，不能写入已核对状态')
    cross=[{'province':'zhejiang','scope_type':'province_page','city':None,'district':None,'verification_status':'partial',
            'source_id':digest(zj['url'])[:24],'source_url':zj['url'],'source_title':zj['title'],'collected_at':zj['captured_at'],'verified_at':zj['captured_at'],
            'raw_text_file':'zhejiang-cross-check.json','screenshot':'19-zhejiang-basic-recheck.png',
            'raw_fields':{'实施主体':'省人力社保厅','承诺办结时限':'44工作日','到现场次数':'0次','法定办结时限':'60天','是否收费':'不收费'},
            'materials':['用人单位登记注册材料','劳动者身份证','《劳动人事争议仲裁申请书》','《证据清单》','存在劳动关系的证据和可证实申请人主张的证据'],
            'material_requirement':'纸质材料2份，A4，原件','online_status':'auth_required','entry_url':zj['url'],'login_origin':'https://user.zjzwfw.gov.cn',
            'limitation':'仅核对省级事项页面，不绑定任何市、区县；没有重新下载或替换已有浙江模板'}]
    event({'province':'zhejiang','service':'劳动人事争议仲裁申请','url':zj['url'],'occurred_at':login['captured_at'],'type':'AUTH_REQUIRED','screenshot':'18-zhejiang-login-boundary.png','reason':'实际点击在线办理进入官方登录页，登录表单还要求图片验证码；停止操作','attempts':1,'final_status':'manual_authorization','remediation':'用户自行在官网登录；省级页面不自动继承到具体区县'})
    event({'province':'guangdong','service':'劳动人事争议仲裁申请','url':'https://www.gdzwfw.gov.cn/portal/v3/guide/11440000553612461J244211105N00302','type':'GUIDE_PAGE_UNAVAILABLE','reason':'本次真实 Agent Browser 访问返回 net::ERR_EMPTY_RESPONSE；没有取得当前页截图，不把旧数据标为新核验','attempts':1,'final_status':'pending','remediation':'保留原有广东来源与文书，另行重试公开页面；当前具体区县显示未核验'})
    manifest=json.loads((REPORT/'CAPTURE-MANIFEST.json').read_text(encoding='utf8'))
    for search in manifest['searches']:
        search['page_title']=None
        search['page_title_status']='当前搜索截图未单独保存 document.title，不补造页面标题'
        search['evidence_file_written_at']=datetime.fromtimestamp((REPORT/search['screenshot']).stat().st_mtime,timezone.utc).isoformat()
        search['time_note']='截图文件生成时间；未补造缺失的页面自报时间'
    inventory={'exported_at':now(),'regions':store.inventory(),'cross_province_checks':cross,'searches':manifest['searches']}
    (REPORT/'SOURCE-INVENTORY.json').write_text(json.dumps(inventory,ensure_ascii=False,indent=2),encoding='utf8')
    issues=store.events()
    (REPORT/'COLLECTION-ISSUES.json').write_text(json.dumps(issues,ensure_ascii=False,indent=2),encoding='utf8')
    (REPORT/'outbox/pending-public-events.json').write_text(json.dumps([e for e in issues if e['delivery_status']=='PENDING_OPENCLAW'],ensure_ascii=False,indent=2),encoding='utf8')
    (REPORT/'CROSS-PROVINCE-CHECKS.json').write_text(json.dumps(cross,ensure_ascii=False,indent=2),encoding='utf8')
    groups={'官方事项搜索失败':['SEARCH_NO_RESULT','WRONG_SERVICE_MATCH'], '搜索关键词有效性':['SEARCH_ALIAS_REQUIRED','SEARCH_NO_RESULT'],
            '各地区网上办理支持':['ONLINE_APPLICATION_UNAVAILABLE','ONLINE_CHANNEL_UNVERIFIED','OFFICIAL_SOURCE_CONFLICT'],
            '官方申请空白模板缺失':['OFFICIAL_TEMPLATE_NOT_FOUND','TEMPLATE_DOWNLOAD_FAILED'],
            '官方页面无法访问':['GUIDE_PAGE_UNAVAILABLE'], '需人工登录或核验':['AUTH_REQUIRED','CAPTCHA_REQUIRED','OFFICIAL_SOURCE_CONFLICT'],
            '地区间办理要求差异':['OFFICIAL_SOURCE_CONFLICT','MATERIAL_INFORMATION_MISSING','SOURCE_STALE']}
    lines=['# 公开采集问题报告','',f'导出时间：{now()}。','',f'本地持久化事件 {len(issues)} 条；等待 OpenClaw 确认 {sum(e["delivery_status"]=="PENDING_OPENCLAW" for e in issues)} 条。',
           '', 'OpenClaw真实CLI 2026.9.4，健康检查可访问。本次隔离模型调用返回 fetch failed；没有已确认接收回执。此报告由本项目从原始事件导出，不冒称 OpenClaw 已接收。实际回执：openclaw/issue-review-receipt.json。','']
    for name,types in groups.items():
        lines+=['## '+name,'']
        subset=[e for e in issues if e['type'] in types]
        if not subset:lines+=['本次无此类记录，不代表全国没有此类问题。','']
        for e in subset:
            lines += [f'- `{e["id"]}` · {e.get("district") or e.get("province", "")} · {e["type"]} · {e["final_status"]}',
                      f'  - {e.get("reason", "")}',f'  - 处理：{e.get("remediation", "")}',f'  - 来源：{e.get("url", "")}',f'  - 截图：{e.get("screenshot") or "未取得，不伪造"}；记录时间：{e["occurred_at"]}；尝试：{e["attempts"]}。','']
    lines+=['## 实际地区对比','', '| 地区 | 办理形式原文 | 承诺时限 | 到场次数 | 网上入口核验 |','|---|---|---|---|---|']
    for g in store.inventory():lines.append(f'| {g["district"]} | {g["channel"]["raw_value"]} | {g["fields"]["承诺办结时限"]["raw_value"]} | {g["fields"]["到办事现场次数"]["raw_value"]} | {g["channel"]["online_status"]} |')
    lines+=['','三地均列出四种材料，份数相同：身份证件3、营业执照1、申请书3、负责人身份证明2；不捏造材料份数差异。实施机关、地点、时限、到场和渠道确有差异。浙江省级页面仅作跨省复核，不作为任何四川或浙江区县要求。']
    (REPORT/'OPENCLAW-ISSUE-REPORT.md').write_text('\n'.join(lines),encoding='utf8')
    print(json.dumps({'regions':len(store.inventory()),'events':len(issues),'pending':sum(e['delivery_status']=='PENDING_OPENCLAW' for e in issues)},ensure_ascii=True))

if __name__=='__main__':run()
