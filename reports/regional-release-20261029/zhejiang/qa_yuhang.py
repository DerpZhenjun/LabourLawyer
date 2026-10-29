"""Own sealed Yuhang input, fictional output and coordinated read-only Word QA."""
from datetime import datetime,timezone
import hashlib,json,subprocess,sys
from pathlib import Path
from zipfile import ZipFile
from docx import Document
from pypdf import PdfReader

OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[2]
sys.path.insert(0,str(ROOT/'backend'))
from regional_zhejiang import parse_yuhang_capture,REPORT
from regional_zhejiang_documents import with_zhejiang_capabilities,zhejiang_blank_binding,fill_zhejiang_document
POPPLER=Path('C:/Users/DerpZhenjun/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe')
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(name,value):
    path=OUT/name;path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf8')
def own():return with_zhejiang_capabilities(parse_yuhang_capture(ROOT/REPORT,ROOT/REPORT/'SHA256-MANIFEST.json'))
def blanks():return [t for t in own()['templates'] if zhejiang_blank_binding(own(),t)]
def audit():
    g=own();records=[]
    for t in blanks():
        path=ROOT/t['file'];d=Document(path)
        with ZipFile(path) as z:parts={n:hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist()}
        records.append({k:t[k] for k in ['official_annex_id','file','sha256','bytes','download_url','source_url']})
        records[-1].update(table_shapes=[[len(x.rows),len(x.columns)] for x in d.tables],parts=parts,
            sections=[{'width':s.page_width.twips,'height':s.page_height.twips,'margins':[s.top_margin.twips,s.bottom_margin.twips,s.left_margin.twips,s.right_margin.twips]} for s in d.sections])
    save('source-audit.json',{'identity':{k:g[k] for k in ['region_code','city','district','authority','source_url','source_id','service_code','service_ids','collected_at']},
        'originals':records,'materials':[m['name'] for m in g['materials']],
        'times':{k:g['fields'][k]['raw_value'] for k in ['法定办结时限','承诺办结时限','办理时间']},
        'online':'prior own native login boundary retained; post-login flow unknown; no new online action in this recheck'})
def build():
    g=own();data={'committeeName':'杭州市余杭区劳动人事争议仲裁委员会','applicantName':'虚构余杭排版甲','birthDate':'1990-01-02',
        'gender':'女','nationality':'汉族','idNumber':'TEST-ID-ONLY','phone':'','householdType':'本省非农业户口','idAddress':'虚构测试住址一号',
        'respondentName':'虚构余杭单位乙','socialCreditCode':'TEST-CREDIT-ONLY','registeredAddress':'虚构注册地址二号','mailingAddress':'虚构通讯地址三号',
        'workAddress':'虚构劳动合同履行地四号','legalRepName':'虚构负责人丙','legalRepPosition':'测试负责人','legalRepPhone':'',
        'companyContact':'虚构联系人丁','companyContactPhone':'','applicationDate':'2026-10-29','submitDate':'2026-10-29','caseNumber':'测试案号不用于实际办理'}
    facts='本文件全部内容均为软件排版测试虚构示例，不用于真实仲裁。测试双方围绕虚构工资及经济补偿发生争议。'
    facts+='申请人与被申请人的名称、地址、日期及金额均为虚构，仅用于检查官方表格的换行和分页。'*6
    payloads={'application':{**data,'requests':['请求支付虚构测试工资100元。','请求支付虚构测试经济补偿200元。'],'factsReason':facts},
        'evidence':{**data,'submitterName':'不可自动填写手签','evidenceList':[{'name':f'虚构测试证据{i}','pageCount':'2页','source':'虚构测试材料，由测试人员保存',
            'purpose':f'第{i}项仅用于验证本区官方证据表的较长文字换行和十项证据扩展，不是实际证据。'} for i in range(1,11)]}}
    results=[]
    for kind,values in payloads.items():
        t=next(t for t in blanks() if zhejiang_blank_binding(g,t)==kind);source=ROOT/t['file'];before=sha(source);dest=OUT/(kind+'-synthetic.docx')
        if dest.exists():raise ValueError('Do not overwrite a retained QA revision')
        fill_zhejiang_document(g,t,kind,source,values).save(dest)
        with ZipFile(source) as a,ZipFile(dest) as b:
            assert set(a.namelist())==set(b.namelist());changed=[n for n in a.namelist() if a.read(n)!=b.read(n)]
        assert changed==['word/document.xml'] and sha(source)==before
        results.append({'kind':kind,'source':t['file'],'source_sha256':before,'output':dest.name,'output_sha256':sha(dest),'changed_parts':changed})
    save('synthetic-payloads.json',payloads);save('package-checks.json',results);print(json.dumps(results,ensure_ascii=False))
def render():
    tasks=[]
    for t in blanks():
        kind=zhejiang_blank_binding(own(),t)
        for role,source in [('original',ROOT/t['file']),('filled',OUT/(kind+'-synthetic.docx'))]:
            folder=OUT/'render'/(role+'-'+kind);folder.mkdir(parents=True,exist_ok=True)
            tasks.append({'source':str(source),'source_sha256':sha(source),'pdf':str(folder/'document.pdf'),'role':role,'kind':kind})
    save('render/inputs.json',tasks)
    script=OUT/'render-isolated.ps1'
    if not script.is_file():raise RuntimeError('Reviewed isolated-instance export script unavailable')
    result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-File',str(script),'-Manifest',str(OUT/'render/inputs.json')],capture_output=True,text=True,timeout=150,creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:raise RuntimeError(result.stdout+result.stderr)
    for task in tasks:
        assert sha(task['source'])==task['source_sha256'];pdf=Path(task['pdf'])
        subprocess.run([str(POPPLER),'-r','115','-png',str(pdf),str(pdf.parent/'page')],check=True,timeout=60,creationflags=subprocess.CREATE_NO_WINDOW)
        task.update(pdf_sha256=sha(pdf),pages=[str(p.relative_to(OUT)).replace('\\','/') for p in sorted(pdf.parent.glob('page-*.png'))],page_count=len(PdfReader(pdf).pages))
    isolation=json.loads((OUT/'render/word-instance-isolation.json').read_text(encoding='utf-8-sig'))
    assert isolation['completed']==4 and isolation['new_pid_verified'] and isolation['original_pids_still_alive']
    save('render-result.json',{'engine':'Microsoft Word isolated COM read-only export + bundled Poppler','tasks':tasks,'sources_unchanged':True,'instance_isolation':isolation})
    print(json.dumps([{'role':t['role'],'kind':t['kind'],'pages':t['page_count']} for t in tasks]))
if __name__=='__main__':{'audit':audit,'build':build,'render':render}[sys.argv[1]]()
