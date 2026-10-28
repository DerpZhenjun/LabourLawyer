"""Task-only local original/filled-document checks; no network, DB or models."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from zipfile import ZipFile
from lxml import etree
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'backend'))
from regional_blank_documents import blank_binding,fill_blank_document
BASE=ROOT/'reports/nationwide-localization-20261028-next/jiangsu'
RUNTIME=Path('C:/Users/DerpZhenjun/.cache/codex-runtimes/codex-primary-runtime/dependencies')
NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(name,value):(OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf8')
def own():
    for code in ['320922','320921']:
        guide=json.loads((BASE/code/'normalized-guide.json').read_text('utf8'))
        for template in guide['templates']:
            kind=blank_binding(guide,template)
            if kind:yield code,guide,template,kind,ROOT/template['file']
def data(guide):
    return dict(committeeName=guide['district']+'劳动人事争议仲裁委员会',
        applicantName='虚构测试甲',gender='女',birthDate='1990-01-02',idNumber='000000199001020000',
        idAddress='虚构测试路1号',applicantMailingAddress='虚构收件路2号',phone='00000000000',
        acceptMediation='是',legalAid='否',respondentName='虚构测试单位有限公司',respondentType='有限责任公司',
        registeredAddress='虚构单位路3号',socialCreditCode='TESTONLY0000000001',legalRepName='虚构测试乙',legalRepPosition='经理',
        departmentHead='虚构测试丙',departmentHeadPosition='主管',mailingAddress='虚构单位收件路4号',
        companyContact='虚构测试丁',companyContactPhone='00000000001',
        requests=['请求支付虚构测试工资100元。'],factsReason='本文件仅用于软件测试，全部姓名、号码、地址、单位和事实均为虚构。双方对虚构测试工资存在争议。',
        copyCount=3,evidenceCopyCount=2,evidenceList=[dict(name='虚构劳动合同',purpose='仅用于软件测试，说明虚构劳动关系。',
        source='虚构本人保存',originalType='复印件',itemCount='1',pageCount='3页')])
def inspect():
    records=[]
    for code,g,t,kind,source in own():
        assert sha(source)==t['sha256']
        with ZipFile(source) as z:
            dom=etree.fromstring(z.read('word/document.xml'))
            records.append(dict(region_code=code,kind=kind,source=source.relative_to(ROOT).as_posix(),sha256=sha(source),
                source_url=g['source_url'],annex_id=t['id'],
                geometry=[etree.tostring(x,encoding='unicode') for x in dom.xpath('//w:sectPr',namespaces=NS)],
                paragraphs=[''.join(p.xpath('.//w:t/text()',namespaces=NS)) for p in dom.xpath('//w:body/w:p',namespaces=NS)],
                tables=[[[''.join(c.xpath('.//w:t/text()',namespaces=NS)) for c in row.xpath('./w:tc',namespaces=NS)] for row in table.xpath('./w:tr',namespaces=NS)] for table in dom.xpath('//w:tbl',namespaces=NS)],
                package_parts=[dict(name=n,size=len(z.read(n)),sha256=hashlib.sha256(z.read(n)).hexdigest(),editable=n=='word/document.xml') for n in z.namelist()]))
    save('reference-inventory.json',records)
def generate():
    records=[]
    for code,g,t,kind,source in own():
        before=sha(source);assert before==t['sha256'];target=OUT/(code+'-'+kind+'.docx');assert not target.exists()
        fill_blank_document(g,t,kind,source,data(g)).save(target)
        with ZipFile(source) as a,ZipFile(target) as b:
            assert a.namelist()==b.namelist()
            changed=[n for n in a.namelist() if a.read(n)!=b.read(n)];assert changed==['word/document.xml']
            preserved=[n for n in a.namelist() if n!='word/document.xml']
        assert sha(source)==before
        records.append(dict(region_code=code,kind=kind,source=t['file'],source_url=g['source_url'],annex_id=t['id'],
            source_sha256=before,output=target.relative_to(ROOT).as_posix(),output_sha256=sha(target),
            changed_parts=changed,preserved_package_parts=len(preserved),synthetic_only=True))
    assert len(records)==4;save('package-checks.json',records)
def render(reference=False):
    items=[];seen=set()
    if reference:
        for code,g,t,kind,source in own():
            if sha(source) in seen:continue
            seen.add(sha(source));items.append((source,'reference-'+kind))
    else:
        items=[(ROOT/r['output'],r['region_code']+'-'+r['kind']) for r in json.loads((OUT/'package-checks.json').read_text('utf8'))]
    tasks=[]
    for source,label in items:
        folder=OUT/'render'/label;folder.mkdir(parents=True,exist_ok=True)
        assert not (folder/'document.pdf').exists()
        tasks.append(dict(source=str(source),pdf=str(folder/'document.pdf'),sha256=sha(source),label=label))
    save('reference-render-input.json' if reference else 'render-input.json',tasks)
    command=['powershell.exe','-NoLogo','-NoProfile','-NonInteractive','-File',str(Path(__file__).with_name('render.ps1')),'-Manifest',str(OUT/('reference-render-input.json' if reference else 'render-input.json'))]
    r=subprocess.run(command,capture_output=True,text=True,timeout=180,creationflags=subprocess.CREATE_NO_WINDOW)
    (OUT/('reference-render.log' if reference else 'render.log')).write_text(r.stdout+'\n'+r.stderr,encoding='utf8')
    assert r.returncode==0,r.stderr
    from pypdf import PdfReader
    manifest=[]
    for task in tasks:
        pdf=Path(task['pdf']);assert pdf.exists() and sha(Path(task['source']))==task['sha256']
        result=subprocess.run([str(RUNTIME/'native/poppler/Library/bin/pdftoppm.exe'),'-png','-scale-to','1600',str(pdf),str(pdf.parent/'page')],capture_output=True,text=True,timeout=120,creationflags=subprocess.CREATE_NO_WINDOW)
        assert result.returncode==0,result.stderr
        pages=sorted(pdf.parent.glob('page-*.png'));assert len(pages)==len(PdfReader(pdf).pages)
        manifest.append(dict(**task,pages=len(pages),page_images=[p.relative_to(ROOT).as_posix() for p in pages],engine='own hidden read-only Word PDF export + bundled Poppler; packaged soffice unavailable'))
    save('reference-render-manifest.json' if reference else 'render-manifest.json',manifest)
def finalize():
    fixed=OUT/'birth-date-fixed';checks=json.loads((fixed/'package-checks.json').read_text('utf8'))
    renders=json.loads((fixed/'render-manifest.json').read_text('utf8'))
    assert len(checks)==4 and sum(r['pages'] for r in renders)==6
    for record in checks:
        assert sha(ROOT/record['source'])==record['source_sha256']
        assert sha(ROOT/record['output'])==record['output_sha256']
        with ZipFile(ROOT/record['source']) as a,ZipFile(ROOT/record['output']) as b:
            assert a.namelist()==b.namelist()
            assert [n for n in a.namelist() if a.read(n)!=b.read(n)]==['word/document.xml']
        match=next(r for r in renders if Path(r['source']).resolve()==(ROOT/record['output']).resolve())
        assert match['sha256']==record['output_sha256']
        record.update(pages=match['pages'],visual_status='PASS',viewed_page_images=match['page_images'],
            handwritten_signature_blank=True,handwritten_date_blank=True)
    save('document-approval.json',dict(status='PASS_OFFLINE_DOCUMENT_QA_ONLY',files=checks,
        reference_pages_viewed=7,initial_failed_pages_viewed=6,final_pages_viewed=6,total_page_images_opened=19,
        corrected_issue='JiangSuSheng expanded birth date wrapped month/day; compact ISO preserves source run properties.',
        original_sha_mismatches=0,non_document_package_part_mismatches=0,full_suite_run=False,
        tests=dict(targeted=8,jiangsu=34,jiangsu_seconds=1.803),published=False,generation_enabled=False,
        product_web_qa_status='NOT_RUN',online_submission_verified=False,
        restrictions=dict(db_writes=False,services_started=False,model_calls=False,git_operations=False)))
    files=[ROOT/'backend/WenShu/exact_template_fill.py',ROOT/'backend/tests/test_jiangsu_binhai_xiangshui_document_qa.py']
    files += [OUT/name for name in ['qa.py','render.ps1','artifact.md','visual-review.md','document-approval.json',
        'reference-inventory.json','reference-render-manifest.json','reference-style-audit.json','reference-section-audit.txt',
        'packaged-render-probe.log','birth-date-red.txt','birth-date-green.txt','jiangsu-tests.txt']]
    files += [fixed/'package-checks.json',fixed/'render-manifest.json']
    files += [ROOT/r['output'] for r in checks]
    files += [ROOT/p for r in renders for p in r['page_images']]
    save('public-file-allowlist.json',dict(scope='Explicit safe synthetic QA and code files; not a publication approval.',
        files=[dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p)) for p in files],
        excluded=['Initial root-level DOCX/render files contain the superseded date-wrap defect.',
                  'No env/auth/connection configuration or model files are in this list.']))
if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf8');p=argparse.ArgumentParser();p.add_argument('action',choices=['inspect','generate','render-reference','render','generate-fixed','render-fixed','finalize']);a=p.parse_args()
    if a.action.endswith('-fixed'):
        OUT=OUT/'birth-date-fixed';OUT.mkdir(exist_ok=True);a.action=a.action[:-6]
    if a.action=='inspect':inspect()
    elif a.action=='generate':generate()
    elif a.action=='finalize':finalize()
    else:render(a.action=='render-reference')
    print(a.action,'completed')
