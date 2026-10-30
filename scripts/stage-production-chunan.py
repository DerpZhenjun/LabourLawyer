"""Create a NEW review-only SQLite candidate; existing stores are never modified."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from regional_guides import RegionalStore
from regional_zhejiang_chunan_oct30 import prepare_candidate
from regional_form_contracts import build_form_contract


def run(output):
    output = Path(output).resolve()
    allowed = (ROOT / 'reports/production-readiness-20261030/localities/chunan/candidate').resolve()
    if not output.is_relative_to(allowed) or output.suffix != '.sqlite':
        raise ValueError('Staging SQLite must be a new file in the Chunan review-only candidate folder')
    if output.exists():
        raise FileExistsError('Candidate already exists; never rewrite a review store')
    guide = prepare_candidate(root=ROOT)
    output.parent.mkdir(parents=True, exist_ok=True)
    guide = RegionalStore(output).put_guide(guide)
    contracts = [build_form_contract(guide, t, t['document_types'][0], root=ROOT)
                 for t in guide['templates'] if t.get('can_generate')]
    for name, content in [('guide.json', guide), ('form-contracts.json', contracts)]:
        (output.parent / name).write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding='utf8')
    print(json.dumps({'candidate': output.relative_to(ROOT).as_posix(), 'source_id': guide['source_id'],
                      'version': guide['version'], 'contracts': len(contracts), 'published': guide['published']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default=ROOT / 'reports/production-readiness-20261030/localities/chunan/candidate/guides.sqlite')
    run(parser.parse_args().output)
