"""Create a new isolated two-guide candidate after pinned root stage approval."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
import regional_jiangsu_oct30f as own
from regional_form_contracts import build_form_contract
from regional_guides import RegionalStore


def run():
    out = ROOT / own.QA_REPORT / 'candidate'
    if out.exists():
        raise ValueError('保留已有候选和证据；不得覆盖旧候选')
    guides = [own.prepare_candidate(code, root=ROOT) for code in sorted(own.SUPPORTED)]
    out.mkdir()
    store = RegionalStore(out / 'guides.sqlite')
    rows, contracts = [], []
    for guide in guides:
        guide = store.put_guide(guide)
        rows.append(guide)
        for kind in ('application', 'evidence'):
            t = next(t for t in guide['templates'] if t.get('document_types') == [kind])
            contracts.append(build_form_contract(guide, t, kind, root=ROOT))
    (out / 'guides.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf8')
    (out / 'form-contracts.json').write_text(json.dumps(contracts, ensure_ascii=False, indent=2), encoding='utf8')
    files = ['backend/regional_jiangsu_oct30f.py', 'backend/regional_adapters.py',
             'backend/regional_form_contracts.py', 'backend/regional_public_provenance.py',
             'backend/routes/regional_guides.py', 'backend/tests/test_jiangsu_oct30f.py',
             'backend/tests/test_jiangsu_oct30f_dispatch.py']
    manifest = {'scope': 'two own localities candidate only', 'published': False,
        'database': (out / 'guides.sqlite').relative_to(ROOT).as_posix(), 'source_stage_sha256': own.STAGE_SHA256,
        'source_ids': [g['source_id'] for g in rows], 'versions': [g['version'] for g in rows],
        'code_files': {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in files},
        'production_db_or_seed_changed': False, 'model_calls': 0,
        'remaining': ['native browser3757681440', 'four native confirmation downloads',
                      'downloaded files Word all-page review', 'separate root publication approval']}
    (out / 'MANIFEST.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf8')
    print(json.dumps({'database': manifest['database'], 'guides': len(rows), 'forms': len(contracts)}))


if __name__ == '__main__':
    run()
