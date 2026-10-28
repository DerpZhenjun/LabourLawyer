"""Independently captured Eco-city guide; internal key is not an admin code."""
import hashlib
import re
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from lxml import html
from regional_guides import digest, resolve_channel

GUIDE='https://www.eco-city.gov.cn/p1/sqldzc/20171010/461.html'
PORTAL='https://www.eco-city.gov.cn/p1/rcfw.html'
LIST='https://www.eco-city.gov.cn/p1/sqldzc.html'
KEY='function:tianjin-eco-city'
ROOT=Path(__file__).resolve().parents[1]
FILES={
    '110943177zze.doc':('https://www.eco-city.gov.cn/u/cms/www/201710/110943177zze.doc','sample','application',
        '2257fa08781ece314f4d1c595f68478c8495b4882a528501dcf78ff5f1f5c825'),
    '081434099aia.docx':('https://www.eco-city.gov.cn/u/cms/www/201910/081434099aia.docx','blank','evidence',
        '929229327433e0457b4a4fbdf4dc11551dbebc6156278b3e5fd22d025ff8a556'),
}


def text(node):return re.sub(r'\s+',' ',node.text_content()).strip()


def parse_ecocity_capture(captures,files):
    for name,url in [('guide',GUIDE),('online-channel',GUIDE),('official-annexes',GUIDE),
                     ('current-service-portal',PORTAL),('current-list',LIST)]:
        if captures[name]['url']!=url:raise ValueError('生态城自身访问路径不匹配')
    portal=html.fromstring(captures['current-service-portal']['html'])
    listing=html.fromstring(captures['current-list']['html'])
    if not any(urljoin(PORTAL,a.get('href'))==LIST for a in portal.xpath('//a[@href]')):
        raise ValueError('现行栏目未提供自身目录链接')
    if not any(urljoin(LIST,a.get('href'))==GUIDE for a in listing.xpath('//a[@href]')):
        raise ValueError('自身目录未引用该指南')
    page=captures['guide'];dom=html.fromstring(page['html'])
    blocks=dom.xpath('//div[contains(concat(" ",normalize-space(@class)," ")," conbox ")]')
    block=next((b for b in blocks if '在中新天津生态城内注册' in text(b)),None)
    if block is None:raise ValueError('缺少生态城自身受理范围')
    sections={};current=None
    for paragraph in block.xpath('./p'):
        value=text(paragraph)
        match=re.match(r'^[一二三四五六七八九十]+、([^：:]+)[：:](.*)',value)
        if match:current=match[1];sections[current]=match[2].strip()
        elif current and value:sections[current]+=('\n' if sections[current] else '')+value
    if sections.get('事项名称')!='劳动争议仲裁申请':raise ValueError('不是仲裁申请事项')
    if '此事项未开通在线受理功能' not in captures['online-channel']['text']:
        raise ValueError('未实际核验在线办事栏目')
    provenance={'source_url':GUIDE,'region_code':KEY,'collected_at':page['captured_at'],
                'verified_at':captures['official-annexes']['captured_at']}
    raw={k:sections.get(v,'') for k,v in {'窗口办理地点':'办理地点','办公时间':'办事时间',
        '联系电话':'联系电话','是否收费':'收费标准'}.items()}
    # Explicitly derived from the actual flow, not a fabricated official label.
    if '到窗口提交书面申请' not in sections.get('办理流程',''):raise ValueError('窗口流程已改变，需重新核验')
    raw.update({'办理形式':'窗口办理','是否网办':'否'})
    fields={k:{**provenance,'raw_value':v,'normalized_value':v or None,
               'verification_status':'verified' if v else 'missing'} for k,v in raw.items()}
    fields['办理形式'].update(raw_value=sections['办理流程'],normalized_value='window',
        original_label='办理流程',normalization_note='依据官网窗口提交流程及在线办事未开通提示归类')
    contact_text=captures['current-service-portal']['text']
    contact=contact_text.split('中新天津生态城劳动人事争议调解中心')[-1].split('业务范围')[0].strip()
    if not all(number in contact for number in ['022-66386789','022-66328970']):
        raise ValueError('现行联系栏目结构改变，需重新核实')
    fields['联系电话'].update(verification_status='conflict',alternative_sources=[{
        **provenance,'source_url':PORTAL,'raw_value':contact,'normalized_value':None,
        'collected_at':captures['current-service-portal']['captured_at'],'verification_status':'conflict'}])
    # The shared public UI uses these normalized keys. Keep the original labels
    # and exact raw values, including the contact conflict, alongside aliases.
    for original,normalized in [('窗口办理地点','办理地点'),('办公时间','办理时间'),('联系电话','咨询方式')]:
        fields[normalized]={**fields[original],'original_label':original}
    materials=[]
    for line in sections.get('办理材料','').splitlines():
        m=re.match(r'^([1-5])、(.*)',line)
        if not m:continue
        i=int(m[1]);value=m[2]
        names={1:'仲裁申请书',2:'申请人身份证',3:'市场主体基本信息',4:'劳动关系基本证据及证据清单',5:'劳动合同履行地在本辖区的证据'}
        materials.append({**provenance,'id':digest([KEY,i])[:20],'name':names[i],
            'required':'符合所列情形时提交' if i==5 else '需要提交',
            'copies':{1:'按被申请人人数＋1（通常两份）',2:'1',3:'1',4:'2',5:'1'}[i],
            'raw_copies':value,'original_copy':'复印件' if i==5 else '原件及复印件' if i in {2,3,4} else '原件',
            'format':'纸质（依据窗口书面提交流程）','purpose':None,
            'applicable_conditions':value if i==5 else None,'details':{'官方材料原文':value},
            'verification_status':'verified'})
    if len(materials)!=5:raise ValueError('官方材料数量或结构改变')
    annex_dom=html.fromstring(captures['official-annexes']['html'])
    links={urljoin(GUIDE,a.get('href')) for a in annex_dom.xpath('//a[@href]')}
    if len(files)!=2 or {f.get('original_name') for f in files}!=set(FILES):
        raise ValueError('自身两份原件信息不全或存在重复')
    templates=[]
    for f in files:
        filename=f['original_name'];spec=FILES.get(filename)
        if not spec:raise ValueError('不是已检查的自身原件')
        url,kind,document_kind,checksum=spec
        expected=f'templates/_docx/_regional/function-tianjin-eco-city/{filename}'
        if (f['source_url']!=GUIDE or f['download_url']!=url or url not in links or f['sha256']!=checksum
                or f['file']!=expected or f['http_status']!=200
                or hashlib.sha256((ROOT/expected).read_bytes()).hexdigest()!=checksum):
            raise ValueError('自身原件来源、路径或校验不匹配')
        templates.append({**provenance,'id':filename,'annex_id':filename,'original_name':f['official_display_name'],
            'official_kind':kind,'classification_note':'原件含示例请求，仅可参考填写' if kind=='sample' else '原件为未填写证据表格',
            'download_url':url,'download_status':'downloaded','file':expected,'sha256':checksum,
            'file_type':Path(filename).suffix[1:],'downloaded_at':f['downloaded_at'],
            'can_generate':False,'document_types':[],'intended_document_type':document_kind})
    channel=resolve_channel(raw,sections['办理流程'])
    channel.update(raw_value=sections['办理流程'],evidence_text='此事项未开通在线受理功能。',
                   verified_at=captures['online-channel']['captured_at'])
    return {'province':'tianjin','province_name':'天津市','city':'天津市','district':'中新天津生态城',
        'region_code':KEY,'official_region_code':None,'region_code_kind':'platform_functional_area_key',
        'service_name':sections['事项名称'],'service_code':None,'source_url':GUIDE,'source_title':page['title'],
        'authority':'人社局','verification_status':'partial',**{k:provenance[k] for k in ['collected_at','verified_at']},
        'fields':fields,'sections':sections,'materials':materials,'templates':templates,'channel':channel,
        'warnings':['仅适用于中新天津生态城，不代表整个滨海新区或天津市。功能区使用平台内部识别码，非官方行政区划编码。',
            '官网现行人社栏目仍引用此指南，但指南未明确更新日期；材料和办理要求请在前往窗口前再次确认。',
            '指南联系电话与现行人社服务栏目不同：指南022-66179792；栏目022-66386789、022-66328970。请以机构确认为准。',
            '申请书原件含示例请求，不是空白模板；目前提供官方原件下载，尚未开放本地填写适配。']}
