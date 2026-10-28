"""Explicit, public-only OpenClaw issue review. No fabricated delivery ACK."""
import argparse,json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from regional_guides import RegionalStore,now
from template_acquisition.openclaw_bridge import describe_image

def run(timeout):
    report=ROOT/'reports/government-guide-localization';report.mkdir(exist_ok=True)
    store=RegionalStore(os.getenv('LABOURLAWYER_REGIONAL_DB',ROOT/'backend/data/regional-guides.sqlite'))
    pending=[e for e in store.events() if e['delivery_status']=='PENDING_OPENCLAW']
    # Only the whitelisted public collection events; never user documents/accounts.
    bundle=[{k:v for k,v in e.items() if k not in {'receipt','delivery_status'}} for e in pending]
    (report/'outbox/pending-public-events.json').write_text(json.dumps(bundle,ensure_ascii=False,indent=2),encoding='utf8')
    prompt='请记录以下公开政府指南采集问题，勿提交仲裁申请。输出JSON：ok、accepted_event_ids（仅实际读到的完整编号）、report（含搜索关键词、网办、模板缺失、访问失败、登录、地区差异摘要）。样表不是空白模板；来源冲突不能断言不支持网办。事件：'+json.dumps(bundle,ensure_ascii=False,separators=(',',':'))
    status={'attempted_at':now(),'engine':'OpenClaw','pending_count':len(pending),'status':'PENDING_OPENCLAW','receipt_file':'openclaw/issue-review-receipt.json'}
    try:
        output=report/'openclaw/issue-review-receipt.json'
        describe_image(report/'04-tianfu-guide.png',output,report/'openclaw/isolated',timeout_seconds=timeout,prompt=prompt,role='public_regional_collection_issue_review')
        receipt=json.loads(output.read_text(encoding='utf8'))
        texts=[x['text'] for x in receipt['result']['outputs'] if x.get('text')]
        answer=json.loads(texts[0].removeprefix('```json').removesuffix('```').strip())
        store.acknowledge([e['id'] for e in pending],answer)
        status.update(status='ACKNOWLEDGED_OPENCLAW',pending_count=0,report=answer.get('report'))
    except Exception as exc:status['reason']=str(exc)
    (report/'OPENCLAW-STATUS.json').write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding='utf8')
    (report/'COLLECTION-ISSUES.json').write_text(json.dumps(store.events(),ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(status,ensure_ascii=True))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--timeout',type=int,default=45)
    run(p.parse_args().timeout)
