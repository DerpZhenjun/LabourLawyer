"""Isolated public-regional UI staging. No model imports, private DB, or login."""
import json
import os
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
BASE=ROOT/'reports/nationwide-localization-20261023-night/cross-province/jiangsu-xishan'
if not os.getenv('LABOURLAWYER_REGIONAL_DB'):
    os.environ['LABOURLAWYER_REGIONAL_DB']=json.loads((BASE/'staging.json').read_text('utf8'))['database']
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.regional_guides import router
app=FastAPI()
app.add_middleware(CORSMiddleware,allow_origins=[os.getenv('LABOURLAWYER_TEST_ORIGIN','http://127.0.0.1:5174')],allow_methods=['*'],allow_headers=['*'])
app.include_router(router,prefix='/api/regional-guides')
if __name__=='__main__':
    import uvicorn
    uvicorn.run(app,host='127.0.0.1',port=8001)
