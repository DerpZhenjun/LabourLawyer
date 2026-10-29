"""Explicit preparation/verification only; never launches candidate services."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from candidate_review import prepare,verify,extend_hunan

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group();mode.add_argument('--prepare',action='store_true');mode.add_argument('--append-hunan',action='store_true');args=parser.parse_args()
    result=prepare() if args.prepare else extend_hunan() if args.append_hunan else verify()
    print(json.dumps({'state':'prepared' if args.prepare else 'verified','guide_count':result['guides'],
                      'candidate_guides':result['candidate_guides'],'models_disabled':True,'service_started':False,'main_database_modified':False},ensure_ascii=False))
