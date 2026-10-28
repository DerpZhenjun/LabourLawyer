"""Four synthetic outputs from each locality's own independently fetched blanks."""
import hashlib,importlib.util,json,sys
from pathlib import Path
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from regional_blank_documents import fill_blank_document,blank_binding
OUT=ROOT/'reports/nationwide-localization-20261028/jiangsu/document-qa'

def main():
    OUT.mkdir(parents=True,exist_ok=True);files=[];checks=[]
    for code in ['320903','320902']:
        guide=json.loads((OUT.parent/code/'normalized-guide.json').read_text('utf8'))
        for template in guide['templates']:
            kind=blank_binding(guide,template)
            if not kind:continue
            source=ROOT/template['file'];before=hashlib.sha256(source.read_bytes()).hexdigest()
            assert before==template['sha256']
            data={'committeeName':'盐城市'+guide['district']+'劳动人事争议仲裁委员会','applicantName':'排版测试劳动者',
                  'respondentName':'虚构排版验证公司','requests':['请求支付测试工资100元。'],
                  'factsReason':'仅用于软件排版验证，所有姓名、单位及请求均为虚构。双方对测试工资存在争议。',
                  'copyCount':2,'evidenceCopyCount':2,
                  'evidenceList':[{'name':'测试劳动合同','purpose':'仅用于排版测试，说明测试劳动关系。',
                                   'pageCount':'3页','itemCount':'1','originalType':'复印件','source':'本人保存'}]}
            target=OUT/(code+'-'+kind+'.docx');assert not target.exists()
            fill_blank_document(guide,template,kind,source,data).save(target)
            with ZipFile(source) as original,ZipFile(target) as final:
                assert set(original.namelist())==set(final.namelist())
                untouched=[n for n in original.namelist() if n!='word/document.xml']
                assert all(original.read(n)==final.read(n) for n in untouched)
            assert hashlib.sha256(source.read_bytes()).hexdigest()==before
            files.append(target);checks.append(dict(region_code=code,kind=kind,source=template['file'],source_sha256=before,
                generated=str(target.relative_to(ROOT)),generated_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
                unchanged_package_parts=len(untouched)))
    assert len(files)==4
    (OUT/'package-checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({'outputs':[str(p) for p in files],'package_checks':'PASS'}))

if __name__=='__main__':main()
