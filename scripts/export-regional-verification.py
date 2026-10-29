"""Validate the fixed public review registry; --write-frontend updates only its UI snapshot."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from regional_verification import load_registry


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-frontend',action='store_true');args=parser.parse_args()
    rows=load_registry(ROOT);payload={'schema_version':1,'items':rows}
    path=ROOT/'frontend/src/data/regionalVerification.json'
    if args.write_frontend:path.write_bytes((json.dumps(payload,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    elif not path.is_file() or json.loads(path.read_text('utf-8'))!=payload:
        raise ValueError('Frontend review snapshot differs; validate and explicitly export it before release')
    print(json.dumps({'reviewed_places':len(rows),'candidate_guides':sum(r['guide_status']=='candidate' for r in rows),
                      'discovery_only':sum(r['guide_status']=='discovery_only' for r in rows),
                      'official_absence_claims':sum(r[k+'_template_status']=='officially_not_provided' for r in rows for k in ['application','evidence']),
                      'publication_or_generation_granted':False},ensure_ascii=False))


if __name__=='__main__':main()
