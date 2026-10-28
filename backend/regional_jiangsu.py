"""Explicit own-source Jiangsu identities, never province-wide requirements."""
import re
import base64
from datetime import datetime
from urllib.parse import parse_qs, urlsplit
from lxml import html

from regional_capture import pairs
from regional_guides import digest, resolve_channel

TASK='11320205014038763X400201430200201'
ITEM='11320205014038763X4002014302002'
SECTIONS={'基本信息':'floor1','部门信息':'floor2','窗口办理':'floor3','受理条件':'floor4',
          '申请材料':'floor10','办理流程':'floor5','办理时限':'floor6','收费标准':'floor7',
          '办理结果':'floor8','设定依据':'floor11','常见问题':'floor12','咨询投诉':'floor13'}


def text(node):return re.sub(r'\s+',' ',node.text_content()).strip()


def official_filename(value):
    # This source returns raw UTF-8 bytes in a legacy Latin-1 HTTP parameter.
    # Keep genuine Unicode/ASCII names as-is; never guess another template name.
    try:return value.encode('latin1').decode('utf8')
    except (UnicodeEncodeError,UnicodeDecodeError):return value


def table_pairs(node):
    return pairs([[text(c) for c in row.xpath('./th|./td')] for row in node.xpath('.//tr')])


def parse_xishan_capture(capture, entry_check=None):
    return _parse_exact_capture(capture,entry_check,{
        'city':'无锡市','district':'锡山区','region_code':'320205','task':TASK,'item':ITEM,
        'host':'www.jszwfw.gov.cn','path':'/jszwfw/bscx/itemlist/briefbszn.do','params':{'type':'2'},
        'authority':'锡山区人力资源和社会保障局'})


def parse_jianhu_capture(capture,entry_check=None):
    return _parse_exact_capture(capture,entry_check,{
        'city':'盐城市','district':'建湖县','region_code':'320925',
        'task':'11320925014387568C400201430200201','item':'11320925014387568C4002014302002',
        'host':'ycjh.jszwfw.gov.cn','path':'/jszwfw/publicservice/itemlist/showDetail.do',
        'params':{'webId':'99','ql_kind':'20'},'authority':'建湖县人力资源和社会保障局'})


def parse_dafeng_capture(capture,entry_check=None):
    return _parse_exact_capture(capture,entry_check,{
        'city':'盐城市','district':'大丰区','region_code':'320904',
        'task':'11320982553776482X400201430200201','item':'11320982553776482X4002014302002',
        'host':'www.jszwfw.gov.cn','path':'/jszwfw/publicservice/itemlist/showDetail.do',
        'params':{'webId':'94'},'authority':'盐城市大丰区人力资源和社会保障局'})


def parse_haizhou_capture(capture,entry_check=None):
    return _parse_exact_capture(capture,entry_check,{
        'city':'连云港市','district':'海州区','region_code':'320706',
        'task':'11320706014267312C400201430200201','item':'11320706014267312C4002014302002',
        'host':'lyghz.jszwfw.gov.cn','path':'/jszwfw/publicservice/itemlist/showDetail.do',
        'params':{'webId':'79','ql_kind':'20'},'authority':'连云港市海州区人力资源和社会保障局'})


def parse_yandu_capture(capture,entry_check=None):
    return _parse_exact_capture(capture,entry_check,{
        'city':'盐城市','district':'盐都区','region_code':'320903',
        'task':'11320928562941566D400201430200201','item':'11320928562941566D4002014302002',
        'host':'ycyd.jszwfw.gov.cn','path':'/jszwfw/publicservice/itemlist/showDetail.do',
        'params':{'webId':'93','ql_kind':'20'},'authority':'盐城市盐都区人力资源与社会保障局'})


def parse_tinghu_capture(capture,entry_check=None):
    return _parse_exact_capture(capture,entry_check,{
        'city':'盐城市','district':'亭湖区','region_code':'320902',
        'task':'11320902014360656E400201430200201','item':'11320902014360656E4002014302002',
        'host':'ycth.jszwfw.gov.cn','path':'/jszwfw/publicservice/itemlist/showDetail.do',
        'params':{'webId':'92','ql_kind':'20'},'authority':'盐城市亭湖区人力资源和社会保障局'})


def parse_dongtai_capture(capture,entry_check=None):
    return _parse_exact_capture(capture,entry_check,{
        'city':'盐城市','district':'东台市','region_code':'320981',
        'task':'11320981014396886W400201430200201','item':'11320981014396886W4002014302002',
        'host':'ycdt.jszwfw.gov.cn','path':'/jszwfw/publicservice/itemlist/showDetail.do',
        'params':{'webId':'100','ql_kind':'20'},'authority':'盐城市东台市人力资源和社会保障局'})


def parse_sheyang_capture(capture,entry_check=None):
    return _parse_exact_capture(capture,entry_check,{
        'city':'盐城市','district':'射阳县','region_code':'320924',
        'task':'11320924737070337G400201430200201','item':'11320924737070337G4002014302002',
        'host':'ycsy.jszwfw.gov.cn','path':'/jszwfw/publicservice/itemlist/showDetail.do',
        'params':{'webId':'98','ql_kind':'20'},'authority':'射阳县人力资源和社会保障局'})


def parse_binhai_capture(capture,entry_check=None):
    return _parse_exact_capture(capture,entry_check,{
        'city':'盐城市','district':'滨海县','region_code':'320922',
        'task':'11320922014374388A400201430200201','item':'11320922014374388A4002014302002',
        'host':'ycbh.jszwfw.gov.cn','path':'/jszwfw/publicservice/itemlist/showDetail.do',
        'params':{'webId':'96','ql_kind':'20'},'authority':'滨海县人力资源和社会保障局'})


def parse_xiangshui_capture(capture,entry_check=None):
    return _parse_exact_capture(capture,entry_check,{
        'city':'盐城市','district':'响水县','region_code':'320921',
        'task':'113209215754155300400201430200201','item':'1132092157541553004002014302002',
        'host':'ycxs.jszwfw.gov.cn','path':'/jszwfw/publicservice/itemlist/showDetail.do',
        'params':{'webId':'95','ql_kind':'20'},'authority':'响水县人力资源和社会保障局'})


def verify_jianhu_online_capture(before,after):
    return _verify_own_online_capture(before,after,parse_jianhu_capture)


def verify_dafeng_online_capture(before,after,callback_capture=None):
    # This observed publicservice alias returns to the own ycdf formal guide.
    # Never trust an arbitrary same-province host or task-looking callback.
    callback=None
    if callback_capture is not None:
        callback=_parse_exact_capture(callback_capture,None,{
            'city':'盐城市','district':'大丰区','region_code':'320904',
            'task':'11320982553776482X400201430200201','item':'11320982553776482X4002014302002',
            'host':'ycdf.jszwfw.gov.cn','path':'/jszwfw/bscx/itemlist/bszn.do',
            'params':{'webId':'94'},'authority':'盐城市大丰区人力资源和社会保障局'})
    result=_verify_own_online_capture(before,after,parse_dafeng_capture,callback)
    if callback:
        result['verified_callback_source_url']=callback['source_url']
        result['callback_verified_at']=callback['verified_at']
    return result


def verify_haizhou_online_capture(before,after,callback_capture=None,redirect_evidence=None):
    # The observed login carries an HTTP public return URL. A fresh native
    # visit reached the exact HTTPS own guide; do not generalize this alias.
    if callback_capture is None or redirect_evidence is None:
        raise ValueError('海州旧回跳缺少实际独立访问证据')
    callback=parse_haizhou_capture(callback_capture)
    legacy=urlsplit(before['url'])._replace(scheme='http').geturl()
    if (redirect_evidence.get('observed_callback')!=legacy
        or redirect_evidence.get('actual_final_url')!=callback['source_url']
        or callback['source_url']!=before['url']
        or redirect_evidence.get('at')!=callback_capture['captured_at']):
        raise ValueError('海州实际回跳来源或最终页面不匹配')
    result=_verify_own_online_capture(before,after,parse_haizhou_capture,callback,legacy)
    result.update(verified_callback_source_url=callback['source_url'],callback_verified_at=callback['verified_at'],
        observed_legacy_callback=legacy,
        callback_notice='认证链接带有旧HTTP回跳；本次独立访问最终到达本区HTTPS指南，登录后业务提交能力未验证。')
    return result


def _verify_own_online_capture(before,after,parse_own_capture,verified_callback=None,observed_legacy_callback=None):
    """Own button + actual redirected login DOM, never header text alone."""
    guide=parse_own_capture(before)
    dom=html.fromstring(before['html'])
    controls=dom.xpath('//a[@onclick="zxbldoonline();" and @jubanexturl]')
    if not any(text(a)=='在线办理' and urlsplit(a.get('jubanexturl')).hostname=='rs.jshrss.jiangsu.gov.cn'
               for a in controls):raise ValueError('缺少本地官网实际在线办理控件')
    url=after['url'];address=urlsplit(url);query=parse_qs(address.query)
    if address.scheme!='https' or address.hostname!='www.jszwfw.gov.cn' or address.path!='/jsjis/front/login.do':
        raise ValueError('不是实际跳转的官方身份认证页')
    try:
        target=urlsplit(base64.b64decode(query.get('gotoUrl',[''])[0],validate=True).decode('utf8'))
    except (ValueError,UnicodeError):raise ValueError('认证回跳来源无法核验')
    own=urlsplit(before['url'])
    if (target.scheme,target.hostname,target.path)!=(own.scheme,own.hostname,own.path) or parse_qs(target.query)!=parse_qs(own.query):
        callback=urlsplit(verified_callback['source_url']) if verified_callback else None
        exact_callback=callback and (target.scheme,target.hostname,target.path)==(callback.scheme,callback.hostname,callback.path)
        own_observed_upgrade=(callback and guide['region_code']=='320706' and target.scheme=='http'
            and target.geturl()==observed_legacy_callback
            and target._replace(scheme='https').geturl()==callback.geturl())
        if (not callback or not (exact_callback or own_observed_upgrade)
                or parse_qs(target.query)!=parse_qs(callback.query)
                or any(guide[k]!=verified_callback[k] for k in ['province','city','district','region_code','service_code','authority'])):
            raise ValueError('认证回跳不是本地区自身事项')
    page=html.fromstring(after['html'])
    if '统一身份认证系统' not in after['text'] or not page.xpath('//input[@type="password"]'):
        raise ValueError('未读取到真实认证表单，不以指南页登录文字代替')
    gap=(datetime.fromisoformat(after['captured_at'].replace('Z','+00:00'))-
         datetime.fromisoformat(before['captured_at'].replace('Z','+00:00'))).total_seconds()
    if not 0<=gap<=600:raise ValueError('认证跳转时间与本次浏览不匹配')
    return {**{k:guide[k] for k in ['province','city','district','region_code']},
            'source_url':guide['source_url'],'checked_at':after['captured_at'],
            'official_link':True,'status':'auth_required','url':url,
            'action':'实际点击自身在线办理进入统一身份认证，停止于登录，未提交申请'}


def _parse_exact_capture(capture,entry_check,spec):
    code=spec['region_code'];task=spec['task'];district=spec['district']
    url=capture['url'];parsed=urlsplit(url);query=parse_qs(parsed.query)
    if (parsed.scheme!='https' or parsed.hostname!=spec['host'] or parsed.path!=spec['path']
            or query.get('iddept_yw_inf')!=[task] or query.get('iddept_ql_inf')!=[spec['item']]
            or any(query.get(key)!=[value] for key,value in spec['params'].items())):
        raise ValueError('不是已独立核验的'+district+'正式指南')
    dom=html.fromstring(capture['html'])
    header=dom.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," area_local ")]')
    if not header or text(header[0])!=district or '劳动人事争议仲裁申请' not in capture['text']:
        raise ValueError('正式页面地区或事项不匹配')
    raw={};sections={}
    for name,identifier in SECTIONS.items():
        nodes=dom.xpath('//*[@id=$id]',id=identifier)
        if not nodes:raise ValueError('正式指南缺少已核验栏目：'+name)
        sections[name]='\n'.join(s.strip() for s in nodes[0].itertext() if s.strip())
        if name in {'基本信息','部门信息','窗口办理','办理时限','办理结果','咨询投诉'}:
            raw.update(table_pairs(nodes[0]))
    if raw.get('业务办理项编码')!=task or raw.get('实施主体')!=spec['authority']:
        raise ValueError('实际事项编码或实施机关已改变，需重新核验')
    service_object=re.search(r'服务对象[：:]\s*([^\n]+)',sections['受理条件'])
    if service_object:raw['服务对象']=service_object.group(1).strip()
    if '不收费' in sections['收费标准']:raw['是否收费']='不收费'
    # Preserve the actual original label as well as the shared UI's field key.
    if '必须到现场办理说明' in raw:raw['必须到现场原因']=raw['必须到现场办理说明']
    provenance={'source_url':url,'region_code':code,'collected_at':capture['captured_at'],
                'verified_at':capture['captured_at']}
    fields={key:{**provenance,'raw_value':value,'normalized_value':value or None,
                 'verification_status':'verified' if value else 'missing'} for key,value in raw.items()}
    if '必须到现场原因' in fields:fields['必须到现场原因']['original_label']='必须到现场办理说明'
    channel=resolve_channel(raw,sections['办理流程'],entry_check)
    if '办理形式' in fields:fields['办理形式']['normalized_value']=channel['form']
    materials=[];templates=[]
    for row in dom.xpath('//*[@id="floor10"]//tr[contains(concat(" ",normalize-space(@class)," ")," tsize ")]'):
        cells=row.xpath('./td')
        if len(cells)!=8:raise ValueError('材料列表列结构已变化')
        name=text(cells[1]);detail_tables=cells[7].xpath('.//table')
        details=table_pairs(detail_tables[0]) if detail_tables else {}
        if details.get('材料名称')!=name:raise ValueError('材料详情与当前材料不匹配')
        material_id=digest([code,name])[:20]
        materials.append({**provenance,'id':material_id,'name':name,'required':text(cells[5]),
                          'copies':re.sub(r'份$','',text(cells[4])),'raw_copies':text(cells[4]),
                          'original_copy':details.get('材料类型') or None,
                          'format':details.get('材料形式') or None,'purpose':None,'applicable_conditions':None,
                          'details':details,'verification_status':'verified'})
        for anchor in cells[2].xpath('.//a[@onclick]'):
            match=re.search(r"downloadClyb\('([^']+)'",anchor.get('onclick',''))
            if not match:continue
            download=match.group(1);address=urlsplit(download)
            annex=parse_qs(address.query).get('attachGuid',[''])[0]
            if address.scheme!='https' or address.hostname!='sxgl.jszwfw.gov.cn' or not re.fullmatch(r'[a-f0-9-]{36}',annex):
                raise ValueError('官方附件地址已变化，不能自动替换为其他来源')
            label=text(anchor);kind={'空白表格':'blank','示例样表':'sample'}.get(label,'unverified')
            templates.append({**provenance,'id':annex,'annex_id':annex,'material_id':material_id,
                              'original_name':name+'（'+label+'）','official_kind':kind,
                              'download_url':download,'download_status':'not_downloaded',
                              'can_generate':False,'document_types':[],'file_type':None})
    if len(materials)!=4:raise ValueError('材料数量已变化，请重新核验页面')
    return {'province':'jiangsu','province_name':'江苏省','city':spec['city'],'district':district,
            'region_code':code,'service_name':'劳动人事争议仲裁申请','service_code':task,
            'source_url':url,'source_title':capture['title'],'authority':raw['实施主体'],
            'collected_at':capture['captured_at'],'verified_at':capture['captured_at'],
            'verification_status':'verified','fields':fields,'sections':sections,
            'materials':materials,'templates':templates,'channel':channel,
            'warnings':[f"官网法定办结时限原文为{raw.get('法定办结时限') or '未公示'}，承诺办结时限原文为{raw.get('承诺办结时限') or '未公示'}；不代表在该时限内一定取得有利裁决。",
                        '办理流程以官网公开流程图为准；空白表格与示例样表分开保存。']}
