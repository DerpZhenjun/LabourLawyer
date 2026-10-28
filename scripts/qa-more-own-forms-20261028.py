"""Independent own-source synthetic outputs; no model, network or database writes."""
import hashlib,json,sys
from pathlib import Path
from zipfile import ZipFile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from regional_blank_documents import blank_binding,fill_blank_document
from regional_zhejiang_documents import zhejiang_blank_binding,fill_zhejiang_document
from regional_adapters import with_reference_capabilities
FINAL_ZHEJIANG='--zhejiang-final' in sys.argv
OUT=ROOT/'reports/nationwide-localization-20261028'/('form-qa-zhejiang-accepted' if FINAL_ZHEJIANG else 'form-qa-next')
def main():
    OUT.mkdir(parents=True,exist_ok=True);checks=[]
    profiles=[('zhejiang',['330110','330106'])] if FINAL_ZHEJIANG else [('jiangsu',['320981','320924']),('zhejiang',['330110','330106'])]
    for province,codes in profiles:
        for code in codes:
            relative=(f'jiangsu/{code}/normalized-guide.json' if province=='jiangsu' else f'zhejiang/staging-candidate/{code}-guide.json')
            g=with_reference_capabilities(json.loads((OUT.parent/relative).read_text('utf8')))
            binding,filler=(blank_binding,fill_blank_document) if province=='jiangsu' else (zhejiang_blank_binding,fill_zhejiang_document)
            for t in g['templates']:
                kind=binding(g,t)
                if not kind:continue
                source=ROOT/t['file'];before=hashlib.sha256(source.read_bytes()).hexdigest();assert before==t['sha256']
                data={'committeeName':g['city']+g['district']+'劳动人事争议仲裁委员会','applicantName':'虚构排版测试人员',
                      'gender':'男','birthDate':'1990-01-01','idNumber':'','phone':'','registeredAddress':'测试省测试市测试地址',
                      'respondentName':'虚构排版测试公司','companyAddress':'测试单位地址','workAddress':'测试工作地点',
                      'requests':['请求支付测试工资100元。'],'factsReason':'本文件全部内容均为软件测试虚构示例，不用于实际仲裁。测试双方存在工资争议。',
                      'copyCount':2,'evidenceCopyCount':2,'evidenceList':[{'name':'测试劳动合同','pageCount':'3页','source':'本人保存',
                      'originalType':'复印件','itemCount':'1','purpose':'仅用于测试，说明虚构劳动关系。'}]}
                out=OUT/(code+'-'+kind+'.docx');assert not out.exists()
                filler(g,t,kind,source,data).save(out)
                with ZipFile(source) as a,ZipFile(out) as b:
                    assert set(a.namelist())==set(b.namelist())
                    assert all(a.read(n)==b.read(n) for n in a.namelist() if n!='word/document.xml')
                assert hashlib.sha256(source.read_bytes()).hexdigest()==before
                checks.append({'region_code':code,'kind':kind,'source_id':g['source_id'],'source':t['file'],'source_sha256':before,
                               'generated':out.relative_to(ROOT).as_posix(),'generated_sha256':hashlib.sha256(out.read_bytes()).hexdigest()})
    assert len(checks)==(4 if FINAL_ZHEJIANG else 8)
    (OUT/'package-checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({'synthetic_docx_outputs':len(checks),'package_integrity':'PASS'}))
if __name__=='__main__':main()
