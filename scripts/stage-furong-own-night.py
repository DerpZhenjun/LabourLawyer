"""Own-guide candidate and public issues only; never publish or call a model."""
import hashlib,json,sqlite3,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from regional_furong import parse_furong_capture,SOURCE
from regional_guides import RegionalStore,digest,now
BASE=ROOT/'reports/nationwide-localization-20261023-night/cross-province/hunan-furong'
PATHS={'list':'list-round26/dom.json','basic':'control-flow-recovery-round26/stable-header.json','online':'online-recovery-round26/boundary.json'}
PATHS.update({n:'sections-round26/'+n+'.json' for n in ['权利与义务','结果样本','常见问题','法律依据']})
def save(path,value):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf8')
def main():
    out=BASE/'staging-round26'
    if out.exists():raise ValueError('Preserve previous independent staging')
    pages={k:json.loads((BASE/p).read_text('utf8')) for k,p in PATHS.items()}
    downloads=json.loads((BASE/'downloads-round26/original-files.json').read_text('utf8'))
    guide=parse_furong_capture(pages,downloads)
    directory=json.loads((BASE/'directory-identity.json').read_text('utf8'))
    assert directory['id']=='national:430102' and directory['district']=='芙蓉区' and directory['city']=='长沙市'
    guide['directory_identity']={k:directory[k] for k in ['id','official_name','source_url','code']}
    qa=json.loads((BASE/'document-qa/original-render.json').read_text('utf8'))
    assert len(qa['tasks'])==4 and sum(len(t['pages']) for t in qa['tasks'])==14
    assert qa['originals_unchanged'] and not qa['authoring']
    save(BASE/'document-qa/visual-review-round26.json',{'reviewed_at':now(),'pages_reviewed':14,'all_pages_opened':True,
        'originals':[{ 'id':t['own_annex_id'],'sha256':t['own_sha256'],'pages':t['pages'],'role':'blank' if t['control_role']=='blank_control_unclassified' else 'sample'} for t in qa['tasks']],
        'originals_preserved':True,'authoring':False,'generated_documents':0,'adapter_approved':False,
        'findings':['两份空白表4页，各有末页空表跨页留白；保留原件，未通过填写适配版式门禁。',
            '两份示例各3页；劳动者示例日期1997.10.32不合法，不复制为默认事实。',
            '全部14页文字可读，未改动官方原件；样例不是空白表。','官方流程PNG已单独打开完整查看；不是申请模板。']})
    out.mkdir()
    with sqlite3.connect((ROOT/'backend/data/regional-guides.sqlite').as_uri()+'?mode=ro',uri=True) as src,sqlite3.connect(out/'staging.sqlite') as dst:src.backup(dst)
    candidate=RegionalStore(out/'staging.sqlite').put_guide(guide)
    public=RegionalStore(ROOT/'backend/data/regional-guides.sqlite')
    assert public.lookup('hunan','长沙市','芙蓉区')['source_id'] is None
    save(out/'guide.json',guide);save(BASE/'guide.json',guide)
    save(out/'source-checksums.json',{k:{'file':(BASE/p).relative_to(ROOT).as_posix(),'sha256':hashlib.sha256((BASE/p).read_bytes()).hexdigest(),'captured_at':pages[k]['captured_at']} for k,p in PATHS.items()})
    save(out/'candidate.json',{'at':now(),'source_id':candidate['source_id'],'version':candidate['version'],
        'own_material_groups':4,'official_application_originals':4,'blank_originals':2,'sample_originals':2,'flow_images':1,
        'original_pages_reviewed':14,'adapters':0,'published':False,'candidate_browser':'NOT_RUN','online_status':'auth_required','models':0})
    issues=[
      ('OFFICIAL_SOURCE_CONFLICT','官网抬头60工作日，时限说明45日加最多15日，环节表3和41工作日；基本信息0次且无需到现场，FAQ答需要现场；份数表2份、填报当事人数+1、空白表副本按被申请人数。原样保留不同口径，不承诺到场或统一份数。','control-flow-recovery-round26/stable-header.png','向本区窗口确认时限、到场和份数；不覆盖或拼成统一要求，保留原文与核验时间。'),
      ('AUTH_REQUIRED','实际本区自身指南点击在线办理，等待个人登录文字后到湖南政务服务网个人/法人认证页。未登录，未填身份或申请数据，未提交。','online-recovery-round26/boundary.png','停在认证边界，记录auth_required，不宣称登录后全程网办或免到场已核验。'),
      ('OFFICIAL_TEMPLATE_NOT_FOUND','本次自身正式指南四项材料中，申请书提供两份空白DOC和两份示例DOC并已公开下载核验；没有发现独立证据清单空白模板。结果样本是裁决等结果文书，不是申请模板；不表示全网不存在。','sections-round26/material-standard-2.png','保留已有本区申请书原件和14页QA；独立证据清单继续查本区来源，不借其他省区模板。本区填写适配及浏览器发布验收尚未完成。')]
    events=[]
    for kind,reason,screenshot,remedy in issues:
        assert (BASE/screenshot).is_file()
        events.append(public.record_event({'id':digest([SOURCE,kind,'furong-own-round26'])[:32],
            'province':'hunan','city':'长沙市','district':'芙蓉区','region_code':'430102','service':'劳动人事争议仲裁申请',
            'type':kind,'url':SOURCE,'occurred_at':now(),'reason':reason,'attempts':1,'final_status':'own_formal_candidate_pending_verification',
            'screenshot':(BASE/screenshot).relative_to(ROOT).as_posix(),'remediation':remedy}))
    save(BASE/'outbox/own-source-round26.json',events)
    save(BASE/'collection-recoveries-round26.json',{'at':now(),'items':[
        {'problem':'flow generic text selector did not locate a native target','recovery':'doctor7PASS; inspect actual saved DOM, native scoped CSS click succeeds','evidence':'control-flow-recovery-round26/flow-expanded.png'},
        {'problem':'native aggregate download wait timed out despite public original GET200','recovery':'low-rate copy the five actual observed public original URLs; HTTP200, magic and SHA verified','evidence':'downloads-round26/original-files.json'},
        {'problem':'first online DOM captured before navigation; stdout GBK encoding failed','recovery':'preserve first evidence, exact own guide reopened, native click and wait personal login then capture; no identity input','evidence':'online-recovery-round26/manifest.json'},
        {'problem':'recheck-only time created new version','recovery':'entry-check metadata uses existing verified_at volatile field; substantive-copy change still creates history; unit tests passed','evidence':'backend/tests/test_furong_capture.py'}],
        'not_government_fault_claims':True,'models':0})
    print(json.dumps({'source':candidate['source_id'],'version':candidate['version'],'materials':4,'originals':4,'published':False,
        'events':[e['id'] for e in events],'delivery':'PENDING_OPENCLAW','models':0}))
if __name__=='__main__':main()
