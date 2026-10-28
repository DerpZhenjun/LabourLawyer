"""Own Chaoyang public candidate and outbox only; no primary publication."""
import copy,hashlib,json,sqlite3,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from regional_beijing import parse_chaoyang_capture,verify_chaoyang_online_capture
from regional_guides import RegionalStore,resolve_channel,digest,now
BASE=ROOT/'reports/nationwide-localization-20261023-night/cross-province/beijing-chaoyang'
def load(p):return json.loads(p.read_text('utf8'))
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf8')
def main():
    out=BASE/'staging-round23'
    if out.exists():raise ValueError('Preserve completed own candidate')
    p=BASE/'sections-round23-resumed'
    captures={str(i):load(p/f'section-{i}.json') for i in range(7)}
    captures.update({k:load(p/f'{v}.json') for k,v in {'basic':'basic-expanded','materials':'materials-final','flow':'flow-final'}.items()})
    files=load(BASE/'downloads-round23/original-files.json');identity=load(BASE/'directory-identity.json')
    assert (identity['code'],identity['parent_code'],identity['city'],identity['district'])==('110105','110100','北京市','朝阳区')
    qa=load(BASE/'document-qa/identical-original-render.json');assert len(qa['records'])==3 and qa['originals_unchanged']
    for item in qa['records']:
        assert hashlib.sha256((ROOT/item['own_downloaded_file']).read_bytes()).hexdigest()==item['own_original_sha256']
        for page in item['pages']:assert hashlib.sha256((ROOT/page['file']).read_bytes()).hexdigest()==page['sha256']
    raw=parse_chaoyang_capture(captures,files)
    raw['warnings'].append('本指南附件流程图只绘出窗口申请路线，正文仍列网上办理且有登录入口；图中未画线上分支不等于确认不支持网办，具体提交及到场要求请向朝阳区机构确认。')
    raw['evidence']={'capture_file':(p/'materials-final.json').relative_to(ROOT).as_posix(),
        'capture_sha256':hashlib.sha256((p/'materials-final.json').read_bytes()).hexdigest(),
        'screenshot':(p/'own-heading.png').relative_to(ROOT).as_posix(),
        'own_directory':(BASE/'directory-identity.json').relative_to(ROOT).as_posix(),
        'own_originals':(BASE/'downloads-round23/original-files.json').relative_to(ROOT).as_posix(),
        'original_review':(BASE/'document-qa/identical-original-render.json').relative_to(ROOT).as_posix(),
        'own_flow_image':next(f for f in files if f['official_kind']=='instruction')}
    entry=verify_chaoyang_online_capture(load(p/'before-online.json'),load(p/'online-after.json'))
    entry.update(screenshot=(p/'online-boundary.png').relative_to(ROOT).as_posix(),
        before_sha256=hashlib.sha256((p/'before-online.json').read_bytes()).hexdigest(),
        after_sha256=hashlib.sha256((p/'online-after.json').read_bytes()).hexdigest())
    final=copy.deepcopy(raw);final['channel']=resolve_channel({k:v['raw_value'] for k,v in raw['fields'].items()},raw['sections']['办理流程'],entry)
    final['warnings'].append(entry['scope_notice'])
    out.mkdir();main=ROOT/'backend/data/regional-guides.sqlite';target=out/'staging.sqlite'
    with sqlite3.connect(main.as_uri()+'?mode=ro',uri=True) as source,sqlite3.connect(target) as dest:source.backup(dest)
    candidate=RegionalStore(target);versions=[candidate.put_guide(g) for g in [raw,final]]
    assert [g['version'] for g in versions]==[190,191];g=versions[-1]
    assert g['channel']['online_status']=='auth_required' and not any(t['can_generate'] for t in g['templates'])
    save(out/'raw-guide.json',versions[0]);save(out/'guide.json',g);save(BASE/'guide.json',g);save(out/'online-check.json',entry)
    save(out/'candidate.json',{'at':now(),'source_id':g['source_id'],'versions':[190,191],
        'own_materials':3,'own_samples':3,'own_flow_image':1,'own_original_bytes_reused_render_pages':6,
        'online_status':'auth_required','generation':'NOT_ADAPTED_SAMPLE_NOT_BLANK','published':False,
        'candidate_browser':'NOT_RUN','models':0})
    store=RegionalStore(main);assert store.lookup('beijing','北京市','朝阳区')['source_id'] is None
    events=[]
    for kind,reason,status,remediation in [
        ('AUTH_REQUIRED','原生点击本区自己的仲裁申请网办入口到达官方个人/法人登录选择页，未登录。','manual_authorization','保留实际入口和源ID，登录后提交能力与到场要求未知，不代交申请。'),
        ('OFFICIAL_TEMPLATE_NOT_FOUND','自己的指南三附件都标样例下载，独立下载原件逐字节验证并复核六页，未发现本事项独立空白申请书或证据表。','documented','同字节官方原件可复用渲染证据，不继承其他区指南或开放未经适配的生成。'),
        ('MATERIAL_INFORMATION_MISSING','官方委托书材料标必要，法律依据适用委托情形；未明确不委托时的免交规则，认证等级未单列。','manual_review','保留原文，具体条件向朝阳区机构确认。'),
        ('TEMPLATE_DOWNLOAD_FAILED','自己的三个样例按钮实际点击未触发下载且控制台有脚本异常；经自身公开元数据下载三个原DOCX均200及SHA核验。','resolved_public_original_get','保留点击证据与异常，不断言唯一根因或全站故障；只使用公开下载，不访问认证接口。'),
        ('OFFICIAL_SOURCE_CONFLICT','自己的流程图只绘窗口申请，文字字段列窗口及网上办理；实际入口可到官方登录选择。图未画线上分支本身不能证明不支持网上办理。','manual_clarification','分别保留自己的图、字段及入口证据；不将图文覆盖范围差异改写成窗口仅办，登录后是否需到场待机构确认。')]:
        e=store.record_event({'id':digest([raw['source_url'],kind,status,raw['collected_at']])[:32],
            **{k:raw[k] for k in ['province','city','district','region_code']},'service':raw['service_name'],
            'keyword':'劳动人事争议仲裁申请','url':raw['source_url'],'occurred_at':raw['collected_at'],
            'type':kind,'screenshot':(p/('online-boundary.png' if kind=='AUTH_REQUIRED' else 'flow.png' if kind=='OFFICIAL_SOURCE_CONFLICT' else 'materials.png')).relative_to(ROOT).as_posix(),
            'reason':reason,'final_status':status,'attempts':2 if status.startswith('resolved') else 1,'remediation':remediation})
        events.append(e)
    save(BASE/'outbox/own-source-round23.json',events)
    print(json.dumps({'source_id':g['source_id'],'candidate_only':True,'new_public_events':len(events),'models':0}))
if __name__=='__main__':main()
