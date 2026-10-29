"""Freeze only reviewed public evidence; no publication or DB changes."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[4]
OUT=Path(__file__).resolve().parent
BASE=OUT.parent
sys.path.insert(0,str(ROOT/'backend'))
from regional_jiangsu_oct29 import ADAPTER,candidate_contract


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf8')


files=[];originals=[];reviews=[]
old=json.loads((BASE/'public-file-allowlist.json').read_text(encoding='utf8'))
for row in old['files']:
    assert sha(ROOT/row['file'])==row['sha256'] and (ROOT/row['file']).stat().st_size==row['bytes']
assert len(old['files'])==31
for code,names in [('320281',['material1','material2','material3-final','material4-final']),
                   ('320282',['material1','material2','material3','material4'])]:
    folder=BASE/code;g=json.loads((folder/'guide.json').read_text(encoding='utf8'))
    contract=candidate_contract(g)
    assert len(g['sections'])==12 and len(g['materials'])==4 and len(g['templates'])==8
    for name,material in zip(names,g['materials']):
        capture=json.loads((folder/(name+'.json')).read_text(encoding='utf8'))
        assert len(capture['visible_details'])==1 and material['name'] in capture['visible_details'][0]
        files.extend([folder/(name+'.json'),folder/(name+'.png')])
    for template in g['templates']:
        assert sha(ROOT/template['file'])==template['sha256']
        binding=next((kind for kind,item in contract['documents'].items() if item['annex_id']==template['id']),None)
        template['offline_document_type']=binding
        template['offline_qa_status']='PASS' if binding else 'NOT_ADAPTED_SAMPLE_OR_PLACEHOLDER'
        template['can_generate']=False
    flow=json.loads((folder/'flow.json').read_text(encoding='utf8'))
    assert sha(ROOT/flow['file'])==flow['sha256']
    g['flow_diagram']=flow
    g['flow_diagram']['observed_nodes']=['仲裁申请','争议受理','案前调解','立案审核','组庭审批','排庭/举证/答辩',
       '增加请求/变更请求/反申请','庭审准备','案件审理','仲裁确认','立卷归档','结果反馈']
    g['flow_diagram']['interpretation_note']='本批实际阅读自身流程图的节点抄录；原图与正文栏目分别保留。'
    note='申请材料页列申请书4份，空白申请书说明按被申请人人数提交副本；两个原文口径保留，未代替当事人决定份数。'
    if note not in g['warnings']:g['warnings'].append(note)
    if code=='320282':
        channel=json.loads((folder/'online-entry-check.json').read_text(encoding='utf8'))
        assert channel['source_url']==g['source_url'] and channel['visible_online_button_count']==0
        g['channel']['online_status']='unverified'
        g['channel']['entry_url']=None
        g['channel']['entry_check']=channel
        if channel['reason'] not in g['warnings']:g['warnings'].append(channel['reason'])
        files.append(folder/'online-entry-check.json')
    else:
        files.extend([folder/'online-boundary.json',folder/'online-boundary.png'])
    g['offline_adapter']=ADAPTER;g['offline_document_qa_status']='PASS';g['web_qa_status']='NOT_RUN'
    write(folder/'guide.json',g)
    files.extend([folder/'guide.json',folder/'official-guide.json',folder/'official-guide.png',
                  folder/'downloads.json',folder/'flow.json',folder/'flow-browser.png',ROOT/flow['file']])
    originals.append(ROOT/flow['file'])
    for item in contract['documents'].values():
        path=ROOT/item['source_file'];files.append(path);originals.append(path)
    reviews.append({'region_code':code,'source_url':g['source_url'],'source_id':g['source_id'],
                    'authority':g['authority'],'service_code':g['service_code'],'own_materials':4,
                    'own_material_downloads':8,'own_flow_downloads':1,'download_sha_mismatches':0,
                    'offline_adapter':ADAPTER,'offline_qa':'PASS','web_qa':'NOT_RUN','published':False})

render=json.loads((OUT/'final-render-manifest.json').read_text(encoding='utf8'))
packages=json.loads((OUT/'final-package-checks.json').read_text(encoding='utf8'))
assert len(render)==4 and sum(row['pages'] for row in render)==6
approved=[]
for row,package in zip(render,packages):
    assert row['sha256']==package['output_sha256']==sha(Path(row['source']))
    approved.append({'region_code':row['region_code'],'kind':row['kind'],'output':package['output'],
                     'output_sha256':package['output_sha256'],'pages':row['pages'],
                     'page_images':[{'file':p,'sha256':sha(ROOT/p)} for p in row['page_images']],
                     'visual_review_status':'PASS','review_method':'Every final page opened with view_image',
                     'checks':['Own locality/committee','All synthetic data','No clipping/overlap/missing glyphs',
                               'Blank signature and handwritten date','Application copies 3 / evidence copies 2',
                               'Evidence six columns / one item / three pages'],
                     'limitations':'Only this short synthetic payload; long facts and multi-item stress visual QA not run'})
write(OUT/'document-approval.json',{'adapter':ADAPTER,'published':False,'web_qa':'NOT_RUN','approved_final_outputs':approved,
                                 'obsolete_outputs':'Initial filled outputs had wrong evidence copies and are excluded',
                                 'original_docx_files_rendered':14,'original_pages_opened':26,'final_pages_opened':6})
write(OUT/'TEST-RESULTS.json',{'targeted_unit_tests':{'methods':7,'result':'PASS','evidence':'copy-count-green.txt'},
                            'original_package_sha_mismatches':0,'original_material_downloads':16,'flow_downloads':2,
                            'source_and_annex_checks':reviews,'first_batch_files_unchanged':31,
                            'full_backend_tests':'NOT_RUN_BY_SUBAGENT','candidate_web_qa':'NOT_RUN',
                            'clean_public_copy_tests':json.loads((OUT/'public-copy-result.json').read_text(encoding='utf8'))})
for relative in ['backend/regional_jiangsu_oct29.py','backend/tests/test_jiangsu_oct29.py']:
    files.append(ROOT/relative)
for name in ['collect.py','qa.py','finalize.py','HANDOFF.md','artifact.md','document-approval.json','TEST-RESULTS.json',
             'final-package-checks.json','320281-adaptation-contract.json','320282-adaptation-contract.json',
             'copy-count-green.txt','public-copy-tests.txt','public-copy-result.json']:
    files.append(OUT/name)
assert len(set(files))==len(files)
manifest={'schema_version':1,'scope':'batch2 Jiangyin/Yixing public evidence and own blank originals only',
          'first_batch_manifest_preserved':'public-file-allowlist.json',
          'first_batch_files_rechecked_unchanged':31,
          'original_file_allowlist':[p.relative_to(ROOT).as_posix() for p in originals],
          'excluded':['Unlisted intermediary captures and initial incorrect outputs',
                      'Identity-photo example JPGs and unnecessary samples/placeholders',
                      'Generated DOCX/PNG/PDF, Word process logs and local rendering inventories',
                      'No HAR/cookies/headers/raw HTML/SSO state was saved'],
          'files':[{'file':p.relative_to(ROOT).as_posix(),'sha256':sha(p),'bytes':p.stat().st_size} for p in files]}
write(BASE/'public-file-allowlist-batch2.json',manifest)
print(json.dumps({'allowlisted_files':len(files),'own_blank_originals':4,'own_flow_originals':2,'old_files_unchanged':31}))
