"""Offline evidence assembly for one unpublished locality; not a registered runtime parser."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlsplit, parse_qs

from lxml import html

from collect import OUT, NOW, save, SENSITIVE

ROOT = OUT.parents[2]
URL = 'https://hf.ahzwfw.gov.cn/bog-bsdt/static/workProcess/components/applicationMaterial.html?ssqdCode=da27275dce0645ffb87c9d9423e84452'
REGION = '340103000000'
AGENCY = '合肥市庐阳区人力资源和社会保障局'
SERVICE = '113401037608378827400201430200201'
TITLE = '劳动人事争议仲裁申请'

def text(node):
    return re.sub(r'\s+', ' ', node.text_content()).strip()

def same(a,b):
    return re.sub(r'\s+','',''+a)==re.sub(r'\s+','',''+b)

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def provenance(path, value):
    return {'source_url':URL,'capture_file':path.relative_to(ROOT).as_posix(),'capture_sha256':digest(path),'collected_at':value['captured_at']}

def load_capture(name):
    path=OUT/'luyang'/name/'dom.json'
    value=json.loads(path.read_text(encoding='utf-8'))
    assert value['url']==URL and AGENCY in value['text']
    dom=html.fromstring(value['html'])
    assert [text(h) for h in dom.xpath('//h1')]==[TITLE]
    return value, dom, provenance(path,value)

def main():
    captures={name:load_capture(name) for name in ['basic','conditions-success','materials-success','process','intermediary','faq','detail-application','detail-id','detail-evidence','statutory-explanation-dialog','promise-explanation-dialog','application-notice-hover']}
    basic, dom, basic_proof=captures['basic']
    raw={}
    for row in dom.xpath('//*[@id="section1"]//table[not(ancestor::table)]/tbody/tr|//*[@id="section1"]//table[not(ancestor::table)]/tr'):
        cells=row.xpath('./td|./th')
        if len(cells) not in (2,4):continue
        for i in range(0,len(cells),2):
            label=text(cells[i]);cell=deepcopy(cells[i+1])
            for hidden in cell.xpath('.//*[contains(@class,"el-dialog__wrapper")]'):
                hidden.getparent().remove(hidden)
            value=re.sub(r'\s*(说明|查看地图)$','',text(cell)).strip()
            assert label not in raw or raw[label]==value
            raw[label]=value
    assert raw['所属区划']=='庐阳区' and raw['实施主体']==AGENCY and raw['所属部门']==AGENCY
    assert raw['基本编码']=='002014302002' and raw['实施清单编码']==SERVICE and raw['事项名称']==TITLE
    public_model_path=OUT/'luyang/public-component-without-url-queries.json'
    public_model=json.loads(public_model_path.read_text(encoding='utf-8'))
    model=public_model['data']
    assert model['ssqdZoneCode']==REGION and model['ssqdBaseCode']==SERVICE and model['ssqdDeptName']==AGENCY
    assert model['ssqdName']==TITLE and model['ssqdCode']==parse_qs(urlsplit(URL).query)['ssqdCode'][0]
    sections={}
    for name,label,identifier in [('basic','基本信息','section1'),('conditions-success','受理条件','section2'),('materials-success','申请材料','section3'),('process','办理流程','section4'),('intermediary','中介服务','section5'),('faq','常见问题','section7')]:
        value,section_dom,proof=captures[name]
        section=section_dom.xpath('//*[@id=$id]',id=identifier)
        assert len(section)==1
        sections[label]=text(section[0])
    assert same(sections['受理条件'],model['acceptCondition'])
    assert re.sub(r'\s+','',model['hanleProc']) in re.sub(r'\s+','',sections['办理流程'])
    for item in model['cjwtJson']:
        for key in ('problemTitle','problemAnswer'):
            assert re.sub(r'\s+','',item[key]) in re.sub(r'\s+','',sections['常见问题'])
    model_proof={'capture_file':public_model_path.relative_to(ROOT).as_posix(),'capture_sha256':digest(public_model_path),'collected_at':public_model['captured_at'],'transformed_public_metadata':True}
    materials=[]
    rows=captures['materials-success'][1].xpath('//*[@id="section3"]//tr[td]')
    assert len(rows)==3 and len(model['clJson'])==3
    for material,row,detail in zip(model['clJson'],rows,['detail-application','detail-id','detail-evidence']):
        cells=row.xpath('./td');actual=[text(c) for c in cells]
        assert len(cells)==9
        expected=[material['materialName'],material['sourceChannelTxt'],material['json']['gbcllxTxt'],material['json']['ggfs'],material['json']['gbclxsTxt'],material['materialNeedTxt']]
        assert all(re.sub(r'\s+','',expect) in re.sub(r'\s+','',seen) for expect,seen in zip(expected,actual[:6]))
        modal_text=captures[detail][0]['text']
        assert re.sub(r'\s+','',material['materialEvidence']) in re.sub(r'\s+','',modal_text)
        assert re.sub(r'\s+','',material['acceptStandard']) in re.sub(r'\s+','',modal_text)
        notice=captures['application-notice-hover'][0]['text']
        assert re.sub(r'\s+','',material['editNotice']) in re.sub(r'\s+','',notice)
        materials.append({**captures['materials-success'][2],'region_code':'340103','id':material['id'],'name':material['materialName'],'required':material['materialNeedTxt'],'original_copy':actual[2],'raw_copies':actual[3],'copies':actual[3],'format':actual[4],'purpose':material['editNotice'],'applicable_conditions':None,'details':{'材料依据':material['materialEvidence'],'受理标准':material['acceptStandard']},'detail_evidence':captures[detail][2],'verification_status':'own_official_source_collected'})
    manifest_path=OUT/'luyang/downloads/manifest.json'
    originals=json.loads(manifest_path.read_text(encoding='utf-8'))
    assert len(originals)==3 and len({r['id'] for r in originals})==3
    expected=[]
    for material in model['clJson']:
        for kind,key in [('blank','materialEmpty'),('sample','materialSample')]:
            expected.extend((item,kind,material['id']) for item in material['json'][key])
    expected.extend((item,'instruction',None) for item in model['processImgJson'])
    templates=[]
    records={record['id']:record for record in originals}
    for item,kind,material_id in expected:
        record=records[item['id']]
        relative=Path('templates/_docx/_regional')/REGION/(item['id']+'-'+item['fileName'])
        original=OUT/'luyang/downloads'/relative.name
        assert record['file']==relative.as_posix() and record['source_url']==URL
        assert record['classification']==kind and record['fileName']==item['fileName'] and record['download_url']==item['filePath']
        assert record['http_status']==200 and record['request_credentials']=='none'
        assert record['bytes']==int(item['fileSize'])==original.stat().st_size
        assert digest(ROOT/relative)==digest(original)==record['sha256']
        templates.append({**model_proof,'source_url':URL,'region_code':'340103','id':item['id'],'annex_id':item['id'],'material_id':material_id,'original_name':item['fileName'],'official_kind':kind,'official_label':{'blank':'空白表格','sample':'示例样表','instruction':'办理流程图'}[kind],'file':relative.as_posix(),'file_type':item['fileExt'],'sha256':record['sha256'],'bytes':record['bytes'],'download_url':record['download_url'],'downloaded_at':record['downloaded_at'],'download_status':'downloaded','document_types':[],'content_verification_status':'NOT_RUN','content_classification':'official_label_unreviewed_content' if kind!='instruction' else 'workflow_instruction','download_manifest':{'file':manifest_path.relative_to(ROOT).as_posix(),'sha256':digest(manifest_path)},'download_provenance':{k:record[k] for k in ['requested_url_sha256','final_url_sha256','http_status','downloaded_at','request_credentials','response_session_headers']}})
    statutory=captures['statutory-explanation-dialog'][1].xpath('//*[@role="dialog" and @aria-label="法定办结时限说明"]')
    assert len(statutory)==1 and '四十五日' in text(statutory[0])
    sections['时限说明']=text(statutory[0])
    check=json.loads((OUT/'luyang/online-check-corrected.json').read_text(encoding='utf-8'))
    assert check['status']=='auth_required' and not check['callback_is_exact_service'] and not check['observation']['visible_credential_values_present']
    issues=[{'type':'statutory_time_unit_conflict','detail':'基本表为45个工作日；实际展开法定说明写受理起四十五日、复杂可延长最多十五日。逐字保留，未自行统一单位。'}, {'type':'promise_scope_unexplained','detail':'承诺1个工作日说明弹窗仅标题、正文为空；流程表为受理0.3/审查0.4/办结0.3工作日，不能认定全仲裁1日完结。'}, {'type':'faq_limitation_conflict','detail':'同一FAQ同时写仲裁时效一年及注意事项60日，保留冲突并待官方核实；未转化为用户期限提示。'}, {'type':'online_boundary_unverified','detail':'实际在线办理停于统一登录，回调为通用transition.html，不证明自身事项可线上提交。'}, {'type':'attachment_content_unreviewed','detail':'两份DOC按官网空白/示例标签分类；未转换、填写或逐页渲染，不断言内部字段空白或样例内容安全。'}]
    from regional_guides import digest as canonical_digest
    source_id=canonical_digest(URL)[:24]
    guide={'province':'anhui','province_name':'安徽省','city':'合肥市','district':'庐阳区','region_code':'340103','official_service_region_code':REGION,'service_name':TITLE,'original_service_name':TITLE,'service_code':SERVICE,'source_id':source_id,'source_url':URL,'source_title':TITLE,'source_type':'official_guide','authority':AGENCY,'collected_at':basic['captured_at'],'verified_at':None,'verification_status':'unpublished_candidate','fields':{k:{'raw_value':v,**basic_proof} for k,v in raw.items()},'materials':materials,'templates':templates,'sections':sections,'channel':{'raw_value':raw['办理形式'],'form':'window_and_online','online_status':'auth_required_unverified','entry_url':None,'entry_check':{'status':'auth_required','exact_service_verified':False,'evidence_file':(OUT/'luyang/online-check-corrected.json').relative_to(ROOT).as_posix()}},'source_issues':issues,'official_identity':{k:model[k] for k in ['ssqdCode','ssqdZoneCode','ssqdZoneName','ssqdBaseCode','ssqdDeptName','implementOrgName']},'evidence':{'captures':{name:record[2] for name,record in captures.items()},'public_component':model_proof},'publication_status':'unpublished','warnings':['自身来源采集，不是发布或文书适配通过。','公开component仅省略附件URL查询，完整原始component私有封存；未保存Cookie或Authorization值。']}
    guide_path=OUT/'luyang/normalized-guide.json'
    save(guide_path,guide)
    save(OUT/'staging-candidate.json',{'created_at':NOW(),'province':'anhui','province_name':'安徽省','city':'合肥市','district':'庐阳区','region_code':'340103','official_service_region_code':REGION,'source_id':source_id,'source_url':URL,'guide_file':guide_path.relative_to(ROOT).as_posix(),'guide_sha256':digest(guide_path),'materials':3,'templates':[{k:t[k] for k in ['id','file','sha256','bytes','official_kind','original_name']} for t in templates],'can_generate':False,'publication_status':'unpublished','web_qa':'NOT_RUN','document_generation':'NOT_RUN','document_render':'NOT_RUN','source_site_screenshot_review':'materials/process/login inspected; source evidence only','runtime_parser':'not_registered','shared_registry_modified':False})
    print(json.dumps({'source_id':source_id,'material_count':len(materials),'template_count':len(templates),'fields':len(raw),'public_candidate':guide_path.relative_to(ROOT).as_posix()},ensure_ascii=False))

if __name__=='__main__':
    import sys
    sys.path.insert(0,str(ROOT/'backend'))
    main()
