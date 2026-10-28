"""Isolated public-guide candidate and public auth-boundary outbox only."""
import hashlib,json,sqlite3,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from regional_guides import RegionalStore,digest,now
BASE=ROOT/'reports/nationwide-localization-20261023-night/cross-province/jiangsu-haizhou'


def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf8')


def main():
    stage=BASE/'staging-0540';db=stage/'staging.sqlite'
    if db.exists():raise ValueError('Preserve independent candidate database')
    g=json.loads((BASE/'guide.json').read_text('utf8'))
    render=json.loads((BASE/'document-qa/original-render.json').read_text('utf8'))
    if (len(render['tasks'])!=6 or sum(len(t['pages']) for t in render['tasks'])!=12
        or not (BASE/'document-qa/visual-review.md').is_file()):raise ValueError('Own original review missing')
    for t in g['templates']:
        assert t['download_status']=='downloaded' and hashlib.sha256((ROOT/t['file']).read_bytes()).hexdigest()==t['sha256']
        if t['id'] in {'4a075913-1fc9-4483-8398-299ff491d115','dcf32a17-5c59-49fd-8eb5-b6c7bb493994','700f57ca-e9bc-4e31-b7e6-fbcc28108d7f'}:
            t['content_kind']='material_placeholder';t['classification_note']='原件仅标题，是材料提示，不是可代替本人证据或身份证明的文书模板。'
        t['can_generate']=False;t['document_types']=[]
    g['warnings'].extend(['官网证据复印件的空白与样例链接返回同一标题页，不是本人证据。',
        '实际点击网办进入登录和验证码，但认证回跳使用旧HTTP地址，尚待严格回跳核验；不保证登录后可提交。',
        '申请书原件同时包含劳动者和用人单位两种表，尚未开放本区填写生成。'])
    g['evidence']['original_review']=(BASE/'document-qa/visual-review.md').relative_to(ROOT).as_posix()
    save(stage/'reviewed-guide.json',g)
    main_db=ROOT/'backend/data/regional-guides.sqlite';stage.mkdir(exist_ok=True)
    with sqlite3.connect(main_db.as_uri()+'?mode=ro',uri=True) as source,sqlite3.connect(db) as dest:source.backup(dest)
    candidate=RegionalStore(db).put_guide(g);store=RegionalStore(main_db)
    assert store.lookup('jiangsu','连云港市','海州区')['source_id'] is None
    save(stage/'candidate.json',{'at':now(),'source_id':candidate['source_id'],'version':candidate['version'],
        'materials':4,'originals':8,'original_pages_inspected':12,'sample_images_inspected':1,'adapters':0,
        'online_status':'unverified','actual_auth_boundary':True,'callback_review':'legacy HTTP own callback pending strict validation',
        'published':False,'candidate_browser':'NOT_RUN','no_staging_launch_attempt':True,'models':0})
    boundary=json.loads((BASE/'online-boundary-0530/after.json').read_text('utf8'))
    if '统一身份认证系统' not in boundary['text'] or 'password' not in boundary['html']:raise ValueError('Actual login evidence missing')
    screenshot=(BASE/'online-boundary-0530/authentication-boundary.png').relative_to(ROOT).as_posix()
    events=[]
    for typ,reason in [('AUTH_REQUIRED','自己的在线办理按钮实际进入江苏统一身份认证表单，未登录，不判断登录后具体服务可用性。'),
        ('CAPTCHA_REQUIRED','真实身份认证页面出现验证码输入和图片，停止于边界，未识别/解答/绕过。'),
        ('ONLINE_CHANNEL_UNVERIFIED','官方原文窗口办理、网上办理；实际认证回跳仍为自身旧HTTP地址，需要单独核验，不放宽其他区县验证规则。'),
        ('MATERIAL_INFORMATION_MISSING','自己证据复印件空白与样例附件均只有标题且SHA相同，身份证DOCX也仅标题；已保留原件，不把材料提示当可填模板。')]:
        events.append(store.record_event({'id':digest([g['source_url'],typ,boundary['captured_at']])[:32],
            **{k:g[k] for k in ['province','city','district','region_code']},'service':g['service_name'],
            'type':typ,'url':g['source_url'],'keyword':'劳动人事争议仲裁申请','occurred_at':boundary['captured_at'],
            'reason':reason,'attempts':1,'final_status':'manual_review',
            'screenshot':screenshot if typ!='MATERIAL_INFORMATION_MISSING' else g['evidence']['screenshot'],
            'remediation':'保留本区原始来源、原件和边界截图，继续独立适配/回跳核验，不登录、不提交、不继承邻区。'}))
    save(BASE/'outbox/own-source-0540.json',events)
    print(json.dumps({'candidate':candidate['source_id'],'version':candidate['version'],'published':False,'public_events':len(events),'delivery':'PENDING_OPENCLAW','receipt':None}))


if __name__=='__main__':main()
