"""Independent jiq4 eight-tab evidence parser; never enables a generator.

The selected tab and selected locality are checked on *every* snapshot. Hidden
material popup data is retained as raw detail, not claimed as a downloaded file
or a completed interactive review. Existing jiq evidence is never reinterpreted.
"""
import hashlib
import copy
import json
import re
from pathlib import Path
from urllib.parse import parse_qs,urlsplit

from lxml import html
from regional_guides import digest,resolve_channel

SECTIONS=('基本信息','申请材料','受理条件','办理流程','收费标准','设定依据','中介服务','常见问题')


def _class(node,name):return name in node.get('class','').split()


def _text(node):return '\n'.join(s.strip() for s in node.itertext() if s.strip())


def _rows(table):
    return [[' '.join(_text(td).split()) for td in tr.xpath('./th|./td')]
            for tr in table.xpath('./tr|./tbody/tr|./thead/tr')]


def _pairs(rows):
    return {row[i]:row[i+1] for row in rows for i in range(0,len(row)-1,2)}


def parse_sichuan_v4_capture(manifest,captures,region_metadata):
    code=manifest.get('region_code','');city=manifest.get('city','');district=manifest.get('district','')
    url=manifest.get('source_url','');p=urlsplit(url);q=parse_qs(p.query)
    metadata=region_metadata or {}
    if (not re.fullmatch(r'51\d{10}',code) or manifest.get('province')!='sichuan'
            or p.scheme!='https' or p.hostname!='www.sczwfw.gov.cn'
            or p.path!='/jiq4/front/transition/ywTransToDetail' or q.get('areaCode')!=[code]
            or not q.get('itemCode') or metadata.get('areaCode')!=code or metadata.get('shortName')!=district):
        raise ValueError('新版官方来源或目录地区身份不匹配')
    if len(captures)!=8 or [s.get('section') for s in manifest.get('sections',[])]!=list(SECTIONS):
        raise ValueError('新版八个栏目证据不完整或顺序错误')
    allowed={district,'四川'+district,metadata.get('name')};trees=[];panels=[];sections={}
    for index,(name,capture) in enumerate(zip(SECTIONS,captures)):
        if capture.get('url')!=url or not capture.get('captured_at'):
            raise ValueError('新版栏目来源或时间不匹配')
        tree=html.fromstring(capture['html']);trees.append(tree)
        header=tree.xpath('//*[@id="cityName"]')
        item=tree.xpath('//*[@id="itemCode"]/@value');area=tree.xpath('//*[@id="areaCode"]/@value')
        title=tree.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," content1_title ")]')
        chosen=tree.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," selected ")]')
        if (not header or _text(header[0]) not in allowed or area!=[code] or item!=q['itemCode']
                or not any(n.get('data-name')==city and n.get('data-code')==code[:4]+'00000000' for n in chosen)
                or not any(n.get('data-code')==code and n.get('data-name')==district for n in chosen)
                or not title or _text(title[0])!='劳动人事争议仲裁申请'):
            raise ValueError('新版页头、事项、城市或区县编码不匹配')
        all_panels=tree.xpath('//div[contains(concat(" ",normalize-space(@class)," ")," content3_text_all ")]/div[contains(concat(" ",normalize-space(@class)," ")," content3_text ")]')
        active=[n for n in all_panels if _class(n,'on')]
        tabs=tree.xpath('//ul[contains(concat(" ",normalize-space(@class)," ")," content3_title_list ")]/li')
        if (len(all_panels)!=8 or len(active)!=1 or not _class(all_panels[index],'on')
                or not any(_class(n,'on') and _text(n)==name for n in tabs)):
            raise ValueError('新版栏目没有实际选中，禁止读取其他栏目冒充')
        panels.append(active[0]);sections[name]=_text(active[0])
    raw={}
    for table in trees[0].xpath('//table'):
        rows=_rows(table)
        if rows and rows[0] and rows[0][0] in {'服务对象','实施主体','是否支持预约办理','办理时间','办理行政许可的程序环节'}:
            raw.update(_pairs(rows))
    if not raw.get('实施主体') or not raw.get('办理形式'):
        raise ValueError('新版实施机关或办理形式缺失')
    at=captures[0]['captured_at'];mat_at=captures[1]['captured_at']
    fields={key:{'raw_value':value,'normalized_value':value or None,'source_url':url,'region_code':code,
                 'collected_at':at,'verified_at':at,'verification_status':'verified' if value else 'missing'}
            for key,value in raw.items()}
    channel=resolve_channel(raw,sections['办理流程']+'\n'+sections['常见问题'])
    # Generic window/online flow tabs do not establish a usable online channel.
    fields['办理形式']['normalized_value']=channel['form']
    materials=[];templates=[];material_panel=panels[1]
    tables=material_panel.xpath('.//table')
    summary=next((t for t in tables if _rows(t) and _rows(t)[0][:2]==['材料名称','材料必要性']),None)
    if summary is not None:
        for tr in summary.xpath('./tr|./tbody/tr|./thead/tr')[1:]:
            row=[' '.join(_text(td).split()) for td in tr.xpath('./th|./td')]
            if len(row)!=8 or not row[0].isdigit():raise ValueError('新版材料表结构变化，需人工核验')
            name,required,kind,form,copies=row[1:6]
            name_cell=tr.xpath('./td')[1]
            badges=[_text(n) for n in name_cell.xpath('./span[contains(concat(" ",normalize-space(@class)," ")," isReduce ")]')]
            if badges:
                labels=[_text(n) for n in name_cell.xpath('./span[not(contains(concat(" ",normalize-space(@class)," ")," isReduce "))]')]
                if len(labels)!=1:raise ValueError('新版材料名称与减免标记结构不明确')
                name=labels[0]
            detail=next((_pairs(_rows(t)) for t in tables if _rows(t) and _rows(t)[0]==['材料名称',name]),{})
            if not detail:raise ValueError('新版材料明细缺失')
            materials.append({'id':digest([code,name])[:20],'name':name,'required':required,
                              'original_copy':kind,'format':form,'copies':copies,'details':detail,
                              'purpose':None,'applicable_conditions':None,'official_badges':badges,'source_url':url,'region_code':code,
                              'verification_status':'verified','collected_at':mat_at,'verified_at':mat_at,
                              'detail_evidence':'raw_dom_popup_not_interactively_rechecked'})
    for link in material_panel.xpath('.//a[@onclick]'):
        match=re.fullmatch(r"downloadAnnexFile\('([0-9]+)'\);?",link.get('onclick','').strip())
        if not match:continue
        ancestors=list(link.iterancestors())
        popup=next((n for n in ancestors if _class(n,'material_example') or _class(n,'material_empty')),None)
        row=next((n for n in ancestors if n.tag=='tr'),None)
        names=row.xpath('./td[1]') if row is not None else []
        filename=_text(names[0]) if names else ''
        if popup is None or not filename:raise ValueError('新版附件用途或原始文件名不明确')
        annex=match.group(1)
        if any(t['id']==annex for t in templates):raise ValueError('新版附件ID重复，需检查关联材料')
        templates.append({'id':annex,'annex_id':annex,'original_name':filename,
                          'official_kind':'sample' if _class(popup,'material_example') else 'blank',
                          'source_url':url,'region_code':code,'collected_at':mat_at,
                          'file_type':filename.rsplit('.',1)[-1].lower(),
                          'download_status':'not_downloaded','can_generate':False,'document_types':[],
                          'download_reason':'尚未通过本地区实际下载控件核验，不推测下载地址'})
    warnings=['新版指南已按八个栏目读取；附件尚未完成本地区下载、填写适配和版式核验，暂不提供生成。']
    if not materials:warnings.append('官方当前页面显示“该事项暂无申请材料”，不代表无需提交材料；请向本地办理机构确认。')
    if channel['online_status']=='unverified':warnings.append('网上办理入口尚未核实；流程中的通用网上办理标签不代表可以在线申请。')
    if channel['online_status']=='conflict':warnings.append('官网不同栏目关于网上申请的表述不一致，请先向办理机构核实。')
    # Missing downloads/popup interaction remain explicit even when base fields exist.
    return {'province':'sichuan','province_name':'四川省','city':city,'district':district,'region_code':code,
            'service_name':'劳动人事争议仲裁申请','source_url':url,'source_title':captures[0]['title'],
            'collected_at':at,'verified_at':captures[-1]['captured_at'],'verification_status':'partial',
            'authority':raw['实施主体'],'official_version':raw.get('事项版本'),
            'service_code':raw.get('实施编码'),'fields':fields,'sections':sections,'channel':channel,
            'materials':materials,'templates':templates,'warnings':warnings,
            'portal_version':'jiq4','generation_enabled':False}


def load_sichuan_v4_capture(folder,region_metadata):
    folder=Path(folder).resolve()
    manifest=json.loads((folder/'manifest.json').read_text('utf8'));captures=[]
    for section in manifest.get('sections',[]):
        path=(folder/section['file']).resolve()
        if not path.is_relative_to(folder) or not path.is_file():raise ValueError('栏目证据路径越界或缺失')
        data=path.read_bytes()
        if hashlib.sha256(data).hexdigest()!=section.get('sha256'):raise ValueError('栏目证据SHA256已变化')
        capture=json.loads(data)
        if capture.get('captured_at')!=section.get('captured_at'):raise ValueError('栏目证据时间不匹配')
        captures.append(capture)
    result=parse_sichuan_v4_capture(manifest,captures,region_metadata)
    result['evidence']={'portal':'jiq4','sections':manifest['sections'],
                        'manifest_sha256':hashlib.sha256((folder/'manifest.json').read_bytes()).hexdigest()}
    return result


def annotate_download_failure(guide,network,checked_at,evidence_file):
    """Attach only this guide's observed public annex -> failing gateway chain.

    A shared browser trace may contain earlier regions. Exact Referer and own
    annex IDs are mandatory; a bare CLI timeout is not a government HTTP error.
    """
    url=guide['source_url'];q=parse_qs(urlsplit(url).query)
    if (guide.get('portal_version')!='jiq4' or q.get('areaCode')!=[guide['region_code']]
            or not checked_at or not evidence_file):raise ValueError('缺少自己的新版来源及核验时间')
    own=[r for r in network.get('requests',[]) if r.get('headers',{}).get('Referer')==url]
    result=copy.deepcopy(guide);annotated=0
    for template in result['templates']:
        candidates=[]
        for r in own:
            p=urlsplit(r.get('url',''))
            if (p.scheme=='https' and p.hostname=='www.sczwfw.gov.cn'
                    and p.path=='/jiq4/interface/item/annex/encryptUrl'
                    and parse_qs(p.query).get('rowguid')==[template['id']] and r.get('status')==200):
                candidates.append(r)
        if len(candidates)!=1:continue
        start=candidates[0]
        ends=[]
        for r in own:
            p=urlsplit(r.get('url',''))
            if (p.scheme=='https' and p.hostname=='www.sczwfw.gov.cn'
                    and p.path=='/materialibraryui/v4.0/meterialibraryCatFile/openDownload/giveFw'
                    and r.get('status')==504 and 0<=r.get('timestamp',0)-start.get('timestamp',0)<=120000):ends.append(r)
        if len(ends)!=1:continue
        if template.get('can_generate') or template.get('sha256'):raise ValueError('已适配或已有文件的附件不能用失败状态覆盖')
        template.update(download_status='failed',download_http_status=504,download_endpoint=start['url'],
                        attempted_download_url=ends[0]['url'],download_checked_at=checked_at,
                        download_network_evidence=evidence_file,can_generate=False,document_types=[],
                        download_error='本次实际点击后，官网附件文件网关返回 HTTP 504，尚未取得原文件。')
        annotated+=1
    if not annotated:raise ValueError('没有该地区自己附件的可核验HTTP504请求链')
    result['verification_status']='partial'
    result['warnings'].append('本次实际点击官网申请书附件后，文件网关返回 HTTP 504，未取得原文件，暂不开放生成。其他材料和办理方式仍以该地区原文为准。')
    return result
