"""Own-source fictional QA only; native Word is coordinated by the parent agent."""
from datetime import datetime,timezone
import hashlib,json,subprocess,sys
from pathlib import Path
from zipfile import ZipFile
from docx import Document
from pypdf import PdfReader

OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[2]
sys.path.insert(0,str(ROOT/'backend'))
from regional_zhejiang_more import parse_shangcheng_capture,parse_binjiang_capture,REPORT
from regional_shangcheng_documents import with_shangcheng_capabilities,shangcheng_blank_binding,fill_shangcheng_document
POPPLER=Path(r'C:/Users/DerpZhenjun/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe')
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(name,value):
    path=OUT/name;path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf8')
def own():return with_shangcheng_capabilities(parse_shangcheng_capture(ROOT/REPORT,ROOT/REPORT/'SOURCE-MANIFEST.json'))
def selected(kind):
    g=own();return g,next(t for t in g['templates'] if shangcheng_blank_binding(g,t)==kind)
def audit():
    g=own();records=[]
    for t in g['templates']:
        p=ROOT/t['file'];d=Document(p)
        records.append({'annex_id':t['official_annex_id'],'source_url':t['download_url'],'guide_url':g['source_url'],
            'canonical_file':t['file'],'sha256':sha(p),'bytes':p.stat().st_size,
            'table_shapes':[[len(x.rows),len(x.columns)] for x in d.tables],
            'sections':[{'width_twips':s.page_width.twips,'height_twips':s.page_height.twips,
                'margins_twips':[s.top_margin.twips,s.bottom_margin.twips,s.left_margin.twips,s.right_margin.twips]} for s in d.sections],
            'supported_kind':t['document_types'],'supported_applicant':t.get('supported_applicant')})
    safe={k:g[k] for k in ['province','city','district','region_code','source_id','source_url','service_code','authority','collected_at']}
    safe.update(originals=records,publication='NOT_PUBLISHED',web='NOT_RUN_POLICY_REFUSAL_RETAINED',online_status='auth_required_post_login_unknown',
        material_count=4,raw_window_hours=g['fields']['办理时间']['raw_value'],
        material_notice='仅保留实际四项公开材料，不推断身份证或委托手续免交；份数冲突仍须机构核实。')
    save('public-source-provenance.json',safe)
    save('field-audit.json',{'source_id':g['source_id'],'application_worker':{
        'applicantName':[1,1],'birthDate':[1,4],'gender':[2,1],'nationality':[2,4],'idNumber':[3,1],'phone':[3,4],
        'householdType':[4,1],'idAddress':[5,2],'respondentName':[7,2],'socialCreditCode':[8,2],
        'registeredAddress':[9,2],'mailingAddress':[10,2],'workAddress':[11,2],'legalRepName':[12,2],
        'legalRepPhone':[12,4],'legalRepPosition':[13,4],'companyContact':[14,2],'companyContactPhone':[14,4],
        'requests_rows':[16,17,18,19],'factsReason':[21,0],'closing_row':22,'request_capacity':4,
        'signature_policy':'handwritten applicant slot remains empty; employer form not filled'},
        'evidence':{'first_data_row':2,'columns':{'number':0,'name':1,'pageCount':3,'source':4,'purpose':5},
            'extension':'clone own original data row; submitting and receiving signatures stay blank'},'originals':records})
    return safe
def build():
    # Explicitly fictional markers only, with no valid personal ID or phone.
    common={'committeeName':'杭州市上城区劳动人事争议仲裁委员会','applicantName':'虚构上城测试甲','birthDate':'1990-01-02',
        'gender':'女','nationality':'汉族','idNumber':'TEST-ID-ONLY','phone':'','householdType':'本省非农业户口',
        'idAddress':'虚构测试住址一号','respondentName':'虚构上城测试单位乙','socialCreditCode':'TEST-CREDIT-ONLY',
        'registeredAddress':'虚构单位注册地址二号','mailingAddress':'虚构单位通讯地址三号','workAddress':'虚构劳动合同履行地四号',
        'legalRepName':'虚构负责人丙','legalRepPosition':'测试负责人','legalRepPhone':'','companyContact':'虚构联系人丁',
        'companyContactPhone':'','copyCount':2,'applicationDate':'2026-10-28','submitDate':'2026-10-28','caseNumber':'测试案号不用于实际办理'}
    facts='本文件全部内容均为软件排版测试虚构示例，不用于真实仲裁。测试双方围绕虚构工资及经济补偿发生争议。'
    facts+='申请人与被申请人的名称、地址、日期及金额均为虚构，仅用于检查官方表格的换行和分页。'*6
    payloads={'application':{**common,'requests':['请求支付虚构测试工资100元。','请求支付虚构测试经济补偿200元。'], 'factsReason':facts},
        'evidence':{**common,'submitterName':'不可自动填写签名','evidenceList':[{'name':f'虚构测试证据{i}', 'pageCount':'2页',
            'source':'虚构测试材料，由测试人员保存','purpose':'仅用于验证本区官方证据表的较长文字换行和十项证据扩展，不是实际证据。'} for i in range(1,11)]}}
    checks=[]
    for kind,data in payloads.items():
        g,t=selected(kind);source=ROOT/t['file'];before=sha(source)
        dest=OUT/(kind+'-synthetic.docx')
        if dest.exists():raise ValueError('Do not overwrite prior QA output')
        fill_shangcheng_document(g,t,kind,source,data).save(dest)
        with ZipFile(source) as a,ZipFile(dest) as b:
            assert set(a.namelist())==set(b.namelist())
            changed=[n for n in a.namelist() if a.read(n)!=b.read(n)]
            assert changed==['word/document.xml']
        assert sha(source)==before
        checks.append({'kind':kind,'source_file':t['file'],'source_sha256':before,'generated':dest.name,
            'generated_sha256':sha(dest),'changed_package_parts':changed,'fictional_payload':True})
    save('synthetic-payloads.json',payloads);save('package-checks.json',checks)
    return checks
def render(mode):
    probe=subprocess.run(['powershell.exe','-NoProfile','-Command','@(Get-Process WINWORD -ErrorAction SilentlyContinue).Count'],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
    if probe.stdout.strip()!='0':raise RuntimeError('Existing WINWORD present; left untouched, waiting for coordinated slot')
    if mode=='reference':
        g=own();paths=[ROOT/t['file'] for t in g['templates']]
        labels=['original-application' if '21B24C52' in p.name else 'original-evidence' for p in paths]
    elif mode=='fixed-evidence':paths=[OUT/'evidence-synthetic-fixed.docx'];labels=['fixed-evidence']
    else:paths=[OUT/'application-synthetic.docx',OUT/'evidence-synthetic.docx'];labels=['filled-application','filled-evidence']
    tasks=[]
    for p,label in zip(paths,labels):
        folder=OUT/'render'/label;folder.mkdir(parents=True,exist_ok=True)
        tasks.append({'source':str(p.resolve()),'pdf':str((folder/'document.pdf').resolve()),'label':label,'source_sha256':sha(p)})
    save('render/'+mode+'-inputs.json',tasks)
    script=OUT/'render'/'export-own-readonly.ps1'
    script.write_text('''param([string]$Manifest)
$ErrorActionPreference='Stop'
$items=Get-Content -LiteralPath $Manifest -Raw -Encoding UTF8 | ConvertFrom-Json
$word=$null
try {
 $word=New-Object -ComObject Word.Application
 $word.Visible=$false
 $word.DisplayAlerts=0
 $word.AutomationSecurity=3
 foreach($item in $items) {
  $document=$null
  try {
   $document=$word.Documents.Open($item.source,$false,$true,$false)
   $document.ExportAsFixedFormat($item.pdf,17)
  } finally {if($null -ne $document){$document.Close($false)}}
 }
} finally {if($null -ne $word){$word.Quit()};[GC]::Collect();[GC]::WaitForPendingFinalizers()}
''',encoding='utf-8-sig')
    result=subprocess.run(['powershell.exe','-NoLogo','-NoProfile','-NonInteractive','-File',str(script),'-Manifest',str(OUT/'render'/(mode+'-inputs.json'))],capture_output=True,text=True,timeout=120,creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:raise RuntimeError(result.stdout+result.stderr)
    for item in tasks:
        assert sha(item['source'])==item['source_sha256']
        pdf=Path(item['pdf']);assert pdf.is_file()
        subprocess.run([str(POPPLER),'-r','115','-png',str(pdf),str(pdf.parent/'page')],check=True,timeout=60,creationflags=subprocess.CREATE_NO_WINDOW)
        item['pages']=[str(p.relative_to(OUT)).replace('\\','/') for p in sorted(pdf.parent.glob('page-*.png'))]
        item['pdf_sha256']=sha(pdf);reader=PdfReader(pdf)
        item['page_texts']=[p.extract_text() or '' for p in reader.pages]
        item['page_count']=len(reader.pages)
    save(mode+'-render.json',{'engine':'Microsoft Word own hidden read-only PDF export + bundled Poppler',
        'packaged_renderer':'failed: no soffice.exe; packaged-render.log retained','tasks':tasks,'source_files_unchanged':True})
    print(json.dumps({'mode':mode,'page_counts':[t['page_count'] for t in tasks],'pages':[p for t in tasks for p in t['pages']]},ensure_ascii=False))
def fixed_evidence():
    payload=json.loads((OUT/'synthetic-payloads.json').read_text(encoding='utf8'))['evidence']
    g,t=selected('evidence');source=ROOT/t['file'];before=sha(source);dest=OUT/'evidence-synthetic-fixed.docx'
    if dest.exists():raise ValueError('Do not overwrite retained revision')
    fill_shangcheng_document(g,t,'evidence',source,payload).save(dest)
    with ZipFile(source) as a,ZipFile(dest) as b:
        changed=[n for n in a.namelist() if a.read(n)!=b.read(n)]
        assert changed==['word/document.xml']
    assert sha(source)==before
    save('evidence-fix-package.json',{'source_sha256':before,'generated':dest.name,'generated_sha256':sha(dest),
        'changed_package_parts':changed,'supersedes':'evidence-synthetic.docx','fixes':['case label remains 案号','repeat original header rows','do not split evidence records across pages']})
if __name__=='__main__':
    command=sys.argv[1]
    if command=='audit':print(json.dumps(audit(),ensure_ascii=False))
    elif command=='build':print(json.dumps(build(),ensure_ascii=False))
    elif command=='build-fixed-evidence':fixed_evidence()
    elif command in {'reference','generated','fixed-evidence'}:render(command)
    else:raise ValueError('Unknown offline QA command')
