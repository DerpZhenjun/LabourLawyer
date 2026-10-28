"""Independent own-guide candidate and public outbox only; no publication."""
import copy,hashlib,json,sqlite3,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from regional_beijing import parse_tongzhou_capture,verify_tongzhou_online_capture
from regional_guides import RegionalStore,resolve_channel,digest,now
BASE=ROOT/'reports/nationwide-localization-20261023-night/cross-province/beijing-tongzhou'
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf8')
def load(p):return json.loads(p.read_text('utf8'))
def main():
    out=BASE/'staging-0710'
    if out.exists():raise ValueError('Preserve own candidate iteration')
    p=BASE/'sections-0650';captures={str(i):load(p/f'section-{i}.json') for i in range(7)}
    captures.update(basic=load(p/'basic-expanded.json'),materials=load(p/'materials-final.json'),flow=load(p/'flow-final.json'))
    identity=load(BASE/'directory-identity.json')
    assert (identity['provider'],identity['code'],identity['parent_code'],identity['city'],identity['district'])==('national','110112','110100','北京市','通州区')
    reviewed=load(BASE/'document-qa/reference-render.json');assert reviewed['originals_unchanged']
    assert [len(t['pages']) for t in reviewed['tasks']]==[2,2,2]
    for task in reviewed['tasks']:
        for image in task['pages']:assert (ROOT/image).is_file()
    guide=parse_tongzhou_capture(captures,load(BASE/'downloads-0700/original-files.json'))
    guide['evidence']={'capture_file':(p/'materials-final.json').relative_to(ROOT).as_posix(),
        'capture_sha256':hashlib.sha256((p/'materials-final.json').read_bytes()).hexdigest(),
        'screenshot':(p/'flow-reviewed.png').relative_to(ROOT).as_posix(),
        'directory_evidence':(BASE/'directory-identity.json').relative_to(ROOT).as_posix(),
        'section_captures':{name:{'file':(p/f'section-{i}.json').relative_to(ROOT).as_posix(),
            'sha256':hashlib.sha256((p/f'section-{i}.json').read_bytes()).hexdigest()} for i,name in enumerate(guide['sections'])},
        'original_review':(BASE/'document-qa/reference-render.json').relative_to(ROOT).as_posix(),
        'flow_image':load(BASE/'downloads-0700/flow-response-inspection.json')}
    before=load(p/'before-online.json');after=load(p/'online-after.json')
    entry=verify_tongzhou_online_capture(before,after)
    entry.update(before_sha256=hashlib.sha256((p/'before-online.json').read_bytes()).hexdigest(),
        after_sha256=hashlib.sha256((p/'online-after.json').read_bytes()).hexdigest(),
        screenshot=(p/'online-boundary.png').relative_to(ROOT).as_posix())
    final=copy.deepcopy(guide);final['channel']=resolve_channel({k:v['raw_value'] for k,v in guide['fields'].items()},guide['sections']['办理流程'],entry)
    final['warnings'].append(entry['scope_notice'])
    out.mkdir();main=ROOT/'backend/data/regional-guides.sqlite';target=out/'staging.sqlite'
    with sqlite3.connect(main.as_uri()+'?mode=ro',uri=True) as source,sqlite3.connect(target) as dest:source.backup(dest)
    candidate=RegionalStore(target);rawversion=candidate.put_guide(guide);version=candidate.put_guide(final)
    assert [rawversion['version'],version['version']]==[190,191]
    assert len(version['materials'])==3 and len(version['templates'])==3 and not any(t['can_generate'] for t in version['templates'])
    assert version['channel']['online_status']=='auth_required'
    save(out/'raw-guide.json',rawversion);save(out/'guide.json',version);save(out/'online-check.json',entry)
    save(out/'candidate.json',{'at':now(),'source_id':version['source_id'],'versions':[190,191],
        'materials':3,'own_official_samples':3,'own_public_flow_image':1,'reviewed_sample_pages':6,
        'generation':'NOT_ADAPTED_SAMPLE_NOT_BLANK','online_status':'auth_required',
        'post_login_submission_verified':False,'candidate_browser':'NOT_RUN','published':False,'models':0})
    current=RegionalStore(main);assert current.lookup('beijing','北京市','通州区')['source_id'] is None
    events=[]
    for kind,reason,status,remediation,screenshot in [
        ('AUTH_REQUIRED','实际点击本区官方仲裁网办入口到达个人/法人登录选择页，未登录。','manual_authorization','由用户自行选择登录；不核验登录后的私人账户或代交申请。','online-boundary.png'),
        ('OFFICIAL_TEMPLATE_NOT_FOUND','本区三份附件均标注样例下载，逐页看到示例信息；未发现独立空白申请书或证据清单。','documented','保留本区样表来源；未通过适配不开放生成，不套用其他区县。','materials-all.png'),
        ('MATERIAL_INFORMATION_MISSING','官方材料表将授权委托书标为必要；法律依据描述委托情形，未明确未委托时免交规则；认证等级也未单列。','manual_review','保留必要标注和委托情形原文，请向本区机构核对，不擅自省略材料。','materials-expanded.png'),
        ('TEMPLATE_DOWNLOAD_FAILED','样例控件本次原生点击未触发下载，控制台出现脚本异常；随后根据自身公开元数据定位公开原件，三个DOCX均HTTP200且SHA核验。','resolved_public_original_get','保留原生点击和错误记录，不断言唯一根因；下载样表保持样表身份，未访问认证接口。','materials-all.png'),
        ('TEMPLATE_DOWNLOAD_FAILED','流程图官方扩展名及响应类型为JPEG，但内容签名实际为PNG；初次仅接受JPEG的本地校验误报失败。','resolved_actual_png_signature','独立复核原始字节并按实际PNG保存，原URL与原文件名保留；不是政府网站技术故障。','flow-reviewed.png')]:
        event=current.record_event({'id':digest([guide['source_url'],kind,status,guide['collected_at']])[:32],
            **{k:guide[k] for k in ['province','city','district','region_code']},'service':guide['service_name'],
            'keyword':'劳动人事争议仲裁申请','url':guide['source_url'],'occurred_at':guide['collected_at'],
            'type':kind,'screenshot':(p/screenshot).relative_to(ROOT).as_posix(),'reason':reason,
            'attempts':2 if status.startswith('resolved') else 1,'final_status':status,'remediation':remediation})
        events.append(event)
    save(BASE/'outbox/own-source-0710.json',events)
    print(json.dumps({'source_id':version['source_id'],'versions':[190,191],'candidate_only':True,'new_events':len(events),'models':0}))
if __name__=='__main__':main()
