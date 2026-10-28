"""Exact Baiyun material notice, not a province guide or approved generator."""
import hashlib
import re
from pathlib import Path
from urllib.parse import urljoin
from zipfile import ZipFile
from lxml import html
from regional_guides import digest, resolve_channel

ROOT=Path(__file__).resolve().parents[1]
SOURCE='https://www.by.gov.cn/gzjg/qrlzyhshbzj/zcgg/cjgg/content/post_10451075.html'
TITLE='白云区劳动人事争议仲裁申请材料清单'
PACKAGES={
    'https://www.by.gov.cn/attachment/7/7891/7891723/10451075.zip':
        ('official-materials.zip','66edc11750f60e32633f99425233e5392c1988139305f3a79c71acb4ac1565a8',5),
    'https://www.by.gov.cn/attachment/7/7886/7886011/10451075.zip':
        ('official-examples.zip','b07c3df8c905badc72ad4ab6a29a6305d730d60625a632c8bc6c0e72630ab375',3),
}
NAMES=['申请人身份证正反面复印件','被申请人的工商登记资料','当事人送达地址确认书','仲裁申请书','证据材料','劳动争议仲裁收件单及其存根']


def parse_baiyun_capture(page,packages):
    if page['url']!=SOURCE:raise ValueError('不是白云区自身材料清单来源')
    dom=html.fromstring(page['html'])
    headings=dom.xpath('//h1[@class="article-title"]');blocks=dom.xpath('//div[@id="zoomcon"]')
    if len(headings)!=1 or headings[0].text_content().strip()!=TITLE or len(blocks)!=1:
        raise ValueError('自身事项标题或正文结构改变，需重新核验')
    block=blocks[0]
    paragraphs=[re.sub(r'\s+',' ',p.text_content()).strip() for p in block.xpath('./p')]
    raw_materials=[]
    for p in paragraphs:
        if p=='文书填写说明':break
        match=re.match(r'^([1-6])\.(.*)',p)
        if match:raw_materials.append((int(match[1]),match[2]))
    if [n for n,_ in raw_materials]!=list(range(1,7)):
        raise ValueError('材料数量或顺序已改变，不能套用旧清单')
    remark=next((p for p in paragraphs if p.startswith('备注：')),None)
    if not remark or '每增加一个被申请人' not in remark:raise ValueError('未保留按被申请人人数追加份数的原文')
    provenance={'source_url':SOURCE,'region_code':'440111','collected_at':page['captured_at'],
                'verified_at':page['captured_at']}
    materials=[]
    digits={'一':'1','两':'2','二':'2','三':'3','四':'4','五':'5','六':'6','七':'7','八':'8','九':'9'}
    for (n,value),name in zip(raw_materials,NAMES):
        if not value.startswith(name):raise ValueError('材料名称变化，需重新核验')
        count=re.search(r'([一两二三四五六七八九])份',value)
        if not count:raise ValueError('未识别自身材料份数')
        copies=digits[count[1]]
        if n==6:copies='收件单及存根各'+copies+'份'
        materials.append({**provenance,'id':digest([SOURCE,n])[:20],'name':name,
            'required':'需要提交（官方材料清单所列）','copies':copies,'raw_copies':value,
            'original_copy':'复印件' if '复印件' in value else '打印件' if '截图打印' in value else None,
            'format':'纸质（原文要求复印、打印或手写）','purpose':None,
            'applicable_conditions':remark if n in {4,5} else None,
            'details':{'官方材料原文':value,'统一填写要求':remark},'verification_status':'verified'})
    links={urljoin(SOURCE,a.get('href')) for a in block.xpath('.//a[@href]')}
    if len(packages)!=2 or {p.get('download_url') for p in packages}!=set(PACKAGES):
        raise ValueError('自身两份附件包缺失或被重复替代')
    templates=[]
    for package in packages:
        url=package['download_url'];filename,checksum,count=PACKAGES[url]
        expected='templates/_docx/_regional/440111/'+filename
        path=ROOT/expected
        if (package.get('source_url')!=SOURCE or url not in links or package.get('file')!=expected
            or package.get('sha256')!=checksum or package.get('http_status')!=200
            or package.get('download_status')!='downloaded' or not path.is_file()
            or hashlib.sha256(path.read_bytes()).hexdigest()!=checksum):
            raise ValueError('白云区自身附件包来源或原件校验失败')
        members=package.get('members',[]);pn=1 if filename=='official-materials.zip' else 2
        if len(members)!=count or len({m.get('archive_member_name') for m in members})!=count:
            raise ValueError('附件成员缺失或重复')
        with ZipFile(path) as archive:
            originals={}
            for info in archive.infolist():
                if info.is_dir():continue
                name=info.filename
                if not info.flag_bits&0x800:name=name.encode('cp437').decode('gbk')
                originals[name]=archive.read(info)
        if set(originals)!={m['archive_member_name'] for m in members}:raise ValueError('压缩包成员身份不匹配')
        for n,m in enumerate(members,1):
            name=m['archive_member_name'];ext=Path(name).suffix.lower()
            own=f'templates/_docx/_regional/440111/package-{pn}/{n:02}{ext}'
            member_path=ROOT/own
            if (m.get('file')!=own or not member_path.is_file()
                or member_path.read_bytes()!=originals[name]
                or hashlib.sha256(originals[name]).hexdigest()!=m.get('sha256')):
                raise ValueError('自身原附件成员来源、路径或SHA不匹配')
            kind='sample' if pn==2 else 'instruction' if n in {1,4} else 'blank'
            templates.append({**provenance,'id':f'baiyun-10451075-p{pn}-{n:02}',
                'id_kind':'platform_archive_member_key','official_annex_id':'7891723' if pn==1 else '7886011',
                'archive_member_name':name,'original_name':Path(name).name,'official_kind':kind,
                'classification_note':'官方填写示例，不是空白表格' if kind=='sample' else
                    '官方告知或材料说明，不是申请表' if kind=='instruction' else '官方材料包中的未填写表格，尚未适配生成',
                'download_url':url,'final_download_url':package.get('final_url'),
                'archive_sha256':checksum,'file':own,'sha256':m['sha256'],'file_type':ext[1:],
                'download_status':'downloaded','downloaded_at':package['downloaded_at'],
                'can_generate':False,'document_types':[],
                'contained_document_types':['application','evidence'] if pn==1 and n==5 else []})
    missing={k:{**provenance,'raw_value':'','normalized_value':None,'verification_status':'missing'}
        for k in ['办理形式','办理地点','办理时间','咨询方式','服务对象','法定办结时限','承诺办结时限','是否收费','到办事现场次数','必须到现场原因']}
    return {'province':'guangdong','province_name':'广东省','city':'广州市','district':'白云区','region_code':'440111',
        'service_name':'劳动人事争议仲裁申请','service_code':None,'source_url':SOURCE,'source_title':page['title'],
        'source_type':'official_material_notice','authority':'广州市白云区劳动人事争议仲裁委员会',
        'verification_status':'partial','collected_at':page['captured_at'],'verified_at':page['captured_at'],
        'fields':missing,'materials':materials,'templates':templates,'channel':resolve_channel({},''),
        'sections':{'申请材料':'\n'.join(f'{n}.{v}' for n,v in raw_materials)+'\n'+remark,
            '文书填写说明':'\n'.join(paragraphs[paragraphs.index('文书填写说明')+1:]),'官方材料说明全文':block.text_content().strip()},
        'warnings':['仅核验白云区自己的官方材料公告及附件，不代表广东省或广州市其他区县。',
            '本页未明确办理形式、网上申请入口、窗口时间和办理时限；纸质材料或邮寄收件单不等于只支持窗口办理。',
            '公告所写签字页码与空白原件当前渲染页码不一致；应按“申请人”“提交人”签字位置核对并向机构确认。',
            '原申请书附带证据清单、须知和旧窗口地址；尚未独立核验该地址及附录受理条件的现行有效性，不自动作为当前管辖判断。',
            '官方空白原件为DOC，申请书中含四列证据表；尚未完成此版填写适配，不使用其他省区模板替代。']}
