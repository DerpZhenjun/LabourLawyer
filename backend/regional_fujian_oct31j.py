"""Unregistered six-own-source J provider; offline QA never grants public phases."""
from copy import deepcopy
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import re
from zipfile import ZipFile
from lxml import etree as E
from regional_guides import digest,region_key

ROOT=Path(__file__).resolve().parents[1]
ADAPTER='fujian_six_own_blank_oct31j_v1'
SOURCE_BASE='reports/overnight-gap-closure-20261030/localities/fujian-j-source-projection'
REGIONS={'350122': {'province': 'fujian',
            'city': '福州市',
            'district': '连江县',
            'region_code': '350122',
            'source_id': 'bca45154d74905b963af83c9',
            'source_url': 'https://zwfw.fujian.gov.cn/person-todo/todo-fingerpost?unid=0AB23B595298D2754FC2B46E318C32FB&infoType=1',
            'service_code': '11350122003647125G400201430200201',
            'authority': '连江县人力资源和社会保障局',
            'allowed_kinds': ['application', 'evidence'],
            'copy_literals': ['原件份数2份', '原件份数2份', '复印件份数2份'],
            'folder': 'lianjiang-350122',
            'manifest_sha256': '3eb93e75371cc2e1ae75fd60373e055b61834d506618271a3f5bb76d97988493',
            'parent_source_version': '5384827484043c9b7919068c2aaaf3374d197b007e898852c1ac205df2a889dc',
            'boundary_title': '福建省智慧调解仲裁平台',
            'boundary_kind': 'Minzhengtong_APP_scan_login_required',
            'boundary_host': 'fjzc.fjzhkj.cn',
            'templates': {'application': {'file_id': 'F4048D8C91E2FF882AC6C62CC0EC4D86',
                                          'material_id': '073FF228AF99034EE0636C0E010A8FDE',
                                          'official_label': '仲裁申请书.docx',
                                          'sha256': '093b08f0c6aa6a33c535e3c0c196b74c496f86f23e65c09900fbdb2fc39d6365',
                                          'bytes': 13093,
                                          'source_file': 'reports/overnight-gap-closure-20261030/localities/fujian-j-source-projection/lianjiang-350122/application-own-format-public-retrieval.docx'},
                          'evidence': {'file_id': 'CC300F5D9DD5DC404D65C68116D50C55',
                                       'material_id': 'E831BA1D73F16062A761AC54EDFB2EEB',
                                       'official_label': '证据清单（空白）.docx',
                                       'sha256': 'd70eb6e31557c72029ab7b80c6d4f7783833e44c2cbf22e0cf9e1ef06abf4815',
                                       'bytes': 18887,
                                       'source_file': 'reports/overnight-gap-closure-20261030/localities/fujian-j-source-projection/lianjiang-350122/evidence-list-own-format-public-retrieval.docx'}}},
 '350123': {'province': 'fujian',
            'city': '福州市',
            'district': '罗源县',
            'region_code': '350123',
            'source_id': 'e6dccff3468cba55aa9b5c09',
            'source_url': 'https://zwfw.fujian.gov.cn/person-todo/todo-fingerpost?unid=F9AC961E43C2B1BEF413BE5DBFA96CE2&infoType=1',
            'service_code': '1135012300365355XX400201430200201',
            'authority': '罗源县人力资源和社会保障局',
            'allowed_kinds': ['application', 'evidence'],
            'copy_literals': ['原件份数2份', '原件份数2份', '复印件份数2份'],
            'folder': 'luoyuan-350123',
            'manifest_sha256': '4a0bdf4b2abd2c3b8a5a1c3285e26d903aa1bdc91900cd34ddd4bed8b0e87d44',
            'parent_source_version': '8c675d63e87d0985c2da3c2652f1291709ed578a03a77a5755fa40358352b20d',
            'boundary_title': '福建省智慧调解仲裁平台',
            'boundary_kind': 'Minzhengtong_APP_scan_login_required',
            'boundary_host': 'fjzc.fjzhkj.cn',
            'templates': {'application': {'file_id': 'F4048D8C91E2FF882AC6C62CC0EC4D86',
                                          'material_id': 'F0593EE6F76460FD02F07713E7C6313A',
                                          'official_label': '仲裁申请书.docx',
                                          'sha256': '093b08f0c6aa6a33c535e3c0c196b74c496f86f23e65c09900fbdb2fc39d6365',
                                          'bytes': 13093,
                                          'source_file': 'reports/overnight-gap-closure-20261030/localities/fujian-j-source-projection/luoyuan-350123/application-own-format-public-retrieval.docx'},
                          'evidence': {'file_id': 'CC300F5D9DD5DC404D65C68116D50C55',
                                       'material_id': 'FE995B2A9FF81FFB12C2C92D20BDC0E3',
                                       'official_label': '证据清单（空白）.docx',
                                       'sha256': 'd70eb6e31557c72029ab7b80c6d4f7783833e44c2cbf22e0cf9e1ef06abf4815',
                                       'bytes': 18887,
                                       'source_file': 'reports/overnight-gap-closure-20261030/localities/fujian-j-source-projection/luoyuan-350123/evidence-list-own-format-public-retrieval.docx'}}},
 '350124': {'province': 'fujian',
            'city': '福州市',
            'district': '闽清县',
            'region_code': '350124',
            'source_id': '4d74f378197bace2e63b05e9',
            'source_url': 'https://zwfw.fujian.gov.cn/person-todo/todo-fingerpost?unid=8145FB57E5488D9301D1A44B780F0AE7&infoType=1',
            'service_code': '11350124003659775T400201430200202',
            'authority': '闽清县人力资源和社会保障局',
            'allowed_kinds': ['application', 'evidence'],
            'copy_literals': ['原件份数2份', '原件份数2份', '复印件份数2份'],
            'folder': 'minqing-350124',
            'manifest_sha256': 'ef2c858082d86489e1c006a82b05202ad0b630d0217304b38616ba77efc5b987',
            'parent_source_version': '198ea6dd2a4c0cbf55f2b635a022cfea51795ee66a3d8fa20fa073e6cd31de2a',
            'boundary_title': '福建省智慧调解仲裁平台',
            'boundary_kind': 'Minzhengtong_APP_scan_login_required',
            'boundary_host': 'fjzc.fjzhkj.cn',
            'templates': {'application': {'file_id': 'F4048D8C91E2FF882AC6C62CC0EC4D86',
                                          'material_id': 'FB58DED77FB2681CCAE248FB07CEEE02',
                                          'official_label': '仲裁申请书.docx',
                                          'sha256': '093b08f0c6aa6a33c535e3c0c196b74c496f86f23e65c09900fbdb2fc39d6365',
                                          'bytes': 13093,
                                          'source_file': 'reports/overnight-gap-closure-20261030/localities/fujian-j-source-projection/minqing-350124/application-own-format-public-retrieval.docx'},
                          'evidence': {'file_id': 'CC300F5D9DD5DC404D65C68116D50C55',
                                       'material_id': 'D01298D0610CA0D256186A34871A5A9C',
                                       'official_label': '证据清单（空白）.docx',
                                       'sha256': 'd70eb6e31557c72029ab7b80c6d4f7783833e44c2cbf22e0cf9e1ef06abf4815',
                                       'bytes': 18887,
                                       'source_file': 'reports/overnight-gap-closure-20261030/localities/fujian-j-source-projection/minqing-350124/evidence-list-own-format-public-retrieval.docx'}}},
 '350125': {'province': 'fujian',
            'city': '福州市',
            'district': '永泰县',
            'region_code': '350125',
            'source_id': '3bfbebb0f7115a969c3d77be',
            'source_url': 'https://zwfw.fujian.gov.cn/person-todo/todo-fingerpost?unid=836301B361845E6D866C29E099B63DC9&infoType=1',
            'service_code': '11350125003666043A400201430200201',
            'authority': '永泰县人力资源和社会保障局',
            'allowed_kinds': ['application'],
            'copy_literals': ['原件份数2份', '原件份数2份', '复印件份数2份'],
            'folder': 'yongtai-350125',
            'manifest_sha256': '3f791f6bd9b0e33c64f0edac507ed66fb39897c4e9a7c43e8014ae7fc2a03dc2',
            'parent_source_version': 'b4474695c88e6381b4ed38691816724366c4a7b45a45ecbf5a4fceef3907d48b',
            'boundary_title': '福建省智慧调解仲裁平台',
            'boundary_kind': 'Minzhengtong_APP_scan_login_required',
            'boundary_host': 'fjzc.fjzhkj.cn',
            'templates': {'application': {'file_id': 'F4048D8C91E2FF882AC6C62CC0EC4D86',
                                          'material_id': 'C2F148AA7DC189D59113E8E47202E9D0',
                                          'official_label': '仲裁申请书.docx',
                                          'sha256': '093b08f0c6aa6a33c535e3c0c196b74c496f86f23e65c09900fbdb2fc39d6365',
                                          'bytes': 13093,
                                          'source_file': 'reports/overnight-gap-closure-20261030/localities/fujian-j-source-projection/yongtai-350125/application-own-format-public-retrieval.docx'}}},
 '350181': {'province': 'fujian',
            'city': '福州市',
            'district': '福清市',
            'region_code': '350181',
            'source_id': '9af3a0528483a9bb4fb67de5',
            'source_url': 'https://zwfw.fujian.gov.cn/person-todo/todo-fingerpost?unid=469958A9BED0E05129E545EFD2E2A759&infoType=1',
            'service_code': '113501810036849898400201430200201',
            'authority': '福清市人力资源和社会保障局',
            'allowed_kinds': ['application', 'evidence'],
            'copy_literals': ['原件份数2份', '原件份数2份', '复印件份数2份'],
            'folder': 'fuqing-350181',
            'manifest_sha256': 'cb8db6db69fa69a674a7cdb7bc4668a851f9f0e66f07ddfd3e5900ad0de18630',
            'parent_source_version': '07767ee192eac4f0918fe925b63dd528487915ce23b1288f7ac14cce28888f19',
            'boundary_title': '福建省智慧调解仲裁平台',
            'boundary_kind': 'Minzhengtong_APP_scan_login_required',
            'boundary_host': 'fjzc.fjzhkj.cn',
            'templates': {'application': {'file_id': 'F4048D8C91E2FF882AC6C62CC0EC4D86',
                                          'material_id': 'C6D041032B23726615A7FF1ED9F90E67',
                                          'official_label': '仲裁申请书.docx',
                                          'sha256': '093b08f0c6aa6a33c535e3c0c196b74c496f86f23e65c09900fbdb2fc39d6365',
                                          'bytes': 13093,
                                          'source_file': 'reports/overnight-gap-closure-20261030/localities/fujian-j-source-projection/fuqing-350181/application-own-format-public-retrieval.docx'},
                          'evidence': {'file_id': 'CC300F5D9DD5DC404D65C68116D50C55',
                                       'material_id': 'C3D25788F4625B882DE76F8830DADC4A',
                                       'official_label': '证据清单（空白）.docx',
                                       'sha256': 'd70eb6e31557c72029ab7b80c6d4f7783833e44c2cbf22e0cf9e1ef06abf4815',
                                       'bytes': 18887,
                                       'source_file': 'reports/overnight-gap-closure-20261030/localities/fujian-j-source-projection/fuqing-350181/evidence-list-own-format-public-retrieval.docx'}}},
 '350182': {'province': 'fujian',
            'city': '福州市',
            'district': '长乐区',
            'region_code': '350182',
            'source_id': 'e0b2adc9b9b0b10bc0eb9332',
            'source_url': 'https://zwfw.fujian.gov.cn/person-todo/todo-fingerpost?unid=CFA1069F9BE910A14774F6F86D48BB3C&infoType=1',
            'service_code': '113501820036722836400201430200201',
            'authority': '福州市长乐区人力资源和社会保障局',
            'allowed_kinds': ['application', 'evidence'],
            'copy_literals': ['原件份数2份', '原件份数2份', '复印件份数2份'],
            'folder': 'changle-350182',
            'manifest_sha256': 'f00d1b33a3179397b6cb42c8e7c587a56c468d0bf3a80d613e0ff8c52f788df4',
            'parent_source_version': 'b2f0361505a0176ca9972ec9176a7fbca75014744d6dc1b4933ea813d80359d2',
            'boundary_title': '福建省数字身份管理服务平台',
            'boundary_kind': 'Fujian_digital_identity_multi_method_login',
            'boundary_host': 'iam.e-govt.cn',
            'templates': {'application': {'file_id': 'F4048D8C91E2FF882AC6C62CC0EC4D86',
                                          'material_id': 'A14415F048410FBAD33BBECC53C5A6DB',
                                          'official_label': '仲裁申请书.docx',
                                          'sha256': '093b08f0c6aa6a33c535e3c0c196b74c496f86f23e65c09900fbdb2fc39d6365',
                                          'bytes': 13093,
                                          'source_file': 'reports/overnight-gap-closure-20261030/localities/fujian-j-source-projection/changle-350182/application-own-format-public-retrieval.docx'},
                          'evidence': {'file_id': 'C0D98561149170947B4366BCA0299DD9',
                                       'material_id': 'F03100CFE99D2A3222F14B9AE02695DD',
                                       'official_label': '证据清单（空白）.docx',
                                       'sha256': '511d213073af6e25b0f9f8ed2b914b7b31ee47bf6cef2fbb85a0422e3d6a4f56',
                                       'bytes': 18805,
                                       'source_file': 'reports/overnight-gap-closure-20261030/localities/fujian-j-source-projection/changle-350182/evidence-list-own-format-public-retrieval.docx'}}}}
BATCH_SHA='a718ca440ec04e701f3e93f0b79ddf4436ab19357a4eb6dc7814af2fd591b0af'
QA_REPORT='reports/overnight-gap-closure-20261030/localities/fujian-j/integration-qa-v1'
WORD_MANIFEST=QA_REPORT+'/WORD-MANIFEST.json'
PARITY_REPORT=QA_REPORT+'/SAFE-SOURCE-WORD-PARITY.json'
WORD_SHA='346e74b6afee3a6d8366fcc3910aef11e958d06b898c7045b0988b4525cc501d'
STAGE_RECEIPT=QA_REPORT+'/STAGE-APPROVAL.json'
PUBLICATION_RECEIPT=QA_REPORT+'/FINAL-BROWSER-QA.json'
STAGE_SHA256='129474f0bba0f7d79363899ab21244fa595f0a356a0bb000c907fc5d62e2126e'
PUBLICATION_SHA256='9860482c9772783927184e28686fb9779b1cce1a283c0d61902d8cde5dd57c45'
SUPPORTED=frozenset(REGIONS)
KINDS=('application','evidence')
APP_FIELDS=('applicantName','agentName','respondentName','requests','factsReason')
ITEM_FIELDS=('name','pageCount','originalType','purpose','pageRange')
_METADATA=frozenset({'version','region_id','content_hash'})
_FAILURES=(ValueError,OSError,KeyError,TypeError,StopIteration,AttributeError)
W='http://schemas.openxmlformats.org/wordprocessingml/2006/main';N={'w':W}


def require(ok,message):
    if not ok:raise ValueError(message)
def exact(a,b):
    if type(a) is not type(b):return False
    if isinstance(b,dict):return a.keys()==b.keys() and all(exact(a[k],v) for k,v in b.items())
    if isinstance(b,list):return len(a)==len(b) and all(exact(x,y) for x,y in zip(a,b))
    return a==b
def path_at(root,relative):
    require(root is not None and str(root).strip(),'Explicit own J public root required')
    root=Path(root).resolve();rel=Path(relative)
    require(not rel.is_absolute() and not rel.drive and '..' not in rel.parts,'Own public relative path required')
    path=(root/rel).resolve();require(path.is_relative_to(root) and path.relative_to(root).as_posix()==rel.as_posix(),'Own public path escaped or linked');return path
def _bytes(root,relative):
    try:return path_at(root,relative).read_bytes()
    except OSError as exc:raise ValueError('Explicit public root lacks own J proof') from exc
def _read(root,relative):return json.loads(_bytes(root,relative))
def _meta(code):
    require(type(code) is str and code in REGIONS,'Only six own J identities supported');return REGIONS[code]
def _kind(code,kind):
    meta=_meta(code);require(type(kind) is str and kind in meta['allowed_kinds'],'Own J sample/reference/unsupported kind cannot generate');return meta


def _sources(root,code):
    meta=_meta(code);folder=SOURCE_BASE+'/'+meta['folder'];raw=_bytes(root,folder+'/SOURCE-PROJECTION-MANIFEST.json')
    require(sha256(raw).hexdigest()==meta['manifest_sha256'],'Own J safe source version changed');manifest=json.loads(raw)
    expected={k:meta[k] for k in ['province','city','district','region_code','source_id','source_url','service_code','authority','copy_literals','allowed_kinds']}
    expected.update(derived_sanitized_projection=True,parent_source_freeze_sha256=meta['parent_source_version'],raw_api_response_included=False,
        raw_parent_is_runtime_dependency=False,can_generate=False,published=False,stage_approval=False,publication_approval=False,guide_status='partial',committee_full_name=None)
    require(all(k in manifest and exact(manifest[k],v) for k,v in expected.items()) and digest(meta['source_url'])[:24]==meta['source_id'],'Own J source identity or scope changed')
    require(type(manifest['files']) is dict and len(manifest['files'])==15,'Own safe source file set changed')
    for name,pin in manifest['files'].items():
        data=_bytes(root,folder+'/'+name);require(type(pin['bytes']) is int and len(data)==pin['bytes'] and sha256(data).hexdigest()==pin['sha256'],'Own safe source bytes changed')
    binding=_read(root,folder+'/own-official-bindings.json');api=_read(root,folder+'/api-own-attachment-metadata.json')
    require(all(exact(binding.get(k),meta[k]) for k in ['region_code','source_id','source_url','service_code','authority'])
        and binding['can_generate'] is False and binding['published'] is False and binding['byte_identity_grants_other_region_authority'] is False,'Own binding frame differs')
    require(api['raw_response_included'] is False and api['derived_public_allowlist_only'] is True and api['http_status']==200 and len(api['attachments'])==6,'Only own allowlisted source metadata accepted')
    for kind,t in meta['templates'].items():
        row=next(r for r in binding['attachments'] if r['file_id']==t['file_id'])
        item=next(r for r in api['attachments'] if r['file_id']==t['file_id'])
        require(item['material_id']==row['material_id']==t['material_id'] and item['type']=='1' and row['official_type']=='format'
            and row['eligible_kind']==kind and row['content_role']=='fillable_own_blank' and row['source_url']==meta['source_url']
            and folder+'/'+row['file']==t['source_file'] and row['sha256']==t['sha256'] and item['name']==t['official_label'],'Own J material/template/type binding differs')
        blank_layout(_bytes(root,t['source_file']),kind)
    dom=_read(root,folder+'/own-guide-native-dom.json');materials=_read(root,folder+'/material-statements.json')
    require(dom['url']==meta['source_url'] and len(dom['materials'])==3 and all(m['visible'] is True for m in dom['materials'])
        and exact(materials['copy_literals'],meta['copy_literals']),'Own J native guide/material scope differs')
    boundary=_read(root,folder+'/online-boundary.json');qualification=_read(root,folder+'/boundary-qualification.json')
    require(boundary['region_code']==code and boundary['source_url']==meta['source_url'] and boundary['observed_title']==meta['boundary_title']
        and boundary['boundary_kind']==meta['boundary_kind'] and qualification['observed_host']==meta['boundary_host']
        and qualification['actual_iam_qualification_applied'] is (code=='350182')
        and all(boundary[k] is False and qualification[k] is False for k in ['login_attempted','qr_scanned','application_submitted']),'Own J login boundary differs')
    require(qualification['parent_source_freeze_sha256']==meta['parent_source_version'],'Own boundary qualification version differs')
    types=_read(root,folder+'/type-content-qualification.json')
    require(exact(types['eligible_kinds'],meta['allowed_kinds']) and types['sample_to_blank_reclassification'] is False and types['committee_full_name'] is None,'Own format/sample classification differs')
    return manifest


def source_files(root,code=None):
    paths=[]
    for c in [code] if code is not None else REGIONS:
        meta=_meta(c);manifest=_sources(root,c);folder=SOURCE_BASE+'/'+meta['folder']
        paths.extend([folder+'/SOURCE-PROJECTION-MANIFEST.json',*[folder+'/'+n for n in manifest['files']]])
    if code is None:
        require(sha256(_bytes(root,SOURCE_BASE+'/BATCH-PROJECTION-INDEX.json')).hexdigest()==BATCH_SHA,'Own J batch index changed');paths.append(SOURCE_BASE+'/BATCH-PROJECTION-INDEX.json')
    return paths


def _word_manifest(root):
    raw=_bytes(root,WORD_MANIFEST);require(type(WORD_SHA) is str and sha256(raw).hexdigest()==WORD_SHA,'Own J public Word manifest changed');m=json.loads(raw)
    require(m['original_pages']==17 and m['generated_pages']==60 and m['word_documents']==22 and m['fictional_fixtures']==22
        and m['eligible_originals']==11 and m['stage_approved'] is False and m['can_publish'] is False,'Own J offline Word scope changed')
    require(m['actual_new_safe_projection_regeneration'] is True and m['same_request_claimed'] is False,'New own source request identity must be disclosed')
    require(type(m['files']) is list and len({r['path'] for r in m['files']})==len(m['files']),'Own Word leaf set invalid')
    for row in m['files']:
        require(row['path'].startswith(QA_REPORT+'/'),'Own J Word leaf path differs')
        raw=_bytes(root,row['path']);require(type(row['bytes']) is int and len(raw)==row['bytes'] and sha256(raw).hexdigest()==row['sha256'],'Own J Word proof leaf differs')
    return m


def parse_capture(code,*,root):
    meta=_meta(code);manifest=_sources(root,code);folder=SOURCE_BASE+'/'+meta['folder'];capture=folder+'/own-guide-native-dom.json';dom=_read(root,capture)
    fields={}
    def field(label,value,pointer):
        require(type(value) is str,'Own observed value must be text');value=value.strip()
        return {'raw_value':value,'normalized_value':value,'source_url':meta['source_url'],'source_label':label,'source_pointer':pointer,
            'capture_file':capture,'capture_sha256':manifest['files']['own-guide-native-dom.json']['sha256'],'region_code':code,
            'collected_at':dom['captured_at'],'verified_at':dom['captured_at'],'verification_status':'verified'}
    for row in dom['tables'][1]:
        if len(row)==2 and all(type(x) is str for x in row):fields[row[0].rstrip('：:').strip()]=field(row[0],row[1],'tables[1]')
    for display,source in {'咨询方式':'联系电话','服务对象':'申报对象','必须到现场原因':'必须现场办理原因','承诺办结时限':'承诺时限','法定办结时限':'法定时限'}.items():
        if source in fields:fields[display]=deepcopy(fields[source])
    for label,pattern in [('到办事现场次数',r'服务承诺到现场次数\n([^\n]+)'),('是否收费',r'\n收费情况\n是否收费：[\t ]*([^\n]+)')]:
        match=re.search(pattern,dom['text'])
        if match:fields[label]=field(label,match.group(1),'text/'+label)
    window=re.search(r'窗口办理\n办理时间：([^\n]+)\n办理地点：([^\n]+)\n',dom['text'])
    if window:
        fields['办理时间']=field('办理时间',window.group(1),'text/window_time');fields['办理地点']=field('办理地点',window.group(2),'text/window_address')
    statements=_read(root,folder+'/material-statements.json');binding=_read(root,folder+'/own-official-bindings.json');api=_read(root,folder+'/api-own-attachment-metadata.json')['attachments'];materials=[]
    for index,item in enumerate(dom['materials']):
        raw=item['text'];labels=list(re.finditer(r'(?:^|\n)([^\n\t]{1,40})\t[ \t]*',raw));details={}
        for i,label in enumerate(labels):
            end=labels[i+1].start() if i+1<len(labels) else len(raw)
            details[label.group(1).rstrip('：:').strip()]=raw[label.end():end].strip()
        own_material_ids={r['material_id'] for r in binding['attachments'] if r['official_label'] in raw}
        require(len(own_material_ids)==1,'Own native material panel has ambiguous attachment labels')
        material_id=next(iter(own_material_ids))
        require(any(r['material_id']==material_id for r in api),'Own native material is absent from own API frame')
        # Match only this panel's actual own attachment labels; retrieval order
        # differs from native panel order and confers no binding authority.
        name=item.get('header','').splitlines()[-1].strip()
        copies=int(re.search(r'(\d+)份',meta['copy_literals'][index]).group(1))
        original=re.search(r'材料类型：([^\n]+)',details.get('材料要求',''))
        materials.append({'id':material_id,
            'name':name,'required':details.get('材料必要性',''),'format':details.get('材料形式',''),'copies':copies,'paper_copies':copies,
            'copies_source_literal':meta['copy_literals'][index],'copies_are_source_metadata':True,'official_badges':[],
            'original_copy':original.group(1).strip() if original else '',
            'attachment_labels':['格式文本','示范文本'],'instructions':details.get('填报须知',''),'details':details,'raw_source_text':raw,
            'source_url':meta['source_url'],'capture_file':capture,'capture_sha256':manifest['files']['own-guide-native-dom.json']['sha256']})
    templates=[]
    for row in binding['attachments']:
        eligible=row['eligible_kind'];reference=row['content_role'] in {'scanning_instructions_only','official_format_contains_filled_sample_no_generation'}
        templates.append({'id':row['file_id'],'annex_id':row['file_id'],'region_code':code,'material_id':row['material_id'],
            'official_kind':'sample' if row['official_type']=='sample' else 'reference' if reference else 'blank','official_reported_type':row['official_type'],
            'original_name':row['official_label'],'file_type':'docx','source_url':meta['source_url'],'download_url':row['public_download_url'],
            'download_status':'downloaded','document_types':[],'can_generate':False,'file':folder+'/'+row['file'],'sha256':row['sha256'],'bytes':row['bytes'],
            'content_role':row['content_role'],'sample_contents_verified':False,'eligible_own_kind':eligible})
    boundary=_read(root,folder+'/online-boundary.json')
    return {'province':'fujian','province_name':'福建省','city':meta['city'],'district':meta['district'],'region_code':code,'source_id':meta['source_id'],
        'source_url':meta['source_url'],'source_version':meta['manifest_sha256'],'service_code':meta['service_code'],'service_name':'劳动人事争议仲裁申请',
        'authority':meta['authority'],'official_version':'','source_type':'own_official_guide_derived_safe_projection','verification_status':'partial','guide_status':'partial',
        'collected_at':dom['captured_at'],'verified_at':dom['captured_at'],'fields':fields,'sections':{'本区公开办事指南原文':dom['text']},'materials':materials,
        'templates':templates,'committee_full_name':None,'committee_autofill_allowed':False,'sample_contents_verified':False,'can_generate':False,'published':False,
        'publication_status':'source_only','channel':{'raw_value':fields.get('办理形式',{}).get('raw_value',''),'online_status':'auth_required','entry_url':None,
            'observed_entry_url':boundary['observed_entry_url'],'entry_check':{'status':'auth_required','observed_title':boundary['observed_title'],'boundary_kind':boundary['boundary_kind']},'submission_verified':False},
        'evidence':{'capture_file':capture,'capture_sha256':manifest['files']['own-guide-native-dom.json']['sha256'],'source_projection':folder+'/SOURCE-PROJECTION-MANIFEST.json','source_projection_sha256':meta['manifest_sha256']},
        'warnings':['自身指南仍为部分核实；缺少明确自身完整委员会名称，不自动填写。','自身材料份数只作来源信息，不自动推断法律提交份数。',
            '官方示范及已填内容不作为空白模板或案件事实；扫描说明不可生成。','自身登录边界只作观察，未登录、未扫码、未提交。']}


def prepare_candidate(code,*,root):
    meta=_meta(code);g=parse_capture(code,root=root);_word_manifest(root)
    g.update(can_generate=True,generation_adapter=ADAPTER,offline_candidate=True,publication_status='unregistered_offline_candidate')
    for kind,spec in meta['templates'].items():
        t=next(t for t in g['templates'] if t['id']==spec['file_id'])
        t.update(can_generate=True,document_types=[kind],adapter=ADAPTER,generation_mode='blank',content_kind='filled_official_blank',
            strict_binding={'region_code':code,'source_id':meta['source_id'],'source_version':meta['manifest_sha256'],'material_id':spec['material_id'],
                'template_sha256':spec['sha256'],'template_file':spec['source_file']},generation_label='依据'+meta['district']+'自身官方空白表格填写')
    return g


def approval_requirements(*,stage=True):
    result={'identities':[{'region_code':c,'source_id':m['source_id'],'source_projection_sha256':m['manifest_sha256'],'service_code':m['service_code']} for c,m in REGIONS.items()],
        'word_manifest_sha256':WORD_SHA,'eligible_originals':11,'approved_by':'independent_root','visual_review':'PASS','source_projection_review':'PASS','can_publish':not stage,'model_calls':0}
    if not stage:result.update(stage_receipt_sha256=STAGE_SHA256,native_confirmation_download_own_forms=True)
    return result
def _receipt(root,stage=True):
    pin=STAGE_SHA256 if stage else PUBLICATION_SHA256;require(type(pin) is str and re.fullmatch('[a-f0-9]{64}',pin),'Own J independent phase not approved')
    for code in REGIONS:_sources(root,code)
    word=_word_manifest(root);raw=_bytes(root,STAGE_RECEIPT if stage else PUBLICATION_RECEIPT);require(sha256(raw).hexdigest()==pin,'Own J phase receipt changed');receipt=json.loads(raw)
    require(all(k in receipt and exact(receipt[k],v) for k,v in approval_requirements(stage=stage).items()),'Own J phase approval scope differs')
    files=receipt.get('files');require(type(files) is list and files and len({r['path'] for r in files})==len(files),'Own phase leaves invalid')
    if stage:require(exact(files,word['files']),'Complete own offline Word proof not approved by stage')
    for row in files:
        require(row['path'].startswith(QA_REPORT+'/'),'Own approval leaf path differs');body=_bytes(root,row['path'])
        require(type(row['bytes']) is int and len(body)==row['bytes'] and sha256(body).hexdigest()==row['sha256'],'Own approval leaf bytes differ')
    return {'receipt':STAGE_RECEIPT if stage else PUBLICATION_RECEIPT,'sha256':pin}
def staged_candidate(code,*,root):
    g=prepare_candidate(code,root=root);g['candidate_adapter_evidence']=_receipt(root);g.update(offline_candidate=False,publication_status='staged_own_word_qa');return g
def _published(code,root):
    g=staged_candidate(code,root=root);g['publication_adapter_evidence']=_receipt(root,False);g.update(published=True,publication_status='published');return g
def _matches(g,canonical):
    if type(g) is not dict or set(g)-set(canonical)-_METADATA:return False
    if 'version' in g and (type(g['version']) is not int or g['version']<1):return False
    if 'region_id' in g and g['region_id']!=region_key('fujian',canonical['city'],canonical['district']):return False
    if 'content_hash' in g and (type(g['content_hash']) is not str or not re.fullmatch('[a-f0-9]{64}',g['content_hash'])):return False
    return all(k in g and exact(g[k],v) for k,v in canonical.items())
def _bound(g,root,allow_source=False):
    require(type(g) is dict,'Own J guide object required');code=g.get('region_code');raw=parse_capture(code,root=root)
    if allow_source and _matches(g,raw):return raw
    canonical=_published(code,root) if g.get('published') is True or 'publication_adapter_evidence' in g else staged_candidate(code,root=root)
    require(_matches(g,canonical),'Own J guide/source/material/template/phase binding differs');return canonical
def with_capabilities(g,*,root):_bound(g,root,True);return deepcopy(g)
def with_publication_evidence(g,*,root):
    require(type(g) is dict and _matches(g,staged_candidate(g.get('region_code'),root=root)),'Own stage is required before publication')
    result=_published(g['region_code'],root)
    for key in _METADATA&set(g):result[key]=deepcopy(g[key])
    return result
def checked_adapter(g,t,kind,*,root):
    canonical=_bound(g,root);meta=_kind(g['region_code'],kind);expected=next(v for v in canonical['templates'] if v['id']==meta['templates'][kind]['file_id'])
    require(exact(t,expected) and expected['can_generate'] is True and expected['official_kind']=='blank','Own J blank binding differs');return ADAPTER
def public_evidence(g,root):
    try:return deepcopy(_bound(g,root,True)['evidence'])
    except _FAILURES:return None
def approved_report_attachment(g,t,root):
    try:return any(exact(row,t) and row['download_status']=='downloaded' for row in _bound(g,root,True)['templates'])
    except _FAILURES:return False


def defaults(code,kind):
    _kind(code,kind)
    return {'applicantName':'','agentName':'','respondentName':'','requests':[''],'factsReason':''} if kind=='application' else {'evidenceList':[{k:'' for k in ITEM_FIELDS}]}
def form_fields(code,kind):
    _kind(code,kind)
    def text(key,label,n,**extra):return {'key':key,'label':label,'type':'text','nullable':False,'maxLength':n,**extra}
    if kind=='application':return [text('applicantName','申请人信息',180),text('agentName','委托代理人信息',180),text('respondentName','被申请人信息',180),{'key':'requests','label':'仲裁请求','type':'text_list','nullable':False,'maxItems':3,'maxLength':360},text('factsReason','事实与理由',2400)]
    return [{'key':'evidenceList','label':'证据内容','type':'object_list','nullable':False,'maxItems':15,'fields':[text('name','证据名称',60),text('pageCount','页数',4),text('originalType','原件或复印件',4,choices=['原件','复印件']),text('purpose','证明对象',80),text('pageRange','页码',32)]}]
def schema_descriptor(code,kind):
    meta=_kind(code,kind);return {'schema_id':f'fujian-j-{code}-{kind}-v1','schema_version':1,'region_code':code,'source_id':meta['source_id'],'source_version':meta['manifest_sha256'],'fields':form_fields(code,kind),'defaults':defaults(code,kind),'policy':{'unknown_fields':'reject','invalid_xml':'reject','text_controls':'newline_only','trim_text':True,'capacity_is_official_requirement':False}}
def template_path(code,kind,*,root):
    meta=_kind(code,kind);_sources(root,code);return path_at(root,meta['templates'][kind]['source_file'])
def envelope(code,kind,data,*,root):
    meta=_kind(code,kind);_sources(root,code);t=meta['templates'][kind]
    return {'province':meta['province'],'city':meta['city'],'district':meta['district'],'region_code':code,'source_id':meta['source_id'],'source_url':meta['source_url'],'source_version':meta['manifest_sha256'],
        'material_id':t['material_id'],'template_id':t['file_id'],'template_file':t['source_file'],'template_sha256':t['sha256'],'template_version':'sha256:'+t['sha256'],
        'schema_id':f'fujian-j-{code}-{kind}-v1','schema_version':1,'kind':kind,'mode':'blank','data':deepcopy(data)}
def validate_request(payload,*,root):
    require(type(payload) is dict,'Own J request object required');code=payload.get('region_code');kind=payload.get('kind');meta=_kind(code,kind);expected=envelope(code,kind,{},root=root)
    require(payload.keys()==expected.keys() and all(exact(payload[k],v) for k,v in expected.items() if k!='data'),'Own J region/source/version/material/template/schema tuple differs')
    data=payload['data'];require(type(data) is dict,'Own J form data must be object')
    if kind=='application':
        require(not set(data)-set(APP_FIELDS),'Unsupported own J application slot');values={k:'' for k in APP_FIELDS if k!='requests'};values['requests']=[]
        for key,value in data.items():
            if key=='requests':
                require(type(value) is list and len(value)<=3,'Own J request capacity exceeded');values[key]=[text(v,360) for v in value]
            else:values[key]=text(value,2400 if key=='factsReason' else 180)
    else:
        require(not set(data)-{'evidenceList'},'Unsupported own J evidence slot');rows=data.get('evidenceList',[]);require(type(rows) is list and len(rows)<=15,'Own J evidence capacity exceeded');values={'evidenceList':[]}
        for row in rows:
            require(type(row) is dict and not set(row)-set(ITEM_FIELDS),'Unsupported own J evidence item slot');item={k:'' for k in ITEM_FIELDS}
            for key,value in row.items():item[key]=text(value,{'name':60,'pageCount':4,'originalType':4,'purpose':80,'pageRange':32}[key])
            require(item['originalType'] in ('','原件','复印件') and (not item['pageCount'] or re.fullmatch('[1-9][0-9]{0,3}',item['pageCount'])),'Own page count/original type invalid');values['evidenceList'].append(item)
    return meta,kind,values


# Copied only J's independently reviewed pure OOXML mapping; no other provider imports.

def blank_layout(raw,kind):
    with ZipFile(BytesIO(raw)) as z:
        require(z.testzip() is None,'Own DOCX package invalid')
        r=E.fromstring(z.read('word/document.xml'));ps=r.findall('w:body/w:p',N)
        require(len(r.findall('w:body/w:sectPr',N))==1,'Own section layout changed')
        if kind=='application':
            require(len(ps)==22 and not r.findall('.//w:tbl',N),'Own application layout changed')
            text=lambda p:''.join(p.itertext())
            require(text(ps[0])=='仲裁申请书' and text(ps[2]).strip()=='申请人：' and text(ps[3]).strip()=='委托代理人：'
                and text(ps[4]).strip()=='被申请人：' and text(ps[19])=='申请人：','Own application is not the inspected blank')
            require(all(not text(p).strip() for p in ps[11:15]),'Filled facts cannot be a blank')
            for i,p in enumerate(ps[7:10]):require(text(p).strip()==f'{i+1}、','Filled requests cannot be a blank')
        else:
            ts=r.findall('.//w:tbl',N);require(len(ps)==2 and len(ts)==1,'Own evidence layout changed')
            rows=ts[0].findall('w:tr',N)
            require(len(rows)==11 and [''.join(c.itertext()) for c in rows[0].findall('w:tc',N)]==['序号','证据名称','页数','原件/复印件','证明对象','页码'],'Own evidence columns changed')
            require(all(not ''.join(c.itertext()).strip() for row in rows[1:-1] for c in row.findall('w:tc',N)),'A filled sample is not a blank evidence list')
        return r


def text(value,capacity):
    require(type(value) is str and len(value)<=capacity and all(c=='\n' or 0x20<=ord(c)<=0xd7ff or 0xe000<=ord(c)<=0xfffd or 0x10000<=ord(c)<=0x10ffff for c in value),'Invalid text type/XML characters/technical capacity')
    return value.strip()


def replace_text(p,value):
    """Locality-free paragraph/run mutation; preserve paragraph and run properties."""
    runs=p.findall('w:r',N)
    if runs:
        r=runs[0]
        for child in list(r):
            if child.tag!='{'+W+'}rPr':r.remove(child)
        for extra in runs[1:]:p.remove(extra)
    else:
        r=E.SubElement(p,'{'+W+'}r');pr=p.find('w:pPr/w:rPr',N)
        if pr is not None:r.append(deepcopy(pr))
    t=E.SubElement(r,'{'+W+'}t');t.set('{http://www.w3.org/XML/1998/namespace}space','preserve');t.text=value


def candidate_fill(payload,*,root):
    profile,kind,values=validate_request(payload,root=root);raw=path_at(root,profile['templates'][kind]['source_file']).read_bytes()
    active=any(values[k] for k in APP_FIELDS if k!='requests') or any(values['requests']) if kind=='application' else any(any(row.values()) for row in values['evidenceList'])
    if not active:return raw
    document=blank_layout(raw,kind);ps=document.findall('w:body/w:p',N)
    if kind=='application':
        for index,key,label in [(2,'applicantName','申请人：'),(3,'agentName','委托代理人：'),(4,'respondentName','被申请人：')]:
            if values[key]:replace_text(ps[index],label+values[key])
        for i,p in enumerate(ps[7:10]):
            if i<len(values['requests']) and values['requests'][i]:p.findall('.//w:t',N)[1].text=values['requests'][i]
        if values['factsReason']:replace_text(ps[11],values['factsReason'])
        # Committee text and every signature/date run stay unchanged.
        for p in ps[15:20]:
            pr=p.find('w:pPr',N)
            if pr is None:pr=E.Element('{'+W+'}pPr');p.insert(0,pr)
            keep=pr.find('w:keepNext',N)
            if keep is None:keep=E.SubElement(pr,'{'+W+'}keepNext')
            keep.set('{'+W+'}val','1')
    else:
        table=document.find('.//w:tbl',N);rows=table.findall('w:tr',N);items=[row for row in values['evidenceList'] if any(row.values())]
        E.SubElement(rows[0].find('w:trPr',N),'{'+W+'}tblHeader')
        for unused in rows[1+len(items):-1]:table.remove(unused)
        rows=table.findall('w:tr',N)
        while len(rows)-2<len(items):
            node=deepcopy(rows[1]);table.insert(list(table).index(rows[-1]),node);rows=table.findall('w:tr',N)
        for i,row in enumerate(rows[1:-1]):
            E.SubElement(row.find('w:trPr',N),'{'+W+'}cantSplit');item=items[i]
            fields=[str(i+1),item['name'],item['pageCount'],item['originalType'],item['purpose'],item['pageRange']]
            for cell,value in zip(row.findall('w:tc',N),fields):replace_text(cell.find('w:p',N),value)
        pages=str(sum(int(row['pageCount']) for row in items)) if all(row['pageCount'] for row in items) else '____'
        replace_text(rows[-1].find('w:tc/w:p',N),f'以上证据材料合计 {len(items)}份（组） {pages}页')
    xml=E.tostring(document,encoding='UTF-8',xml_declaration=True,standalone=True);out=BytesIO()
    with ZipFile(BytesIO(raw)) as src,ZipFile(out,'w') as result:
        for member in src.infolist():result.writestr(member,xml if member.filename=='word/document.xml' else src.read(member.filename))
    return out.getvalue()


class _PatchedDocument:
    def __init__(self,body,root):self.body=body;self.root=Path(root).resolve()
    def save(self,destination):
        if hasattr(destination,'write'):destination.write(self.body);return
        target=Path(destination).resolve();require(not target.is_relative_to(self.root/'reports'),'Do not overwrite own source/proof');target.write_bytes(self.body)
def fill_document(g,t,kind,path,data,*,root):
    checked_adapter(g,t,kind,root=root);require(Path(path).resolve()==template_path(g['region_code'],kind,root=root),'Own original path differs')
    return _PatchedDocument(candidate_fill(envelope(g['region_code'],kind,data,root=root),root=root),root)
def example_data(code,kind,stress=False,*,root):
    _kind(code,kind);_word_manifest(root);fixture=_read(root,QA_REPORT+f'/fixtures/{code}-'+('stress' if stress else 'normal')+f'-{kind}.json')
    require(exact(fixture['request'],envelope(code,kind,fixture['data'],root=root)),'Own fictional fixture context differs');return deepcopy(fixture['data'])
