"""Generate actual frontend examples and all-page visual comparison artifacts.

No visible windows, no browser downloads, original official templates untouched.
Windows Word COM is used when the bundled LibreOffice renderer is unavailable.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from docx import Document

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from province_documents import PROVINCE_DOCUMENTS, get_province_document
from WenShu.generic_template_fill import generate_application,generate_evidence
from WenShu.exact_template_fill import select_form
from WenShu.Zhejiang.LAdocx import _keep_worker_form_only

OUT=ROOT/'templates'/'_validation'/'generated-documents'
RUNTIME=Path(r'C:\Users\DerpZhenjun\.cache\codex-runtimes\codex-primary-runtime\dependencies')

def generate():
    OUT.mkdir(parents=True,exist_ok=True)
    examples=json.loads((ROOT/'.runtime/document-audit/frontend-examples.json').read_text(encoding='utf8'))
    tasks=[]
    for example in examples:
        for kind in PROVINCE_DOCUMENTS[example['slug']]['documents']:
            _,path=get_province_document(example['slug'],kind)
            digest=hashlib.sha256(path.read_bytes()).hexdigest()
            folder=OUT/example['slug']/kind
            folder.mkdir(parents=True,exist_ok=True)
            official=Document(path)
            select_form(official,path,kind)
            if example['slug']=='zhejiang' and kind=='application':
                _keep_worker_form_only(official)
            original=folder/'official-form.docx'
            official.save(original)
            generated=folder/'example.docx'
            (generate_application if kind=='application' else generate_evidence)(example[kind],path).save(generated)
            assert digest==hashlib.sha256(path.read_bytes()).hexdigest()
            tasks.append({'slug':example['slug'],'kind':kind,'name':example['name'],'template':str(path),'template_sha256':digest,'official':str(original),'generated':str(generated)})
            print(example['slug'],kind,flush=True)
    (OUT/'manifest.json').write_text(json.dumps(tasks,ensure_ascii=False,indent=2),encoding='utf8')
    return tasks

def render(tasks):
    from PIL import Image, ImageDraw, ImageFont
    # Reuse the established hidden Office exporter, with output isolated here.
    spec=importlib.util.spec_from_file_location('office_renderer',ROOT/'scripts/validate_acquired_templates.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.OUTPUT_ROOT=OUT/'render'
    documents=[]
    for task in tasks:
        for role in ('official','generated'):
            documents.append({'source':task[role],'format':'docx','province_folder':task['slug']+'/'+task['kind']+'/'+role})
    module.convert_office_files(documents)
    font=ImageFont.truetype(r'C:\Windows\Fonts\msyh.ttc',24)
    for task in tasks:
        pages={}
        for role in ('official','generated'):
            item=next(x for x in documents if x['source']==task[role])
            if item.get('conversion')=='failed':
                task[role+'_render_error']='Office export failed';continue
            pdf=Path(item['pdf'])
            # Do not retain old pages after a repair reduces the page count.
            if not pdf.parent.resolve().is_relative_to(OUT.resolve()):
                raise ValueError('render output escaped audit directory')
            for old in pdf.parent.glob('page-*.png'):
                old.unlink()
            subprocess.run([str(module.PDFTOPPM),'-scale-to','1600','-png',str(pdf),str(pdf.parent/'page')],check=True,creationflags=subprocess.CREATE_NO_WINDOW)
            pages[role]=sorted(pdf.parent.glob('page-*.png'))
            task[role+'_pages']=[str(p) for p in pages[role]]
        task['comparisons']=[]
        for i in range(max((len(p) for p in pages.values()),default=0)):
            sheet=Image.new('RGB',(1700,1240),'#eeeeee');draw=ImageDraw.Draw(sheet)
            for col,role in enumerate(('official','generated')):
                draw.text((col*850+10,10),f'{task["slug"]} {task["kind"]} {role} page {i+1}',fill='black',font=font)
                if i<len(pages.get(role,[])):
                    img=Image.open(pages[role][i]);img.thumbnail((830,1180));sheet.paste(img,(col*850+10,50))
                else:draw.text((col*850+20,100),'No corresponding page (blank slots removed)',fill='black',font=font)
            dest=OUT/task['slug']/task['kind']/f'comparison-{i+1}.png';sheet.save(dest)
            task['comparisons'].append(str(dest))
        print('rendered',task['slug'],task['kind'],{k:len(v) for k,v in pages.items()},flush=True)
    (OUT/'manifest.json').write_text(json.dumps(tasks,ensure_ascii=False,indent=2),encoding='utf8')

def vision(tasks):
    from template_acquisition.openclaw_bridge import describe_image, COMPARISON_VISION_PROMPT
    prompt=COMPARISON_VISION_PROMPT
    failures=0
    for task in tasks:
        reviews=[]
        for page_index, screenshot in enumerate(task.get('comparisons',[])):
            if 'generated_pages' in task and page_index >= len(task['generated_pages']):
                reviews.append({'image':screenshot,'skipped':'右侧没有生成文书页；删除的空白填写页仅保留对比图，不交由模型推测'});continue
            if failures>=2:
                reviews.append({'image':screenshot,'skipped':'连续两次视觉调用失败，保留截图供人工复核'});continue
            dest=Path(screenshot).with_suffix('.openclaw.json')
            try:describe_image(Path(screenshot),dest,OUT/'openclaw',timeout_seconds=240,prompt=prompt,role='generated_template_comparison')
            except Exception as exc:
                reviews.append({'image':screenshot,'error':str(exc)});failures+=1;continue
            reviews.append({'image':screenshot,'result':str(dest)})
            print('vision',task['slug'],task['kind'],Path(screenshot).name,flush=True)
        task['vision']=reviews
        (OUT/'manifest.json').write_text(json.dumps(tasks,ensure_ascii=False,indent=2),encoding='utf8')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--render',action='store_true');parser.add_argument('--vision',action='store_true');parser.add_argument('--existing',action='store_true');parser.add_argument('--province')
    args=parser.parse_args()
    tasks=json.loads((OUT/'manifest.json').read_text(encoding='utf8')) if args.existing else generate()
    all_tasks=tasks
    if args.province:tasks=[t for t in tasks if t['slug']==args.province]
    if args.render:render(tasks)
    if args.vision:vision(tasks)
    if args.province:
        # Keep unselected regions in the manifest during a targeted repair.
        selected={(t['slug'],t['kind']):t for t in tasks}
        (OUT/'manifest.json').write_text(json.dumps([selected.get((t['slug'],t['kind']),t) for t in all_tasks],ensure_ascii=False,indent=2),encoding='utf8')
