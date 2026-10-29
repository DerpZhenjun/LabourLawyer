"""Capture actual native browser downloads; never POST/replay from Python."""
import base64
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import zipfile
from xml.etree import ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'.runtime/candidate-browser-20261029/js'
OUT=ROOT/'reports/nationwide-verification-20261029/candidate-jiangsu'
EXE=Path('D:/Apps/agent-browser/node_modules/agent-browser/bin/agent-browser-win32-x64.exe')
SESSION='js-candidate-binary-oct29'
RESULT=[]
FAILURES=[]

def browser(*args):
    # Native daemon launch may inherit pipe handles; files avoid waiting for EOF
    # from a daemon after the CLI itself has exited.
    with tempfile.TemporaryFile() as stdout,tempfile.TemporaryFile() as stderr:
        p=subprocess.run([str(EXE),'--session',SESSION,*args],stdout=stdout,stderr=stderr,timeout=40)
        stdout.seek(0);stderr.seek(0)
        p.stdout=stdout.read().decode('utf-8');p.stderr=stderr.read().decode('utf-8')
    with (RAW/'agent-browser-native-downloads.jsonl').open('a',encoding='utf-8') as f:
        f.write(json.dumps({'at':datetime.now(timezone.utc).isoformat(),'command':list(args),'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr},ensure_ascii=False)+'\n')
    if p.returncode:raise RuntimeError(p.stderr or p.stdout)
    return p.stdout.strip()

def ref(text):
    s=browser('snapshot','-i','-u')
    line=next((l for l in s.splitlines() if text in l),None)
    if line is None:raise AssertionError('Missing native element '+text)
    return '@'+re.search(r'\bref=(e\d+)\b',line).group(1)

def click(text):return browser('click',ref(text))
def fill(text,value):return browser('fill',ref(text),value)
def read(js):
    return json.loads(browser('eval','-b',base64.b64encode(js.encode()).decode()))

def download(code,kind,trigger):
    path=RAW/f'{code}-{kind}-actual-browser.docx'
    native_record=None
    reused=path.is_file() and (RAW/f'{code}-{kind}-chrome-download-record.json').is_file()
    if reused:
        native_record=json.loads((RAW/f'{code}-{kind}-chrome-download-record.json').read_text('utf-8'))
    else:
        trigger()
        result=browser('wait','--download',path.as_posix(),'--timeout','15000')
        assert 'Download saved to' in result
    if not path.is_file():
        # Inspect only this dedicated session's Chrome download records. Never
        # enumerate or guess files in a user's download directory.
        browser('tab','new','chrome://downloads')
        try:
            entries=read("Array.from(document.querySelector('downloads-manager').shadowRoot.querySelectorAll('downloads-item')).map(i=>({fileName:i.data.fileName,filePath:i.data.filePath,state:i.data.state,total:String(i.data.total),url:i.data.url}))")
            district={'320281':'江阴市','320282':'宜兴市'}[code]
            expected_name='劳动人事争议仲裁申请书' if kind=='original' else district+'-'+('仲裁申请书' if kind=='application' else '证据清单')+'-空白表格填写'
            candidates=[e for e in entries if e['state']==2 and (e['url'].startswith('http://127.0.0.1:8001/api/regional-guides/templates/') if kind=='original' else e['url'].startswith('blob:http://127.0.0.1:5174/')) and re.fullmatch(re.escape(expected_name)+r'(?:\s*\(\d+\))?\.docx',e['fileName'])]
            if kind=='original':
                own_annex={'320281':'2213bd5f-676c-4db0-9a4e-d9dd8b851919','320282':'9949cd24-29df-4db9-af04-b4395a22aa61'}[code]
                candidates=[e for e in candidates if '/templates/'+own_annex+'?' in e['url']]
            assert len(candidates)==1,repr(candidates)
            native_record=candidates[0]
            source_path=Path(native_record['filePath']);assert source_path.is_file()
            shutil.copy2(source_path,path)
        finally:browser('tab','close')
    b=path.read_bytes();assert b.startswith(b'PK\x03\x04')
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        document=ET.fromstring(z.read('word/document.xml'))
    ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    paragraphs=[''.join(t.text or '' for t in p.findall('.//w:t',ns)) for p in document.findall('.//w:p',ns)]
    text='\n'.join(paragraphs)
    (RAW/f'{code}-{kind}-actual-browser-paragraphs.json').write_text(json.dumps(paragraphs,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    item={'region_code':code,'kind':kind,'captured_at':datetime.fromtimestamp((RAW/f'{code}-{kind}-chrome-download-record.json').stat().st_mtime,timezone.utc).isoformat() if reused else datetime.now(timezone.utc).isoformat(),'method':'Agent Browser native click then wait --download; recover exact completed record from same session chrome://downloads; no HTTP replay','resumed_existing_own_captured_file':reused,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'zip_crc_passed':True,'actual_browser_file':path.relative_to(ROOT).as_posix()}
    item['chrome_download_record_recovered']=native_record is not None
    if native_record:
        (RAW/f'{code}-{kind}-chrome-download-record.json').write_text(json.dumps(native_record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        item['native_download_state']=native_record['state'];item['native_download_filename']=native_record['fileName'];item['native_download_declared_total']=native_record['total']
    if kind=='original':
        assert item['sha256']=='99dfd60d844fa9a4ea3c37df64d447eda980849427a17e1afbba92e61b092dc3'
        item['matches_own_previously_collected_original_sha256']=True
    elif kind=='application':
        assert '1991-05-09' in text or re.search(r'1991\s*年\s*0?5\s*月\s*0?9\s*日',text),text
        assert re.search(r'副本\s*3\s*份',text),text
        assert re.search(r'相关证据\s*2\s*份',text),text
        assert '锡山区' not in text
        item.update(birthDate='1991-05-09',copyCount=3,evidenceCopyCount=2,actual_docx_values_verified=True)
    elif kind=='evidence':
        assert '劳动合同' in text and '劳动关系' in text
        item['actual_docx_default_evidence_verified']=True
    RESULT.append(item)
    print(json.dumps({'PASS':code+' '+kind,'bytes':len(b),'sha256':item['sha256']}),flush=True)

def confirm(kind):
    title='仲裁申请书' if kind=='application' else '证据清单'
    click('button "生成并下载'+title+'"')
    browser('wait','--text','确认生成'+title+'？')
    click('button "确认生成"')

try:
    browser('open','http://127.0.0.1:5174/province/jiangsu')
    fill('combobox "办理城市"','无锡市')
    for code,district,source,annex in [('320281','江阴市','3d304f186983f34c4170a398','2213bd5f-676c-4db0-9a4e-d9dd8b851919'),('320282','宜兴市','509219666f61612819e02f36','9949cd24-29df-4db9-af04-b4395a22aa61')]:
        fill('combobox "办理区县"',district)
        browser('wait','--text','按'+district+'官方空白表格辅助填写')
        actual=read("document.querySelector('[data-source-id]').dataset.sourceId");assert actual==source
        download(code,'original',lambda:click('/templates/'+annex+'?'))
        click('button "仲裁申请书"')
        fill('textbox "出生日期"','1991-05-09')
        browser('find','text','补充表格中的其他信息','click','--exact')
        fill('spinbutton "随申请书附上的副本份数"','3')
        fill('spinbutton "随申请书附上的证据份数"','2')
        download(code,'application',lambda:confirm('application'))
        click('button "证据清单"')
        browser('wait','--text','添加你的证据')
        assert read("document.querySelectorAll('form .regional-material').length")==1
        download(code,'evidence',lambda:confirm('evidence'))
finally:
    report={'checked_at':datetime.now(timezone.utc).isoformat(),'browser_session':SESSION,'synthetic_only':True,'method':'Attempt native browser UI click/fill/confirmation plus CLI wait --download; require existing PK file before counting success; no HTTP replay','files':RESULT,'failures':FAILURES,'binary_validation_complete':len(RESULT)==6,'render_visual_qa':'not_applicable_without_actual_file' if not RESULT else 'pending','raw_downloads_public':False,'prior_mcp_17_checks_preserved':True}
    (OUT/'ACTUAL-DOWNLOAD-RESULTS.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    browser('close')
