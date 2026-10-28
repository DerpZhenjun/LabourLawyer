"""Keep raw/adapted/channel versions in an independent public candidate, never publish."""
import copy,hashlib,json,sqlite3,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from regional_adapters import with_reference_capabilities
from regional_jiangsu import verify_haizhou_online_capture
from regional_guides import RegionalStore,resolve_channel,digest,now
BASE=ROOT/'reports/nationwide-localization-20261023-night/cross-province/jiangsu-haizhou'


def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf8')


def main():
    out=BASE/'staging-adapted-0615';target=out/'staging.sqlite'
    if out.exists():raise ValueError('Preserve own candidate iteration')
    approval=json.loads((BASE/'document-qa/document-approval.json').read_text('utf8'))
    manifest=json.loads((BASE/'document-qa/generated-0555/render-manifest.json').read_text('utf8'))
    if approval['status']!='approved_for_own_offline_filling_only' or approval['output_pages']!=[2,1]:raise ValueError('Own visual gate missing')
    for item in manifest['checks']:
        assert hashlib.sha256((ROOT/item['output']).read_bytes()).hexdigest()==item['sha256']
        assert hashlib.sha256((ROOT/item['original']).read_bytes()).hexdigest()==item['original_sha256']
    before=json.loads((BASE/'online-boundary-0530/before.json').read_text('utf8'))
    after=json.loads((BASE/'online-boundary-0530/after.json').read_text('utf8'))
    callback=json.loads((BASE/'callback-source-0605/callback-page.json').read_text('utf8'))
    redirect=json.loads((BASE/'callback-source-0605/capture-only.json').read_text('utf8'))
    entry=verify_haizhou_online_capture(before,after,callback,redirect)
    entry.update(screenshot=(BASE/'online-boundary-0530/authentication-boundary.png').relative_to(ROOT).as_posix(),
        before_sha256=hashlib.sha256((BASE/'online-boundary-0530/before.json').read_bytes()).hexdigest(),
        after_sha256=hashlib.sha256((BASE/'online-boundary-0530/after.json').read_bytes()).hexdigest(),
        callback_sha256=hashlib.sha256((BASE/'callback-source-0605/callback-page.json').read_bytes()).hexdigest())
    raw=json.loads((BASE/'staging-0540/reviewed-guide.json').read_text('utf8'))
    adapted=with_reference_capabilities(raw)
    adapted['warnings']=[w for w in adapted['warnings'] if '尚未开放本区填写生成' not in w]
    adapted['warnings'].append('本区自己的官方空白申请书和证据清单已完成离线填写适配，仍须本人核对并手写签名。')
    final=copy.deepcopy(adapted)
    final['channel']=resolve_channel({k:v['raw_value'] for k,v in raw['fields'].items()},raw['sections']['办理流程'],entry)
    final['warnings']=[w for w in final['warnings'] if not w.startswith('实际点击网办进入登录和验证码')]
    final['warnings'].append(entry['callback_notice'])
    out.mkdir();main=ROOT/'backend/data/regional-guides.sqlite'
    with sqlite3.connect(main.as_uri()+'?mode=ro',uri=True) as source,sqlite3.connect(target) as dest:source.backup(dest)
    store=RegionalStore(target)
    versions=[store.put_guide(g) for g in [raw,adapted,final]]
    assert [v['version'] for v in versions]==[190,191,192]
    assert len([t for t in versions[-1]['templates'] if t.get('can_generate')])==2
    assert final['channel']['online_status']=='auth_required'
    current=RegionalStore(main)
    assert current.lookup('jiangsu','连云港市','海州区')['source_id'] is None
    save(out/'guide.json',versions[-1]);save(out/'online-check.json',entry)
    save(out/'candidate.json',{'at':now(),'source_id':'f2208816780787a1a046b91f','versions':[190,191,192],
        'materials':4,'own_originals':8,'own_offline_filling_kinds':['application','evidence'],
        'online_status':'auth_required','legacy_callback':'actual native visit reached exact own HTTPS guide',
        'candidate_browser':'NOT_RUN','published':False,'models':0})
    old=json.loads((BASE/'outbox/own-source-0540.json').read_text('utf8'))
    prior=next(e for e in old if e['type']=='ONLINE_CHANNEL_UNVERIFIED')
    event=current.record_event({'id':digest([raw['source_url'],'own-legacy-return-resolved',callback['captured_at']])[:32],
        **{k:raw[k] for k in ['province','city','district','region_code']},'service':raw['service_name'],
        'type':'ONLINE_CHANNEL_UNVERIFIED','url':raw['source_url'],'keyword':'劳动人事争议仲裁申请',
        'occurred_at':callback['captured_at'],'attempts':2,'final_status':'resolved_by_own_callback_https_capture',
        'screenshot':(BASE/'callback-source-0605/callback-page.png').relative_to(ROOT).as_posix(),
        'reason':'原事件'+prior['id']+'的旧HTTP回跳已独立实际访问，浏览器最终到达本区HTTPS同事项，机关/地区/业务编码核验一致。现确认登录与验证码边界，仍不保证登录后能提交。',
        'remediation':'保留原事件和新增解决记录，仅海州精确映射通过；未放宽其他区县、未登录、未解验证码、未代交申请。'})
    save(BASE/'outbox/resolved-callback-0615.json',[event])
    print(json.dumps({'source_id':versions[-1]['source_id'],'versions':[190,191,192],'offline_kinds':2,
        'published':False,'channel':'auth_required','resolution_event':event['id'],'delivery':'PENDING_OPENCLAW'}))


if __name__=='__main__':main()
