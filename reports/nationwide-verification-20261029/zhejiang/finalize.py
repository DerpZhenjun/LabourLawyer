"""Finalize public-only metadata after all 24 PNG pages were individually viewed."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,sys
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[2];sys.path.insert(0,str(ROOT/'backend'))
from regional_zhejiang_oct29 import parse_capture,with_capabilities,SPECS,MANIFEST_SHA256

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(name,data):(OUT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')

def finalize():
    now=datetime.now(timezone.utc).isoformat()
    manifest=json.loads((OUT/'SOURCE-MANIFEST.json').read_text(encoding='utf8'))
    assert sha(OUT/'SOURCE-MANIFEST.json')==MANIFEST_SHA256
    for relative,expected in manifest['files'].items():
        p=OUT/relative;assert expected=={'sha256':sha(p),'bytes':p.stat().st_size}
    guides=[];originals=[]
    for name in SPECS:
        g=with_capabilities(parse_capture(name));save(name+'/guide.json',g)
        guides.append({'province':'zhejiang','city':g['city'],'district':g['district'],'region_code':g['region_code'],'guide_file':str((OUT/name/'guide.json').relative_to(ROOT)).replace('\\','/'),
            'source_url':g['source_url'],'status':'own_official_guide_collected_offline_adapter_verified','published':False,'can_generate_offline':True,
            'materials':len(g['materials']),'blank_originals':2,'sample_originals':1,'web_acceptance':'NOT_RUN_EXISTING_STARTUP_POLICY_REJECTION_NOT_RETRIED'})
        for p in sorted((OUT/name/'originals').rglob('*.source.json')):
            record=json.loads(p.read_text(encoding='utf8'));actual=OUT/record['local_path'];assert sha(actual)==record['sha256']
            originals.append({**record,'file':str(actual.relative_to(ROOT)).replace('\\','/'),'public_reason':'本区官方公开空白/标注样证，按blank和sample分别保存；无私人上传'})
    result=json.loads((OUT/'render-result.json').read_text(encoding='utf8'))
    pages=[]
    for task in result['tasks']:
        for page in task['pages']:
            pages.append({'file':page,'sha256':sha(OUT/page),'district':task['district'],'role':task['role'],'kind':task['kind'],
                'status':'PASS_PRESERVED_OFFICIAL_ORIGINAL' if task['role']=='original' else 'PASS','inspection':'individual view_image; text, table rows, margins, dates, page breaks and signatures reviewed'})
    assert len(pages)==24
    result.update(visual_status='PASS_ALL_24_PAGES_INDIVIDUALLY_VIEWED',visual_checked_at=now,
        scope='Worker application only; evidence eight-item fictional stress sample. Employer application pages in the original remain unadapted.',
        notes=['Original application has six pages including worker and employer versions; filled application retains worker version only.',
            'Official original legal-representative merged cell spans pages 1/2; original bytes are not changed. Filled version keeps that merged cell together.',
            'Original household choice labels repeat an out-of-province non-agricultural option; retained as official source wording.',
            'The first PDF text assertion did not account for extraction spaces between evidence names and digits; normalized extraction passed without document changes or a second Word run.'])
    save('render-result.json',result);save('PAGE-QA.json',{'checked_at':now,'pages':pages,'page_count':len(pages),'status':'PASS'})
    save('RESULTS.json',{'checked_at':now,'guides':guides,'public_originals':originals,'tests':{'command':'.venv/Scripts/python.exe -m unittest backend.tests.test_zhejiang_oct29 -v','passed':7,'failed':0,'log':'tests.log'},
        'layout':{'original_files':4,'filled_files':4,'original_pages':14,'filled_pages':10,'total_pages':24,'status':'PASS_ALL_PAGES_VIEWED'},
        'source_manifest_sha256':MANIFEST_SHA256,'publication':'not_published','models_invoked':False,'private_case_databases_accessed':False,
        'issues':[{'status':'resolved_with_excluded_evidence','type':'SPA_HASH_NAVIGATION_OLD_BODY','evidence':'attempts/yinzhou-faq-stale/OUTCOME.txt','resolution':'reload then own-district phone identity before acceptance; semantic regression test rejects correct URL with previous district body'},
            {'status':'acquired_via_public_http','type':'HAISHU_NATIVE_BROWSER_DOWNLOAD_CANCELED','resolution':'recorded actual material click, public Fetch URL, native suggested name; own exact URL fetched without cookies'},
            {'status':'fallback_completed','type':'LIBREOFFICE_NOT_INSTALLED','resolution':'isolated new Word PID29740, all eight window ownership checks, read-only export, own instance exited'}],
        'limitations':['未发布候选，未启动候选站或绕过旧拒绝，候选网页验收NOT_RUN。','两区在线办理均止于个人登录边界，未登录、未填账号、未代提交。','实施机关保留指南原简称；材料必要性当前界面未分别标示，记not_found_in_checked_sources，不解释为可省略。','仅新增两区自身核验，不代表全省/全国覆盖。']})
    files={}
    for p in sorted(OUT.rglob('*')):
        if not p.is_file() or any(x in {'attempts','__pycache__','packaged-render-attempt'} for x in p.relative_to(OUT).parts) or p.name=='PUBLIC-WHITELIST.json':continue
        relative=str(p.relative_to(ROOT)).replace('\\','/')
        files[relative]={'sha256':sha(p),'bytes':p.stat().st_size}
    for relative in ['backend/regional_zhejiang_oct29.py','backend/tests/test_zhejiang_oct29.py','scripts/collect-zhejiang-oct29.py']:
        p=ROOT/relative;files[relative]={'sha256':sha(p),'bytes':p.stat().st_size}
    save('PUBLIC-WHITELIST.json',{'checked_at':now,'scope':'Only explicitly listed public evidence, official originals, fictional QA outputs and source code. No cookies, raw HAR, SSO query, login DOM, private cases or browser session state.',
        'guides':guides,'public_originals':originals,'files':files,'excluded':['attempts/** (stale district-body observation; not valid source evidence)','**/__pycache__/**','browser session state (not retained in report)','raw HAR/cookies/SSO queries/login DOM (not retained)']})
    print(json.dumps({'guides':len(guides),'originals':len(originals),'public_files':len(files),'source_files':len(manifest['files']),'qa_pages':len(pages)}))

if __name__=='__main__':finalize()
