"""Normalize saved evidence, check AI claims, and publish the client snapshot.

Does not revisit portals or ask the model again. It uses only captured HTML,
official JSON responses and the completed OpenClaw outputs for this batch.
"""
import argparse,json,re,sys,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'));sys.path.insert(0,str(ROOT/'scripts'))
from province_experience import EXPERIENCE_ROOT,plain_guide,guide_rank
from province_documents import PROVINCE_DOCUMENTS
from portal_audit import write_json
from portal_workflows import parse_public_record,official_region_names,clean
import importlib.util
spec=importlib.util.spec_from_file_location('refresh',ROOT/'scripts/refresh-province-experiences.py');refresh=importlib.util.module_from_spec(spec);spec.loader.exec_module(refresh)

def material_names(html):
    from lxml import html as parser
    tree=parser.fromstring(html);names=[]
    for table in tree.xpath('//table'):
        rows=table.xpath('./tr|./thead/tr|./tbody/tr')
        column=None;start=None
        for i,row in enumerate(rows[:6]):
            cells=row.xpath('./td|./th')
            labels=[re.sub(r'\s+','',c.text_content()) for c in cells]
            for j,label in enumerate(labels):
                if label in ('材料名称','申请材料名称','申报材料名称','所需材料名称'):
                    column=j;start=i;break
            if column is not None:break
        if column is None:continue
        for row in rows[start+1:]:
            cells=row.xpath('./td|./th')
            if len(cells)<=column:continue
            value=clean(cells[column].text_content())
            if 1<len(value)<100 and not re.search('材料名称|展开|申请材料总体',value):names.append(value)
    return list(dict.fromkeys(names))

def ai_findings(ai,observations,folder=None):
    text='\n'.join(o.get('text','') for o in ai.get('output',[]))
    try:
        data=json.loads(re.sub(r'^```(?:json)?\s*|\s*```$','',text.strip()))
        if not isinstance(data,list):raise ValueError('Expected per-image array')
        expected={Path(i['filename']).stem for i in ai.get('inputs',[])}
        if {x.get('stage') for x in data}!=expected:raise ValueError('截图阶段未完整对应')
        discrepancies=[];resolutions=[]
        for x in data:
            obs=next((o for o in observations if o['stage']==x['stage']),{})
            if x['stage'].endswith('-templates') and x.get('has_template_download')!=bool(obs.get('template_links')):
                discrepancies.append(x['stage']+'：AI可见下载判断与程序记录不同，保留两份意见，不自动修改模板状态。')
                text=folder/obs.get('text_file','missing.txt') if folder else None
                if text and text.is_file() and re.search('下载办事指南|指南下载',text.read_text(encoding='utf8')):
                    resolutions.append(x['stage']+'：程序已核对下载按钮为办事指南。AI的文书模板下载判断未采纳。')
                links=obs.get('template_links',[])
                if links and all(link.get('kind')=='reference_pdf' for link in links):
                    resolutions.append(x['stage']+'：截图是官方PDF手册中的申请书格式本身，没有独立下载按钮。已保留PDF及页码链接，不能当作可在线填写的Word模板。')
        return {'parse_state':'valid','findings':data,'discrepancies':discrepancies,'resolutions':resolutions}
    except (ValueError,TypeError,KeyError) as exc:return {'parse_state':'failed','error':str(exc),'findings':[],'discrepancies':[]}

def names_from_text(text):
    lines=[s.strip() for s in text.splitlines() if s.strip()]
    names=[]
    for i,line in enumerate(lines):
        if line in ('必要','非必要','必需','非必需') and i+1<len(lines):candidate=lines[i+1]
        elif re.match('纸质材料|电子材料',line) and i: candidate=lines[i-1]
        else:continue
        if 1<len(candidate)<100 and not re.search('下载|示例|模板|原件|复印件|展开|份数',candidate):names.append(candidate)
    return list(dict.fromkeys(names))

def retain_material_evidence(guide,detected,structured):
    # A matching official JSON response gives actual material names, quantities
    # and requirements. A visual footer/column guess must not replace them.
    if structured:return
    if detected:guide.update(materials=detected,materials_complete=True)
    elif 'materials_complete' not in guide:guide['materials_complete']=False

def main(run,publish=True):
    run=run.resolve()
    if not run.is_relative_to(EXPERIENCE_ROOT.resolve()):raise ValueError('Unexpected output directory')
    data=json.loads((run/'experiences.json').read_text(encoding='utf8'))
    for slug,p in data['provinces'].items():
        folder=run/slug;guide=p.get('selected_guide')
        if guide and p['state']=='fresh':
            structured_materials=False
            response_path=folder/'public-guide-responses.json'
            responses=json.loads(response_path.read_text(encoding='utf8')) if response_path.exists() else []
            for record in responses:
                if refresh.response_matches(record,guide['guide_url']):
                    parsed=parse_public_record(record)
                    if parsed:
                        guide.update(parsed)
                        structured_materials=structured_materials or bool(parsed.get('materials'))
            names=official_region_names(responses)
            guide['region_name']=guide.get('region_name') or names.get(str(guide.get('region_code','')),'')
            html=folder/(guide['stage']+'.html')
            detected=material_names(html.read_text(encoding='utf8')) if html.exists() else []
            text_file=folder/(guide['stage']+'.txt')
            if not detected and text_file.exists():detected=names_from_text(text_file.read_text(encoding='utf8'))
            retain_material_evidence(guide,detected,structured_materials)
        if guide:
            p.update(plain_guide(guide,slug,PROVINCE_DOCUMENTS[slug].get('scope','')))
            p['capital_confirmed']=not guide_rank(guide,slug)[1]
            p['templates']=guide.get('templates',[])
        if not p.get('steps'):p['steps']=[{'title':'先打开官方入口','text':'搜索劳动仲裁，选择实际办理地区，再查看办事指南。'}]
        ai=p.get('ai_review',{})
        obs=json.loads((folder/'observations.json').read_text(encoding='utf8'))
        ai.update(ai_findings(ai,obs,folder));p['ai_review']=ai
        write_json(folder/'ai.json',ai);write_json(folder/'experience.json',p)
    write_json(run/'experiences.json',data)
    status=json.loads((run/'status.json').read_text(encoding='utf8'))
    status['ai_parsed']=sum(p['ai_review']['parse_state']=='valid' for p in data['provinces'].values())
    status['capital_confirmed']=sum(bool(p.get('capital_confirmed')) for p in data['provinces'].values())
    status['ai_discrepancies']=sum(bool(p['ai_review']['discrepancies']) for p in data['provinces'].values())
    write_json(run/'status.json',status)
    if publish:
        write_json(EXPERIENCE_ROOT/'latest.json',{'id':run.name,**status})
        subprocess.run([sys.executable,str(ROOT/'scripts/sync-province-experiences.py')],check=True)
    print(json.dumps(status,ensure_ascii=False),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('run',type=Path);parser.add_argument('--no-publish',action='store_true');args=parser.parse_args();main(args.run,publish=not args.no_publish)
