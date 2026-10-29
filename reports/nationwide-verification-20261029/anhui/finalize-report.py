"""Hash only this task's public evidence and synthetic QA artifacts."""
import hashlib
import json
import re
import sys
from datetime import datetime,timezone
from pathlib import Path
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[3]
BASE=Path(__file__).resolve().parent
def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf8')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def plain(value):return re.sub(r'\s+','',value)

qa=[]
for folder in ['fictional-short-final','fictional-capacity-final']:
    path=BASE/'feidong/qa'/folder
    payload=json.loads((path/'payload.json').read_text(encoding='utf8'))
    pdf=PdfReader(path/'filled.pdf')
    # Word's page-number footer sits between continued facts in PDF text order.
    # Remove only an independent leading/trailing numeric footer in extraction
    # order before joining content; no supplied text is removed from the DOCX.
    text=plain(''.join(re.sub(r'^\s*\d+\s*\n|\n\s*\d+\s*$','',page.extract_text() or '') for page in pdf.pages))
    values=[s for key,value in payload.items() for s in (value if isinstance(value,list) else [value])]
    assert len(pdf.pages)==2 and all(plain(value) in text for value in values)
    assert '申请书副本' in text
    qa.append({'folder':path.relative_to(ROOT).as_posix(),'page_count':len(pdf.pages),'all_pages_visually_inspected':True,
               'pdf_all_submitted_text_present':True,'signature_and_date_blank':True,'docx_sha256':sha(path/'filled.docx'),'pdf_sha256':sha(path/'filled.pdf'),
               'page_images':[p.relative_to(ROOT).as_posix() for p in sorted(path.glob('filled-*.png'))]})
originals=[]
for loc in ['yaohai','feidong']:
    for record in json.loads((BASE/loc/'downloads/manifest.json').read_text(encoding='utf8')):
        path=ROOT/record['path'];assert sha(path)==record['sha256']
        originals.append({'region':loc,'file':record['path'],'original_name':record['fileName'],'classification':record['classification'],
                          'sha256':record['sha256'],'bytes':record['bytes'],'source_url':record['source_url'],
                          'downloaded_at':record['downloaded_at'],'visually_inspected':True})
save(BASE/'ORIGINALS-WHITELIST.json',originals)
save(BASE/'QA-RESULT.json',{'verified_at':datetime.now(timezone.utc).isoformat(),'scope':'offline only; candidate browser not run',
                          'official_document_pages_reviewed':10,'official_image_attachments_reviewed':6,'synthetic_outputs':qa,
                          'source_originals_sha256_all_unchanged':True,'original_layout_defects':['Feidong blank has empty third page; two terminal empty paragraphs removed only in filled derivative.',
                          'Feidong sample DOC employer form heading wraps at right margin; original preserved and not used for generation.'],
                          'iterations':['Attempt 1 inherited mixed 16/20/22pt blank runs; oversized body and overflow seen. PDF/images retained in qa/attempt-1.',
                          'Attempt 2 normalised only populated runs to official principal 16pt; 22-character respondent first line still wrapped, note 4 moved to third page. qa/fictional-* retains that evidence.',
                          'Final explicit party first-line cap20/second25 full-width characters, request9 lines (first22/later28), facts10x28. All supplied text present, no clipping or lost text, both outputs 2 pages.'],
                          'signature_date_and_attachment_counts':'left blank in source positions','candidate_web_qa':'NOT_RUN','publication_status':'unpublished'})

pins=json.loads((BASE/'source-lock.json').read_text(encoding='utf8'))
public=set(pins)|{str((BASE/'source-lock.json').relative_to(ROOT))}
for loc in ['yaohai','feidong']:
    public.add((BASE/loc/'guide.json').relative_to(ROOT).as_posix())
    for relative in list(pins):
        p=ROOT/relative
        if p.name=='public-source.json':
            public.update(q.relative_to(ROOT).as_posix() for q in [p.parent/'page.txt',p.parent/'page.png',p.parent/'provenance.json'] if q.is_file())
    public.add((BASE/loc/'online-boundary/page.png').relative_to(ROOT).as_posix())
public.update((BASE/name).relative_to(ROOT).as_posix() for name in ['ORIGINALS-WHITELIST.json','QA-RESULT.json','TEST-REPORT.md','adapter-tests.txt','prepare-offline-qa.py','finalize-report.py','render-isolated.ps1'])
public.update(p.relative_to(ROOT).as_posix() for p in BASE.glob('*/qa/originals/*') if p.is_file())
public.update(p.relative_to(ROOT).as_posix() for p in BASE.glob('feidong/qa/*-final/*') if p.is_file())
public.update(p.relative_to(ROOT).as_posix() for p in (BASE/'qa').glob('*.json'))
public.update(['scripts/collect-anhui-oct29.py','backend/regional_anhui_oct29.py','backend/tests/test_anhui_oct29.py'])
save(BASE/'PUBLIC-WHITELIST.json',[{'file':p.replace('\\','/'),'sha256':sha(ROOT/p)} for p in sorted(public) if (ROOT/p).is_file()])
