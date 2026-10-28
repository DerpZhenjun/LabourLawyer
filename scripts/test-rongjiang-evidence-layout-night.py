"""Check actual rendered pagination, not merely DOCX strings."""
import argparse,json
from pathlib import Path
import pdfplumber
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser();p.add_argument('manifest');args=p.parse_args()
    m=json.loads(Path(args.manifest).read_text(encoding='utf8'))
    task=next(t for t in m['tasks'] if Path(t['source']).stem.startswith('evidence'))
    with pdfplumber.open(task['pdf']) as pdf:
        pages=[p.extract_text() or '' for p in pdf.pages]
    assert '提交人' in pages[-1] and '注' in pages[-1], 'Signature must not be orphaned on its own page'
    for i,text in enumerate(pages):
        assert all(header in text for header in ['序号','证据名称','证据来源','证明目的','页数']),f'Actual page {i+1} lost repeated table header'
    print(json.dumps({'pages':len(pages),'signature_with_note':True,'all_headers':True}))

if __name__=='__main__':main()
