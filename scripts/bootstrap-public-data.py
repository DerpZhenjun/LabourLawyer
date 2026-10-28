"""Initialize only empty public guide/directory databases; no private data/models."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from public_seed import bootstrap_public_data
if __name__=='__main__':print(json.dumps(bootstrap_public_data(ROOT),ensure_ascii=False,indent=2))
