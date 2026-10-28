"""Hash retained capture files, distinguishing file bytes from canonical JSON payloads."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'reports/nationwide-localization-20261023-night/cross-province/beijing-dongcheng'
def main():
    target=BASE/'staging-round28/source-file-checksums.json'
    if target.exists():raise ValueError('Preserve file checksum manifest')
    p=BASE/'capture-remaining-round28'
    files=[p/f'section-{i}.json' for i in range(7)]+[p/(n+'.json') for n in ['basic-expanded','materials-final','flow-final','before-online','online-after']]
    rows=[]
    for f in files:
        page=json.loads(f.read_text('utf8'));rows.append({'file':f.relative_to(ROOT).as_posix(),'source_url':page['url'],
            'collected_at':page['captured_at'],'file_sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
    target.write_text(json.dumps({'captures':rows,'note':'File-byte SHA256. Existing staging source-checksums.json sha256 values were canonical sorted-JSON payload hashes, not file-byte hashes; retain that old provenance and use this explicit file-byte manifest. No capture was rewritten.'},ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({'retained_capture_files_hashed':len(rows),'capture_files_modified':0}))
if __name__=='__main__':main()
