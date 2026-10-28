"""Two synthetic own-reference outputs; original inputs never saved or replaced."""
import argparse,hashlib,importlib,json,subprocess,sys
from pathlib import Path
from zipfile import ZipFile
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'backend'),str(ROOT/'scripts')]
from regional_rongjiang_documents import fill_rongjiang_document,REFERENCE,REFERENCE_SHA
BASE=ROOT/'reports/nationwide-localization-20261023-night/cross-province/jiangxi-rongjiang'
OUT=BASE/'document-qa/generated-0455'
SKILL=Path('C:/Users/DerpZhenjun/.codex/plugins/cache/openai-primary-runtime/documents/26.1017.11052/skills/documents')
qa=importlib.import_module('verify-regional-documents')

def main():
    global OUT
    parser=argparse.ArgumentParser();parser.add_argument('--iteration',default='generated-0455');args=parser.parse_args()
    if not args.iteration.replace('-','').isalnum():raise ValueError('Invalid bounded iteration name')
    OUT=BASE/'document-qa'/args.iteration
    if OUT.exists():raise ValueError('Preserve existing authoring/QA iteration')
    OUT.mkdir();qa.OUT=OUT
    g=json.loads((BASE/'guide.json').read_text(encoding='utf8'));t=g['templates'][0]
    reference=ROOT/REFERENCE
    assert hashlib.sha256(reference.read_bytes()).hexdigest()==REFERENCE_SHA
    samples={
      'application':{'applicantName':'合成测试甲','gender':'女','birthDate':'1990-02-03','nationality':'汉族',
        'idNumber':'仅用于排版测试','phone':'测试联系方式','idAddress':'合成测试户籍地址',
        'applicantMailingAddress':'江西省赣州市蓉江新区合成测试通讯地址','applicantPostalCode':'341000',
        'respondentName':'蓉江合成测试有限公司','socialCreditCode':'仅用于排版测试',
        'registeredAddress':'合成测试注册地址','actualOfficeAddress':'合成测试办公地址',
        'respondentPostalCode':'341000','companyContactPhone':'测试公司电话',
        'legalRepName':'合成负责人','legalRepPosition':'负责人','applicationDate':'2026-10-24',
        'requests':['支付合成测试工资100元。','支付另一项合成测试款项50元。','本项仅检查超过原表两项请求时的自动编号和分页。'],
        'factsReason':'本文件仅用于排版测试，不用于真实申请。'+('测试劳动关系与工资约定说明，检查长内容能否自然换行和分页。'*12)},
      'evidence':{'submitterName':'不应替代手写签名','submitDate':'2026-10-24',
        'evidenceList':[{'name':f'合成测试证据第{i}项','source':'本人保存的合成测试材料',
        'purpose':'仅用于排版测试，不用于实际申请。'+('用于说明合成测试劳动关系和工资支付情况。'*3),
        'pageCount':str(i)} for i in range(1,13)]}}
    outputs=[]
    for kind,data in samples.items():
        path=OUT/(kind+'-synthetic.docx')
        fill_rongjiang_document(g,t,kind,ROOT/t['file'],data).save(path)
        with ZipFile(reference) as before,ZipFile(path) as after:
            for part in before.namelist():
                if part!='word/document.xml':assert before.read(part)==after.read(part),part
        # Canonical renderer is tried first; only known missing bundled soffice
        # permits the already inspected own read-only Word fallback.
        probe=subprocess.run([sys.executable,str(SKILL/'render_docx.py'),str(path),
            '--output_dir',str(OUT/('packaged-'+kind)),'--emit_pdf','--verbose'],capture_output=True,text=True,encoding='utf8',errors='replace')
        (OUT/('packaged-'+kind+'.log')).write_text(probe.stdout+'\n'+probe.stderr,encoding='utf8')
        if probe.returncode and 'soffice.exe' not in probe.stderr:raise RuntimeError('Unexpected renderer failure')
        outputs.append(path)
    tasks=qa.render(outputs)
    for tsk in tasks:
        tsk['sha256']=hashlib.sha256(Path(tsk['source']).read_bytes()).hexdigest()
    assert hashlib.sha256(reference.read_bytes()).hexdigest()==REFERENCE_SHA
    assert hashlib.sha256((ROOT/t['file']).read_bytes()).hexdigest()==t['sha256']
    (OUT/'render-manifest.json').write_text(json.dumps({'tasks':tasks,'source_id':'9324666463f34ff63056367a',
        'reference':REFERENCE,'reference_sha256':REFERENCE_SHA,'original_sha256':t['sha256'],
        'models':0,'marker':'already invoked exactly once before first conversion in prior round; not repeated',
        'visual_review':'pending','preserve_only_package_parts':'byte_identical'},ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({'generated':[Path(x['source']).name for x in tasks],'pages':[len(x['pages']) for x in tasks]}))

if __name__=='__main__':main()
