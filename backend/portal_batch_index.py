"""Keep the most recent complete national deliverable distinct from trial runs."""
import json
from pathlib import Path

def batch_records(root):
    records=[]
    for path in root.glob('*/status.json'):
        try:
            state=json.loads(path.read_text(encoding='utf8'))
            result=path.parent/'results.json'
            items=json.loads(result.read_text(encoding='utf8')) if result.is_file() else []
            regions=len({x['slug'] for x in items});searches=sum(len(x.get('searches',[])) for x in items)
            requested=state.get('total',regions)
            report=path.parent/'劳动仲裁政务服务门户观察报告.docx'
            full=requested==31 and regions==31 and searches==93
            ready=state.get('state')=='complete' and report.is_file()
            record=dict(state,regions_saved=regions,searches_saved=searches,nationwide=full,report_ready=ready,
                scope_label='全国31地区' if requested==31 else f'{requested}个地区的专项批次',
                batch_label='完整全国报告' if full and ready else '专项报告' if ready else '采集中或未完成的证据')
            records.append(record)
        except (OSError,ValueError,KeyError):continue
    return sorted(records,key=lambda r:r.get('updated_at') or r.get('started_at',''),reverse=True)

def publish_index(root):
    from portal_audit import write_json
    records=batch_records(root)
    complete=[r for r in records if r['report_ready'] and r['nationwide']]
    recommended=max(complete,key=lambda r:(r.get('report_revision',1),r.get('updated_at',''))) if complete else None
    for r in records:r['recommended']=bool(recommended and r['id']==recommended['id'])
    write_json(root/'index.json',dict(recommended_id=recommended['id'] if recommended else None,items=records))
    if recommended:
        folder=root/recommended['id']
        write_json(root/'latest.json',dict(id=recommended['id'],report=str(folder/'劳动仲裁政务服务门户观察报告.docx'),
            ai_report=recommended.get('ai_report'),ai_completed=recommended.get('ai_completed',0),total=31,scope='nationwide',updated_at=recommended.get('updated_at')))
    lines=['# 门户报告批次说明','','文件夹名是批次开始时间；修改时间只说明其中有文件被更新。时间靠后不代表全国采集更完整。',
        '',f"当前完整全国报告：`{recommended['id']}`" if recommended else '当前还没有完整全国报告。',
        '','`latest.json` 指向最新完整全国报告；`index.json` 保存所有批次的范围、进度和状态。专项试跑、中断和失败批次保留证据，不覆盖完整全国报告入口。',
        '','| 批次 | 范围 | 状态 | 已保存地区 | 三词检索 | AI完整地区 | 推荐 |','|---|---|---|---:|---:|---:|---|']
    for r in records:
        state={'complete':'已生成','running':'运行中','failed':'失败','interrupted':'中断'}.get(r.get('state'),r.get('state','未知'))
        lines.append(f"| `{r['id']}` | {r['scope_label']} | {state} | {r['regions_saved']} | {r['searches_saved']} | {r.get('ai_completed',0)} | {'当前完整全国报告' if r['recommended'] else ''} |")
    (root/'README.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
    return dict(recommended_id=recommended['id'] if recommended else None,items=records)
