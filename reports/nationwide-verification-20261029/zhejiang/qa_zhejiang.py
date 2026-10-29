"""Fictional own-source DOCX build, preserved-package checks and read-only QA."""
from pathlib import Path
import hashlib,json,subprocess,sys
from zipfile import ZipFile
from docx import Document
from pypdf import PdfReader

OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[2]
sys.path.insert(0,str(ROOT/'backend'))
from regional_zhejiang_oct29 import parse_capture,with_capabilities,fill_document,blank_binding,SPECS
POPPLER=Path('C:/Users/DerpZhenjun/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe')

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,value):
    p=OUT/p;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf8')

def build():
    records=[];tasks=[];payloads={}
    for name,spec in SPECS.items():
        g=with_capabilities(parse_capture(name));save(name+'/guide.json',g)
        data={'committeeName':'宁波市'+spec['district']+'劳动人事争议仲裁委员会','applicantName':'虚构'+spec['district']+'测试甲','birthDate':'1990-01-02',
            'gender':'女','nationality':'汉族','idNumber':'TEST-ID-ONLY','phone':'','householdType':'本省非农业户口','idAddress':'虚构测试住址一号',
            'respondentName':'虚构'+spec['district']+'测试公司乙','socialCreditCode':'TEST-CREDIT-ONLY','registeredAddress':'虚构注册地址二号','mailingAddress':'虚构通讯地址三号',
            'workAddress':'虚构劳动合同履行地四号','legalRepName':'虚构负责人丙','legalRepPosition':'测试负责人','legalRepPhone':'',
            'companyContact':'虚构联系人丁','companyContactPhone':'','applicationDate':'2026-10-29','submitDate':'2026-10-29','caseNumber':'测试案号不用于实际办理'}
        facts='本文件全部内容均为软件排版测试虚构示例，不用于真实仲裁。测试双方围绕虚构工资及经济补偿发生争议。'
        facts+='申请人与被申请人的名称、地址、日期及金额均为虚构，仅用于检查官方表格的换行和分页。'*4
        values={'application':{**data,'requests':['请求支付虚构测试工资100元。','请求支付虚构测试经济补偿200元。'],'factsReason':facts},
            'evidence':{**data,'submitterName':'不可自动填写手签','evidenceList':[{'name':f'虚构测试证据{i}','pageCount':'2页','source':'虚构测试材料，由测试人员保存',
                'purpose':f'第{i}项仅用于验证本区官方证据表的文字换行和八项证据扩展，不是实际证据。'} for i in range(1,9)]}}
        payloads[name]=values
        for template in g['templates'][:2]:
            kind=blank_binding(g,template);source=ROOT/template['file'];destination=OUT/'qa'/name/(kind+'-synthetic.docx');destination.parent.mkdir(parents=True,exist_ok=True)
            if destination.exists():raise ValueError('Do not overwrite retained QA revision')
            before=sha(source);fill_document(g,template,kind,source,values[kind]).save(destination)
            with ZipFile(source) as a,ZipFile(destination) as b:
                assert set(a.namelist())==set(b.namelist());changed=[n for n in a.namelist() if a.read(n)!=b.read(n)]
            assert changed==['word/document.xml'] and sha(source)==before
            document=Document(source)
            records.append({'district':name,'kind':kind,'source':str(source.relative_to(ROOT)),'source_sha256':before,'output':str(destination.relative_to(OUT)),
                'output_sha256':sha(destination),'changed_parts':changed,'table_shapes':[[len(t.rows),len(t.columns)] for t in document.tables],
                'sections':[{'width':s.page_width.twips,'height':s.page_height.twips,'margins':[s.top_margin.twips,s.bottom_margin.twips,s.left_margin.twips,s.right_margin.twips]} for s in document.sections]})
            for role,p in [('original',source),('filled',destination)]:
                folder=OUT/'render'/name/(role+'-'+kind);folder.mkdir(parents=True,exist_ok=True)
                tasks.append({'source':str(p),'source_sha256':sha(p),'pdf':str(folder/'document.pdf'),'district':name,'role':role,'kind':kind})
    save('qa/package-checks.json',records);save('qa/synthetic-payloads.json',payloads);save('render/inputs.json',tasks)
    print(json.dumps({'files':len(records),'render_tasks':len(tasks)}))

def render(raster_only=False):
    tasks=json.loads((OUT/'render/inputs.json').read_text(encoding='utf8'))
    if not raster_only:
        result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-File',str(OUT/'render-isolated.ps1'),'-Manifest',str(OUT/'render/inputs.json')],capture_output=True,text=True,timeout=180,creationflags=subprocess.CREATE_NO_WINDOW)
        (OUT/'render/word-render.log').write_text(result.stdout+'\n'+result.stderr,encoding='utf8')
        if result.returncode:raise RuntimeError(result.stdout+result.stderr)
    for task in tasks:
        assert sha(task['source'])==task['source_sha256'];pdf=Path(task['pdf'])
        subprocess.run([str(POPPLER),'-r','110','-png',str(pdf),str(pdf.parent/'page')],check=True,timeout=60,creationflags=subprocess.CREATE_NO_WINDOW)
        reader=PdfReader(pdf);text='\n'.join(p.extract_text() for p in reader.pages)
        task.update(pdf_sha256=sha(pdf),pages=[str(p.relative_to(OUT)).replace('\\','/') for p in sorted(pdf.parent.glob('page-*.png'))],page_count=len(reader.pages))
        (pdf.parent/'text.txt').write_text(text,encoding='utf8')
        if task['role']=='filled':
            assert '不可自动填写手签' not in text and '虚构' in text
            if task['kind']=='application':assert '2026' in text and '100' in text and '200' in text
            else:assert '虚构测试证据8' in ''.join(text.split()) and '测试案号' in text
    isolation=json.loads((OUT/'render/word-instance-isolation.json').read_text(encoding='utf-8-sig'))
    assert isolation['completed']==8 and isolation['new_pid_verified'] and isolation['original_pids_still_alive']
    save('render-result.json',{'engine':'isolated Word read-only + bundled Poppler','tasks':tasks,'sources_unchanged':True,'isolation':isolation,'visual_status':'PENDING_INDIVIDUAL_PAGE_INSPECTION'})
    print(json.dumps([{'district':t['district'],'role':t['role'],'kind':t['kind'],'pages':t['page_count']} for t in tasks]))

if __name__=='__main__':{'build':build,'render':render,'rasterize':lambda:render(True)}[sys.argv[1]]()
