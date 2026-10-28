"""Assemble isolated public-guide candidates; never publish or touch case databases."""
import hashlib,json,sqlite3,sys
from contextlib import closing
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from regional_guides import RegionalStore
from regional_adapters import with_reference_capabilities

OUT=ROOT/'reports/nationwide-localization-20261028'
OLD=ROOT/'reports/nationwide-localization-20261023-night'

def read(path):return json.loads(path.read_text('utf8'))
def save(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')

def run():
    stage=OUT/'acceptance';stage.mkdir(parents=True,exist_ok=True)
    dbpath=stage/'regional-guides.sqlite'
    if dbpath.exists():raise RuntimeError('Use a fresh candidate DB; preserve prior evidence')
    for name in ['regional-guides.sqlite','regional-directory.sqlite']:
        source=ROOT/'backend/data'/name
        with closing(sqlite3.connect(source.resolve().as_uri()+'?mode=ro',uri=True)) as src,closing(sqlite3.connect(stage/name)) as dst:src.backup(dst)
    store=RegionalStore(dbpath);rows=read(OLD/'PENDING-SOURCES.json');staged=[]
    folders={'tianjin':'tianjin-eco-city','江西蓉江新区':'jiangxi-rongjiang',
             '大丰区':'jiangsu-dafeng','海州区':'jiangsu-haizhou','白云区':'guangdong-baiyun',
             '蓉江新区':'jiangxi-rongjiang','通州区':'beijing-tongzhou','朝阳区':'beijing-chaoyang',
             '东城区':'beijing-dongcheng','南沙区':'guangdong-nansha','福田区':'guangdong-futian','芙蓉区':'hunan-furong'}
    for row in rows:
        folder=OLD/'cross-province'/folders.get(row['district'],folders.get(row['province'],''))
        databases=sorted(folder.rglob('staging.sqlite'),key=lambda p:p.stat().st_mtime,reverse=True)
        guide=None
        for db in databases:
            with closing(sqlite3.connect(db.resolve().as_uri()+'?mode=ro',uri=True)) as con:
                result=con.execute('SELECT payload FROM regional_guides WHERE province=? AND city=? AND district=? AND sequence IN (SELECT sequence FROM regional_current)',tuple(row[k] for k in ['province','city','district'])).fetchone()
            if result:
                guide=json.loads(result[0]);row['staging_origin']=db.relative_to(ROOT).as_posix();break
        if guide is None:raise RuntimeError('No exact retained staging guide: '+row['district'])
        guide=with_reference_capabilities(guide)
        own=store.put_guide(guide);row['candidate_guide']=f"reports/nationwide-localization-20261028/acceptance/guides/{own['source_id']}.json"
        save(ROOT/row['candidate_guide'],own);staged.append({k:own[k] for k in ['province','city','district','source_id','version']})
        row['browser_acceptance']='PENDING_FRESH_AUTHORIZED_ACCEPTANCE';row['published']=False
    for code in ['320903','320902']:
        folder=OUT/'jiangsu'/code;row=read(folder/'staging-candidate.json')
        own=store.put_guide(with_reference_capabilities(read(folder/'normalized-guide.json')))
        row['candidate_guide']=f"reports/nationwide-localization-20261028/acceptance/guides/{own['source_id']}.json"
        save(ROOT/row['candidate_guide'],own);rows.append(row);staged.append({k:own[k] for k in ['province','city','district','source_id','version']})
    save(OUT/'CANDIDATES.json',rows)
    save(stage/'staged.json',{'published':False,'case_database':'isolated runtime only','items':staged})
    print(json.dumps({'candidates':len(staged),'guides':len(store.inventory()),'stage':str(stage)},ensure_ascii=False))

if __name__=='__main__':run()
