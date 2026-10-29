"""Exact-place rollout accounting and queue planning, never a coverage grant."""
from copy import deepcopy
from contextlib import closing
from datetime import datetime,timezone
import json
from pathlib import Path
import sqlite3


def _place(row):
    values=tuple(row.get(k) for k in ('province','city','district'))
    return values if all(isinstance(v,str) and v for v in values) else None


def build_rollout_targets(directory_rows,published_guides,candidates):
    """Union exact names; provider IDs are evidence, not guessed name aliases."""
    targets={}
    for kind,rows in [('directory_records',directory_rows),('published_records',published_guides),('candidate_records',candidates)]:
        for row in rows:
            if kind=='directory_records' and row.get('level')!=4 and row.get('directory_terminal') is not True:continue
            key=_place(row)
            if key is None:continue
            target=targets.setdefault(key,dict(zip(('province','city','district'),key),directory_records=[],published_records=[],candidate_records=[]))
            target[kind].append(deepcopy(row))
    for target in targets.values():
        published=bool(target['published_records'])
        ready=published and any(t.get('can_generate') is True for g in target['published_records'] for t in g.get('templates',[]))
        target['state']='generatable' if ready else 'guide_only' if published else 'candidate' if target['candidate_records'] else 'uncollected'
    return [targets[k] for k in sorted(targets)]


def build_rollout_status(directory_rows,published_guides,candidates,province_catalog):
    targets=build_rollout_targets(directory_rows,published_guides,candidates)
    catalog={p['slug']:p['name'] for p in province_catalog}
    # Unknown exact province keys remain visible; do not guess full/short aliases.
    slugs=list(catalog)+sorted({t['province'] for t in targets}-set(catalog))
    provinces=[]
    for slug in slugs:
        own=[t for t in targets if t['province']==slug]
        counts={state:sum(t['state']==state for t in own) for state in ['generatable','guide_only','candidate','uncollected']}
        provinces.append(dict(slug=slug,name=catalog.get(slug,slug),targets_total=len(own),
            published_guides=counts['generatable']+counts['guide_only'],generatable_localities=counts['generatable'],
            guide_only=counts['guide_only'],candidates=counts['candidate'],uncollected=counts['uncollected'],
            completion_status='incomplete'))
    return dict(directory_is_not_guide_coverage=True,province_count=len(provinces),targets_total=len(targets),
        published_guides=sum(p['published_guides'] for p in provinces),
        generatable_localities=sum(p['generatable_localities'] for p in provinces),
        unpublished_candidates=sum(p['candidates'] for p in provinces),provinces=provinces)


def load_rollout_candidates(root):
    root=Path(root)
    current=root/'reports/nationwide-localization-20261028/CANDIDATES.json'
    historical=root/'reports/nationwide-localization-20261023-night/PENDING-SOURCES.json'
    release=root/'config/regional_candidates.json'
    path=release if release.is_file() else current if current.is_file() else historical
    if not path.is_file():return []
    rows=json.loads(path.read_text(encoding='utf8'))
    if not isinstance(rows,list) or any(not isinstance(r,dict) or _place(r) is None for r in rows):
        raise ValueError('候选登记必须是具有完整省市区县名称的列表')
    return rows


def directory_rows(store):
    with store.connection() as db:
        return [json.loads(r['payload']) for r in db.execute('SELECT payload FROM directory_areas WHERE level=4 ORDER BY id')]


def _read_rows(path,query):
    """Read-only connections avoid constructor/schema writes during dry runs."""
    path=Path(path)
    if not path.is_file():return []
    with closing(sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True)) as db:
        db.row_factory=sqlite3.Row
        return [dict(r) for r in db.execute(query)]


def _snapshot(root):
    directory=Path(root)/'backend/data/regional-directory.sqlite'
    guides=Path(root)/'backend/data/regional-guides.sqlite'
    rows=[json.loads(r['payload']) for r in _read_rows(directory,'SELECT payload FROM directory_areas WHERE level=4 ORDER BY id')]
    published=[json.loads(r['payload']) for r in _read_rows(guides,'SELECT payload FROM regional_guides WHERE sequence IN (SELECT sequence FROM regional_current) ORDER BY province,city,district')]
    jobs=_read_rows(directory,'SELECT id,kind,payload,state FROM discovery_jobs')
    for job in jobs:job['payload']=json.loads(job['payload'])
    return rows,published,jobs


def plan_workspace(root,apply=False):
    root=Path(root);rows,published,jobs=_snapshot(root)
    candidates=load_rollout_candidates(root)
    catalog=json.loads((root/'frontend/src/data/provinceCatalog.json').read_text(encoding='utf8'))
    status=build_rollout_status(rows,published,candidates,catalog)
    existing={(j['kind'],_place(j['payload'])) for j in jobs}
    tasks=[]
    for target in build_rollout_targets(rows,published,candidates):
        kind={'uncollected':'service_discovery','guide_only':'document_adaptation','candidate':'candidate_review'}.get(target['state'])
        if not kind or (kind,_place(target)) in existing:continue
        payload={k:target[k] for k in ['province','city','district']}
        payload['directory_sources']=[{k:r[k] for k in ['id','provider','code','official_name','source_url'] if k in r} for r in target['directory_records']]
        if target['published_records']:
            payload['published_source_ids']=sorted({g['source_id'] for g in target['published_records'] if g.get('source_id')})
        tasks.append({'kind':kind,'payload':payload})
    result=dict(applied=apply,status=status,tasks=tasks,enqueued=0,
        scope='公开地区目录与自身指南待办；不等于已核验覆盖，不启动或认领工作进程',
        completion_status='incomplete')
    if not apply:return result
    from regional_directory import DirectoryStore
    path=root/'backend/data/regional-directory.sqlite'
    # Back up before even invoking the store constructor. Never touch guide/case DBs.
    if path.is_file():
        folder=root/'reports/nationwide-localization-20261028/rollout/backups';folder.mkdir(parents=True,exist_ok=True)
        stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
        backup=folder/('regional-directory-'+stamp+'.sqlite')
        with closing(sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True)) as source,closing(sqlite3.connect(backup)) as dest:source.backup(dest)
        result['backup']=str(backup.resolve())
    directory=DirectoryStore(path)
    # Re-read before enqueueing; preserve all existing states and provider jobs.
    with directory.connection() as db:
        db.execute('BEGIN IMMEDIATE')
        current={(r['kind'],_place(json.loads(r['payload']))) for r in db.execute('SELECT kind,payload FROM discovery_jobs')}
        missing=[task for task in tasks if (task['kind'],_place(task['payload'])) not in current]
    # DirectoryStore.enqueue uses stable INSERT OR IGNORE identities; no claims,
    # state resets, source updates or generation/publication flags are written.
    for task in missing:
        directory.enqueue(task['kind'],task['payload']);result['enqueued']+=1
    return result
