"""Read-only PDF glyph comparison: explain, rather than guess at, a raster diff."""
import json
from pathlib import Path
import pdfplumber
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/nationwide-localization-20261023-night/cross-province/jiangxi-rongjiang/document-qa'

def main():
    target=OUT/'glyph-diagnosis.json'
    if target.exists():raise ValueError('Preserve existing diagnosis')
    originals=json.loads((OUT/'original-render.json').read_text(encoding='utf8'))
    converted=json.loads((OUT/'converted-reference.json').read_text(encoding='utf8'))
    paths=[originals['tasks'][0]['pdf'],converted['tasks'][0]['pdf']]
    values=[]
    for path in paths:
        with pdfplumber.open(path) as pdf:
            page=pdf.pages[1]
            chars=[{k:c[k] for k in ('text','x0','x1','top','bottom','fontname','size')} for c in page.chars if 630<c['top']<685]
            values.append({'pdf':path,'text':''.join(c['text'] for c in chars),'chars':chars})
    a,b=values
    differences=[{'index':i,'original':x,'converted':y} for i,(x,y) in enumerate(zip(a['chars'],b['chars'])) if x!=y]
    result={'values':values,'equal_text':a['text']==b['text'],'counts':[len(x['chars']) for x in values],
            'differences':differences,'read_only':True,'models':0}
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({'equal_text':result['equal_text'],'counts':result['counts'],'differences':differences},ensure_ascii=True))

if __name__=='__main__':main()
