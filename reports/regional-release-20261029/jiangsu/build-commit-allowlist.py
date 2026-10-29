"""Commit candidates only: excludes synthetic outputs, Word runtime and raw captures."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
paths=[ROOT/'backend/regional_jiangsu_candidates.py',ROOT/'backend/tests/test_jiangsu_release_candidates.py',
       OUT/'HANDOFF.md',OUT/'artifact.md',OUT/'document-approval.json',OUT/'source-recheck.json',
       OUT/'build-public-provenance.py',OUT/'build-commit-allowlist.py']
required=[];optional=[]
for code in ['320981','320924']:
    folder=OUT/code
    paths += [folder/n for n in ['public-guide.json','public-provenance.json','adaptation-contract.json','document-approval.json',
                                 'official-recheck.png','materials-rechecked.png']]
    contract=json.loads((folder/'adaptation-contract.json').read_text('utf8'))
    for item in contract['documents'].values():
        path=ROOT/item['source_file'];assert hashlib.sha256(path.read_bytes()).hexdigest()==item['source_sha256']
        required.append(path);paths.append(path)
    guide=json.loads((folder/'public-guide.json').read_text('utf8'))
    optional += [t['file'] for t in guide['templates'] if ROOT/t['file'] not in required]
allowlist=dict(scope='Exact commit whitelist; source assets/structured public provenance and code only, no publication approval.',
    files=[dict(path=p.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in dict.fromkeys(paths)],
    required_runtime_own_blanks=[p.relative_to(ROOT).as_posix() for p in required],
    optional_existing_public_sample_assets=optional,
    excluded=['All generated synthetic .docx and derived PDF/PNG renders','All raw HTML/full-DOM JSON/browser-actions/session/cookie files',
              'All Word process/cleanup/conversion runtime logs','Private DBs or model configuration','Unrelated ModelFinetune files'])
(OUT/'public-file-allowlist.json').write_text(json.dumps(allowlist,ensure_ascii=False,indent=2),encoding='utf8')
print(len(allowlist['files']),'commit candidates;',len(required),'own runtime blanks; no generated outputs/runtime logs')
