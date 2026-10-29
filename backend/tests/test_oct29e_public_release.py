"""Only own E public files survive export, a fresh root and eight real generations."""
import hashlib
import importlib.util
import json
from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]


class EPublicReleaseTests(unittest.TestCase):
    def test_fresh_public_copy_keeps_eight_capabilities_without_private_samples_or_original_repo(self):
        from regional_zhejiang_oct29e import parse_capture as zj
        from regional_jiangsu_oct29e import parse_capture as js
        from regional_adapters import with_reference_capabilities
        spec=importlib.util.spec_from_file_location('export_c',ROOT/'scripts/export-public-data.py')
        exporter=importlib.util.module_from_spec(spec);spec.loader.exec_module(exporter)
        rows=[]
        for g in [js('xiangcheng'),js('wujiang'),zj('fuyang'),zj('jiande')]:
            g.update(published=True,publication_status='published',candidate_web_qa='PASS')
            rows.append(exporter.public_guide(with_reference_capabilities(g)))
        with tempfile.TemporaryDirectory(dir=ROOT/'.runtime') as folder:
            root=Path(folder)
            for dirname in ['backend','WenShu']:
                for p in (ROOT/dirname).rglob('*.py'):
                    target=root/p.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
            for name in ['config/document_forms.json','config/province_official_template_catalog.json']:
                p=root/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,p)
            for directory in ['jiangsu','zhejiang']:
                report='reports/nationwide-verification-20261029-e/'+directory
                white_path=ROOT/report/'PUBLIC-WHITELIST.json';white=json.loads(white_path.read_text('utf8'))
                entries=white['files'];entries={r['path']:r for r in entries} if isinstance(entries,list) else entries
                for filename,meta in entries.items():
                    if filename.startswith(('backend/','WenShu/')):continue
                    source=ROOT/filename;self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),meta['sha256'])
                    target=root/filename;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
                target=root/report/'PUBLIC-WHITELIST.json';target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(white_path,target)
            seed=root/'data/public-regions';seed.mkdir(parents=True)
            payload={'guides.json':rows,'directory.json':[]};pins={}
            for name,value in payload.items():
                body=(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode();(seed/name).write_bytes(body);pins[name]=hashlib.sha256(body).hexdigest()
            (seed/'manifest.json').write_text(json.dumps({'schema_version':1,'files':pins}),'utf8')
            script=r'''
from pathlib import Path
import io,json,zipfile
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
import public_seed,regional_zhejiang_oct29e as zj,regional_jiangsu_oct29e as js
from regional_guides import RegionalStore
from routes import regional_guides as routes
root=Path.cwd().resolve()
assert all(m.ROOT==root for m in [public_seed,zj,js,routes])
result=public_seed.bootstrap_public_data(root);assert result['guides_imported']==4 and not result['missing_attachments']
store=RegionalStore(root/'backend/data/regional-guides.sqlite');guides=store.inventory()
assert sum(any(t.get('can_generate') for t in g['templates']) for g in guides)==4
app=FastAPI();app.include_router(routes.router,prefix='/regional');count=0
with patch.object(routes,'store',return_value=store),TestClient(app) as client:
 for entry in guides:
  g=store.lookup(entry['province'],entry['city'],entry['district'])
  for t in g['templates']:
   if not t.get('can_generate'):continue
   for kind in t['document_types']:
    data={'applicantName':'虚构干净发行验证','requests':['请求支付虚构工资。'],'factsReason':'虚构本区软件验证。'} if kind=='application' else {'evidenceList':[{'name':'虚构证据','source':'本人虚构','purpose':'虚构验证'}]}
    payload={k:g[k] for k in ['province','city','district','source_id','version']};payload.update(template_id=t['id'],kind=kind,mode='blank',data=data)
    r=client.post('/regional/generate',json=payload);assert r.status_code==200,(g['district'],r.text)
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:assert z.testzip() is None
    count+=1
    payload['source_id']='wrong-own-source';assert client.post('/regional/generate',json=payload).status_code==409
  if g['province']=='jiangsu':
   for t in g['templates']:
    if t['official_kind']=='sample':
     assert not t.get('can_generate')
     r=client.get('/regional/templates/'+t['id'],params={k:g[k] for k in ['province','city','district']});assert r.status_code in [409,503]
assert count==8
print(json.dumps({'root':str(root),'guides':4,'generated':count,'models_called':False}))
'''
            env={**os.environ,'PYTHONPATH':str(root/'backend')}
            run=subprocess.run([sys.executable,'-c',script],cwd=root,env=env,capture_output=True,text=True,encoding='utf8',timeout=120)
            self.assertEqual(run.returncode,0,run.stdout+'\n'+run.stderr)
            self.assertIn('"generated": 8',run.stdout)


if __name__=='__main__':unittest.main()
