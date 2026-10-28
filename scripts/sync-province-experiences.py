"""Publish the same sourced provincial guide cards to web/Android and WeChat."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from province_experience import load_experiences,plain_guide,choose_guide,guide_rank,POLICY,PORTALS
from province_documents import PROVINCE_DOCUMENTS
data=load_experiences()
if data is None:
    base=ROOT/'templates/_reports/portal-audits';source=base/json.loads((base/'latest.json').read_text(encoding='utf8'))['id']
    profiles={}
    for slug,meta in PROVINCE_DOCUMENTS.items():
        path=source/slug/'workflows.json'
        guides=json.loads(path.read_text(encoding='utf8')).get('guides',[]) if path.exists() else []
        guide=choose_guide(guides,slug)
        p=plain_guide(guide or {},slug,meta.get('scope',''))
        p.update(slug=slug,name=meta['name'],state='historical' if guide else 'not_detected',portal_url=PORTALS[slug],source_run=source.name,templates=(guide or {}).get('templates',[]),capital_confirmed=bool(guide and not guide_rank(guide,slug)[1]))
        profiles[slug]=p
    data={'version':1,'run_id':source.name,'provinces':profiles}
themes=json.loads((ROOT/'config/province_themes.json').read_text(encoding='utf8'))
for slug,p in data['provinces'].items():
    if p.get('selected_guide'):p.update(plain_guide(p['selected_guide'],slug,PROVINCE_DOCUMENTS[slug].get('scope','')))
    p['theme']=themes[slug]
    if not p.get('steps'):
        p['steps']=[{'title':'先打开官方入口','text':'搜索劳动仲裁，选择实际办理地区，再查看办事指南。'}]
    p['source_status']='本次已打开核对' if p.get('state')=='fresh' else '沿用此前记录，需在官方页面核对' if p.get('state')=='historical' else '尚未取得可确认的办理步骤'
    p['template_links']=[{'name':t.get('material_name') or t.get('text') or t.get('control_text') or '文书模板','kind':t.get('kind','unknown'),'url':t.get('url') or p.get('source_url')} for t in p.get('templates',[]) if t.get('url') or p.get('source_url')]
    # Full responses, browser selectors and model transcripts stay in evidence.
    p.pop('selected_guide',None);p.pop('attempts',None);p.pop('ai_review',None)
    p['templates']=[{k:t[k] for k in ('material_name','text','kind','url') if k in t} for t in p.get('templates',[])]
for name in ('frontend/src/data/provinceExperiences.json','miniprogram/data/provinceExperiences.json'):
    path=ROOT/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print('Synced provincial experiences:',len(data['provinces']),data['run_id'])
