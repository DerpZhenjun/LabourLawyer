"""Read public state and retain an honest resumable nationwide checkpoint."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from regional_rollout import _snapshot,build_rollout_status,build_rollout_targets,load_rollout_candidates
from regional_guides import RegionalStore,now
OUT=ROOT/'reports/nationwide-localization-20261028'
def read(p):return json.loads(p.read_text('utf8'))
def save(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8')
def main():
    candidates=load_rollout_candidates(ROOT)
    for row in candidates:
        code=row.get('region_code')
        qa=('jiangsu/document-qa' if code in ['320903','320902'] else 'form-qa-next' if code in ['320981','320924'] else 'form-qa-zhejiang-accepted' if code in ['330110','330106'] else None)
        if qa:
            checks=[x for x in read(OUT/qa/'package-checks.json') if x['region_code']==code]
            assert len(checks)==2
            row.update(document_visual_qa_status='PASS_OFFLINE_ONLY',document_qa='reports/nationwide-localization-20261028/'+qa,
                       web_qa_status='NOT_RUN_POLICY_REFUSAL',published=False,can_generate=False)
    save(OUT/'CANDIDATES.json',candidates)
    directory,guides,jobs=_snapshot(ROOT)
    status=build_rollout_status(directory,guides,candidates,read(ROOT/'frontend/src/data/provinceCatalog.json'))
    targets=build_rollout_targets(directory,guides,candidates)
    save(OUT/'NATIONAL-STATUS.json',status)
    published=[{k:g.get(k) for k in ['province','province_name','city','district','region_code','source_id','source_url','verified_at','channel']} | {
        'can_generate':any(t.get('can_generate') for t in g.get('templates',[]))} for g in guides]
    save(OUT/'PUBLISHED-LOCALITIES.json',published)
    unfinished=[{k:t[k] for k in ['province','city','district','state']} for t in targets if t['state']!='generatable']
    save(OUT/'UNFINISHED-REGIONS.json',unfinished)
    files=[];failures=[]
    for scope,items in [('published',guides),('staged',RegionalStore(OUT/'acceptance/regional-guides.sqlite').inventory())]:
        for g in items:
            for t in g.get('templates',[]):
                if t.get('download_status')!='downloaded':continue
                p=(ROOT/t['file']).resolve();valid=p.is_relative_to((ROOT/'templates/_docx/_regional').resolve()) and p.is_file()
                actual=hashlib.sha256(p.read_bytes()).hexdigest() if valid else None
                record={'scope':scope,'source_id':g['source_id'],'file':t['file'],'expected_sha256':t['sha256'],'actual_sha256':actual,'pass':actual==t['sha256']}
                files.append(record)
                if not record['pass']:failures.append(record)
    save(OUT/'FILE-INTEGRITY.json',{'checked_at':now(),'checks':len(files),'failures':failures,'items':files})
    assert not failures
    checkpoint={'updated_at':now(),'objective':'全国区县和功能区各自官方指南与文书填写生成','completion_status':'INCOMPLETE',
        'directory_is_not_guide_coverage':True,'public_status':status,
        'directory_physical_rows':len(directory),'unfinished_known_places':len(unfinished),
        'new_own_sources_this_turn':8,'new_own_originals_this_turn':46,'new_own_offline_form_localities':6,
        'published_new_localities_this_turn':0,'candidate_site':{'state':'EXECUTION_POLICY_REJECTED_AFTER_USER_APPROVAL','ports':[8001,5174],
            'reason':'blocked by policy','retried_via_alternate_mechanism':False,'web_acceptance':'NOT_RUN','candidate_database':'acceptance/regional-guides.sqlite'},
        'tests':{'full_backend':{'passed':431,'seconds':97.136,'log':'.runtime/nationwide-20261028/backend-final.log'},
            'after_layout_zhejiang':{'passed':23,'seconds':22.282,'log':'.runtime/nationwide-20261028/zhejiang-canonical-final.log'},
            'frontend_build':{'passed':True,'seconds':2.73,'log':'.runtime/nationwide-20261028/frontend-final-build.log'},
            'real_browser':read(OUT/'rollout/browser-evidence-final/result.json')},
        'openclaw':{'status':'PENDING_OPENCLAW','public_events':306,'acknowledged':0,'new_events':8,'model_calls':0},
        'automation':{'old_overnight':'PAUSED_EXPIRED_UNCHANGED','new_nationwide_automation':'NOT_CREATED','background_collectors':'NONE'},
        'main_website':'http://127.0.0.1:5173','main_api':'http://127.0.0.1:8000','case_data':'.runtime/nationwide-20261028/test-platform',
        'safety':{'windows_ollama_started':False,'models_called':False,'git_commit_push':False,'private_databases_accessed':False},
        'next_actions':['独立候选站执行策略解除前不再换方式重试或发布候选；用户授权已取得但执行层仍拒绝。',
            '19候选逐一真实网页验收；离线已有6新地及旧3地适配不重复采集。',
            '蜀山原DOC与包河空白尚无批准生成适配，先检查原件及版式，不套用省级。',
            '其余3390已知未采集地点按UNFINISHED-REGIONS和持久队列做各自官方浏览。国家API1003不能视为当地无服务。',
            '先检查进程和OS锁；新worker持锁后只恢复service_discovery，严格跳过已有精确来源，其他kind不变。',
            '后续新批次单独留证据/时间/SHA，更新本checkpoint；不自动恢复旧夜间任务或启动模型。']}
    save(OUT/'RESUME-CHECKPOINT.json',checkpoint)
    table=['| 省份 | 已知追踪地点 | 已发布指南 | 可填写生成 | 候选未发布 | 未采集 |','|---|---:|---:|---:|---:|---:|']
    for p in status['provinces']:table.append(f"| {p['name']} | {p['targets_total']} | {p['published_guides']} | {p['generatable_localities']} | {p['candidates']} | {p['uncollected']} |")
    (OUT/'PROVINCE-MATRIX.md').write_text('# 各省实际状态\n\n所有省份均未完成；追踪地点不是完整功能区普查，不包括省级历史模板覆盖推断。\n\n'+'\n'.join(table)+'\n',encoding='utf8')
    print(json.dumps({'guides':len(guides),'can_generate':status['generatable_localities'],'candidates':status['unpublished_candidates'],
        'unfinished_known_places':len(unfinished),'file_checks':len(files),'sha_failures':len(failures),'checkpoint':str(OUT/'RESUME-CHECKPOINT.json')},ensure_ascii=False))
if __name__=='__main__':main()
