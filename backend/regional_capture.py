"""Parse evidence captured in a real browser; never infer another locality."""
import re
from urllib.parse import parse_qs,urlsplit
from lxml import html
from regional_guides import resolve_channel,digest
from sichuan_v4_capture import load_sichuan_v4_capture,parse_sichuan_v4_capture

def pairs(rows):
    result={}
    for row in rows:
        for i in range(0,len(row)-1,2):result[str(row[i]).strip()]=str(row[i+1]).strip()
    return result

def parse_sichuan_capture(capture, city, district, entry_check=None, region_metadata=None):
    url=capture['url'];code=parse_qs(urlsplit(url).query).get('areaCode',[''])[0]
    allowed_headers={district,'四川'+district}
    if region_metadata and region_metadata.get('areaCode')==code and region_metadata.get('shortName')==district:
        allowed_headers.add(region_metadata.get('name'))
    if urlsplit(url).hostname!='www.sczwfw.gov.cn' or not any(name and name in capture.get('text','') for name in allowed_headers) or '劳动人事争议仲裁申请' not in capture.get('text',''):
        raise ValueError('真实页面与事项或地区不匹配')
    dom=html.fromstring(capture['html']);tables=capture['tables'];raw={}
    header=''.join(dom.xpath('//*[@id="cityName"]//text()')).strip()
    chosen_city=dom.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," selected ") and @data-name=$city]',city=city)
    chosen_district=dom.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," selected ") and @data-code=$code]',code=code)
    if header not in allowed_headers or not chosen_city or not chosen_district:
        raise ValueError('正式指南页头或已选地区编码与目标不一致')
    for rows in tables:
        if rows and rows[0][0] in {'服务对象','是否支持预约办理','办理时间','实施主体'}:raw.update(pairs(rows))
    sections={}
    for i,name in enumerate(['基本信息','申请材料','受理条件','办理流程','收费标准','设定依据','中介服务','常见问题'],1):
        nodes=dom.xpath(f'//*[@id="div{i}"]')
        sections[name]='\n'.join(s.strip() for s in nodes[0].itertext() if s.strip()) if nodes else ''
    flow=sections['办理流程']+'\n'+sections['常见问题']
    fields={k:{'raw_value':v,'normalized_value':v or None,'source_url':url,'region_code':code,
               'collected_at':capture['captured_at'],'verified_at':capture['captured_at'],
               'verification_status':'verified' if v else 'missing'} for k,v in raw.items()}
    channel=resolve_channel(raw,flow,entry_check)
    if '办理形式' in fields:fields['办理形式']['normalized_value']=channel['form']
    materials=[]
    material_tables=dom.xpath('//*[@id="div2"]//table')
    summary=next((r for r in tables if r and len(r[0])==7 and r[0][0]=='材料名称'),[])
    for index,row in enumerate(summary[1:]):
        if len(row)<8:continue
        name,required,kind,form,copies=row[1:6]
        detail=next((t for t in tables if t and t[0]==['材料名称',name] and len(t)>2),[])
        materials.append({'id':digest([code,name])[:20],'name':name,'required':required,'original_copy':kind,
                          'format':form,'copies':copies,'details':pairs(detail),
                          'purpose':None,'applicable_conditions':None,
                          'source_url':url,'region_code':code,'verification_status':'verified',
                          'collected_at':capture['captured_at'],'verified_at':capture['captured_at']})
    templates=[]
    for table in material_tables:
        # Hidden download panels are children of the same material's row.
        rows=table.xpath('./tr|./tbody/tr')
        if not rows:continue
        for link in table.xpath('.//a[@onclick]'):
            match=re.search(r"downloadAnnexFile\('([a-f0-9]+)'\)",link.get('onclick',''))
            if not match:continue
            tr=link.getparent()
            while tr is not None and tr.tag!='tr':tr=tr.getparent()
            filename=''.join(tr.xpath('./td[1]//text()')).strip() if tr is not None else ''
            # Page nesting: sample panel class bigtc2 vs blank panel bigtc1.
            parents=list(link.iterancestors())
            panel=next((p for p in parents if p.get('class','') in {'zhezhao4','zhezhao2'}),None)
            # Verified page handlers: biao1 opens zhezhao4 (blank), biao2 opens zhezhao2 (sample).
            cls=panel.get('class','') if panel is not None else ''
            label='sample' if cls=='zhezhao2' else 'blank' if cls=='zhezhao4' else 'unverified'
            annex=match.group(1)
            if any(t['annex_id']==annex for t in templates):continue
            templates.append({'id':annex,'annex_id':annex,'original_name':filename,'official_kind':label,
                              'source_url':url,'download_endpoint':f'https://www.sczwfw.gov.cn/jiq/interface/item/annex/encryptUrl?id={annex}',
                              'region_code':code,'collected_at':capture['captured_at'],'file_type':filename.rsplit('.',1)[-1].lower(),
                              'download_status':'not_downloaded','can_generate':False,'document_types':[]})
    # Some sites place panels as siblings, not under the materials wrapper.
    result={'province':'sichuan','province_name':'四川省','city':city,'district':district,'region_code':code,
            'service_name':'劳动人事争议仲裁申请','source_url':url,'source_title':capture['title'],
            'collected_at':capture['captured_at'],'verified_at':capture['captured_at'],
            'verification_status':'conflict' if channel['online_status']=='conflict' else 'verified',
            'fields':fields,'sections':sections,'materials':materials,'templates':templates,'channel':channel,
            'official_version':raw.get('事项版本'),'service_code':raw.get('业务办理项编码'),
            'authority':raw.get('实施主体',''),'warnings':[]}
    if channel['online_status']=='conflict':result['warnings'].append('官网基本信息与办理流程对网上申请的说明不一致。网上渠道待确认，请先致电办理机构。')
    if district=='天府新区' and '顺圣路60号' in flow and '市民中心' in raw.get('办理地点',''):
        result['warnings'].append('官网办理地点与常见问题列出不同地址。出发前请致电028-63025844确认。')
    if not materials:result['verification_status']='partial';result['warnings'].append('申请材料尚未完整读取。')
    return result
