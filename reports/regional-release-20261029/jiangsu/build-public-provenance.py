"""Public structured own guides, never raw HTML/auth/session/database contents."""
import copy,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
BASE=ROOT/'reports/nationwide-localization-20261028/jiangsu'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
for code in ['320981','320924']:
    folder=OUT/code;g=json.loads((BASE/code/'normalized-guide.json').read_text('utf8'))
    current=json.loads((folder/'official-reviewed.json').read_text('utf8'))
    provenance=dict(region_code=code,source_url=g['source_url'],source_id=g['source_id'],authority=g['authority'],service_code=g['service_code'],
        originally_collected_at=g['collected_at'],official_rechecked_at=current['captured_at'],
        source_verification='own official browser guide and four native material dialogs; parsed identity/fields/annexes unchanged',
        public_materials=len(g['materials']),official_annexes=len(g['templates']),
        public_screenshots=[(folder/name).relative_to(ROOT).as_posix() for name in ['official-recheck.png','materials-rechecked.png']],
        sealed_recheck_sha256=sha(folder/'official-reviewed.json'),raw_html_shipped=False,
        published=False,generation_enabled=False,web_qa_status='NOT_RUN',originals=[])
    for t in g['templates']:
        assert sha(ROOT/t['file'])==t['sha256']
        provenance['originals'].append({k:t.get(k) for k in ['id','annex_id','source_url','download_url','file','original_name','file_type','bytes','sha256','official_kind','content_kind','download_status']})
    public=copy.deepcopy(g)
    for key in ['evidence','offline_adapter_matches']:public.pop(key,None)
    public.update(published=False,generation_enabled=False,review_status='candidate-not-published',web_qa_status='NOT_RUN',
                  document_visual_qa_status='PASS_OFFLINE_CURRENT_SYNTHETIC_ONLY',verified_at=current['captured_at'],
                  public_provenance=(folder/'public-provenance.json').relative_to(ROOT).as_posix())
    for t in public['templates']:
        t.pop('response_headers',None)
        t.update(can_generate=False,document_types=[])
    (folder/'public-guide.json').write_text(json.dumps(public,ensure_ascii=False,indent=2),encoding='utf8')
    provenance['public_guide_sha256']=sha(folder/'public-guide.json')
    (folder/'public-provenance.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2),encoding='utf8')
