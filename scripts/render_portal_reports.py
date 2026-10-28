"""Render portal Word reports with installed hidden Word and bundled Poppler."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
from PIL import Image,ImageDraw,ImageFont,ImageStat
ROOT=Path(__file__).resolve().parents[1]

def inspect_images(folder):
    findings=[]
    for path in folder.glob('*/*.png'):
        with Image.open(path) as image:
            thumb=image.convert('L');thumb.thumbnail((160,100))
            histogram=thumb.histogram();blank=sum(histogram[250:])/sum(histogram)>0.999
            findings.append(dict(path=str(path),blank=blank,size=image.size))
    (folder/'image-quality.json').write_text(json.dumps(findings,ensure_ascii=False,indent=2),encoding='utf8')
    return findings

def render(folder,report=None):
    os.environ.update(TEMP=str(folder/'temp'),TMP=str(folder/'temp'))
    (folder/'temp').mkdir(exist_ok=True)
    spec=importlib.util.spec_from_file_location('office_renderer',ROOT/'scripts/validate_acquired_templates.py')
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);mod.OUTPUT_ROOT=folder/'render'
    docs=[dict(source=str(p.resolve()),format='docx',province_folder='reports') for p in folder.glob('*.docx') if report is None or p.name==report]
    if not docs:raise FileNotFoundError('No matching Word report')
    mod.convert_office_files(docs)
    for item in docs:
        if item.get('conversion')=='failed':raise RuntimeError(item)
        pdf=Path(item['pdf']);out=pdf.parent
        if not out.resolve().is_relative_to(folder.resolve()):raise ValueError('Render output outside report batch')
        for previous in [*out.glob('page-*.png'),*out.glob('overview-*.png')]:previous.unlink()
        subprocess.run([str(mod.PDFTOPPM),'-r','110','-png',str(pdf),str(out/'page')],check=True,creationflags=subprocess.CREATE_NO_WINDOW)
        pages=sorted(out.glob('page-*.png'))
        font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',16)
        for start in range(0,len(pages),8):
            sheet=Image.new('RGB',(1600,1160),'#dedede');draw=ImageDraw.Draw(sheet)
            for i,p in enumerate(pages[start:start+8]):
                x=i%4*400;y=i//4*580;draw.text((x+8,y+3),p.stem,font=font,fill='black')
                with Image.open(p) as image:
                    image.thumbnail((380,545));sheet.paste(image,(x+8,y+28))
            sheet.save(out/f'overview-{start//8+1:02d}.png')
        print(item['source'],len(pages),'pages',flush=True)
    manifest=folder/'render/manifest.json'
    if report and manifest.is_file():
        existing=json.loads(manifest.read_text(encoding='utf8'));sources={r['source'] for r in docs}
        docs=[r for r in existing if r['source'] not in sources]+docs
    manifest.write_text(json.dumps(docs,ensure_ascii=False,indent=2),encoding='utf8')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('folder',type=Path);parser.add_argument('--inspect-only',action='store_true');parser.add_argument('--report',help='Render only one changed report filename');args=parser.parse_args()
    args.folder=args.folder.resolve();inspect_images(args.folder)
    if not args.inspect_only:render(args.folder,args.report)
