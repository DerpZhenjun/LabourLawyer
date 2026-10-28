"""Own exact Dongcheng candidate and public outbox only, no publication or models."""
import copy,hashlib,json,sqlite3,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from regional_beijing import parse_dongcheng_capture,verify_dongcheng_online_capture
from regional_guides import RegionalStore,resolve_channel,digest,now
BASE=ROOT/'reports/nationwide-localization-20261023-night/cross-province/beijing-dongcheng'
def load(p):return json.loads(p.read_text('utf8'))
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf8')
def main():
    out=BASE/'staging-round28'
    if out.exists():raise ValueError('Preserve own staging iteration')
    p=BASE/'capture-remaining-round28';raws={str(i):load(p/f'section-{i}.json') for i in range(7)}
    raws.update({k:load(p/(v+'.json')) for k,v in {'basic':'basic-expanded','materials':'materials-final','flow':'flow-final'}.items()})
    files=load(BASE/'downloads-round28/original-files.json');directory=load(BASE/'directory-identity.json')
    assert directory['id']=='national:110101' and directory['district']=='东城区' and directory['city']=='北京市'
    qa=load(BASE/'document-qa/identical-original-render.json');assert len(qa['records'])==3 and qa['originals_unchanged']
    for record in qa['records']:
        assert hashlib.sha256((ROOT/record['own_downloaded_file']).read_bytes()).hexdigest()==record['own_original_sha256']
        for page in record['pages']:assert hashlib.sha256((ROOT/page['file']).read_bytes()).hexdigest()==page['sha256']
    save(BASE/'document-qa/visual-review-round28.json',{'at':now(),'own_originals':3,'pages_reviewed':6,'all_pages_opened':True,
        'flow_image_opened':True,'originals_unchanged':True,'authoring':False,'models':0,'adapter_approved':False,
        'findings':['全部为样例，含红色示例姓名请求、2018/2019日期、示例证照和盖章，不能当空白。',
            '证照样例的示例有效期已过去，保留原图不复制；原件可读，未作生成适配。',
            '自己的流程JPEG只绘窗口申请，原文字段仍列窗口和网上办理；登录后提交与到场要求待确认。']})
    g=parse_dongcheng_capture(raws,files)
    entry=verify_dongcheng_online_capture(load(p/'before-online.json'),load(p/'online-after.json'))
    entry['screenshot']=(p/'online-boundary.png').relative_to(ROOT).as_posix()
    g['channel']=resolve_channel({k:v['raw_value'] for k,v in g['fields'].items()},g['sections']['办理流程'],entry)
    g['warnings'].extend([entry['scope_notice'],'本区自己的流程JPEG仅绘窗口路线；正文列窗口及网上办理，实际止于登录，不能因图未画线上就断言不支持网办。'])
    g['directory_identity']={k:directory[k] for k in ['id','code','official_name','source_url']}
    g['evidence']={'own_originals':(BASE/'downloads-round28/original-files.json').relative_to(ROOT).as_posix(),
        'own_flow_image':next(f for f in files if f['official_kind']=='instruction'),'original_review':(BASE/'document-qa/visual-review-round28.json').relative_to(ROOT).as_posix()}
    out.mkdir()
    with sqlite3.connect((ROOT/'backend/data/regional-guides.sqlite').as_uri()+'?mode=ro',uri=True) as src,sqlite3.connect(out/'staging.sqlite') as dst:src.backup(dst)
    candidate=RegionalStore(out/'staging.sqlite').put_guide(g)
    save(out/'guide.json',candidate);save(BASE/'guide.json',candidate);save(out/'online-check.json',entry)
    save(out/'source-checksums.json',{k:{'source_url':v['url'],'collected_at':v['captured_at'],'canonical_json_payload_sha256':digest(v)} for k,v in raws.items()})
    save(out/'candidate.json',{'at':now(),'source_id':candidate['source_id'],'version':candidate['version'],'own_materials':3,
        'own_samples':3,'own_flow_images':1,'original_pages_reviewed':6,'adapters':0,'published':False,'candidate_browser':'NOT_RUN','online_status':'auth_required','models':0})
    store=RegionalStore(ROOT/'backend/data/regional-guides.sqlite');assert store.lookup('beijing','北京市','东城区')['source_id'] is None
    events=[]
    reasons=[
        ('AUTH_REQUIRED','实际点击本区自己的网上办理控件，到官方个人/法人登录选择页，未登录或提交。','online-boundary.png','保留本区入口和来源；登录后网办和到场要求未知，用户自行在官网登录，不代交申请。'),
        ('OFFICIAL_TEMPLATE_NOT_FOUND','本区三份公开附件均标样例下载；自己独立下载并校验原件及六页后确认含示例信息，没有发现本指南自己的独立空白申请书或证据清单。不是全网不存在。','materials.png','官方样例不是空白，不借通州或朝阳要求；同字节只复用渲染证据，不开放未适配生成。'),
        ('MATERIAL_INFORMATION_MISSING','指南委托书材料标必要，但法条说明委托情形；未明确本人自行申请的免交细节，认证等级等字段没有明示。','materials.png','保留必要原文与条件说明，具体免交向东城机构确认，缺项保持未知不造规则。'),
        ('OFFICIAL_SOURCE_CONFLICT','本区流程JPEG绘窗口路线，正文同时列窗口及网上办理，实际网办控件止于官方登录。图的覆盖范围不等于确认仅窗口，具体登录后提交及到场需确认。','flow.png','分别保留自己的流程图、正文和登录边界，不能改写为只窗口或保证全程网办。')]
    for kind,reason,screen,remedy in reasons:
        events.append(store.record_event({'id':digest([candidate['source_url'],kind,'dongcheng-own-round28'])[:32],
            **{k:candidate[k] for k in ['province','city','district','region_code']},'service':candidate['service_name'],
            'url':candidate['source_url'],'type':kind,'occurred_at':now(),'attempts':1,'final_status':'own_candidate_pending_verification',
            'screenshot':(p/screen).relative_to(ROOT).as_posix(),'reason':reason,'remediation':remedy}))
    save(BASE/'outbox/own-source-round28.json',events)
    print(json.dumps({'source_id':candidate['source_id'],'version':candidate['version'],'samples':3,'published':False,'events':[e['id'] for e in events],'models':0}))
if __name__=='__main__':main()
