"""Explicit local-only ownership migration. Never auto-claim or expose old cases."""
import argparse,sqlite3,sys,uuid
from contextlib import closing
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from auth_store import AuthStore

def claim(cases_db,auth_db,case_id,username):
    cases_db=Path(cases_db).resolve()
    if not cases_db.is_file() or not Path(auth_db).is_file():raise ValueError('请指定现有案件库和账号库')
    user=next((u for u in AuthStore(auth_db).list_users() if u['username']==username.strip().lower() and u['active']),None)
    if not user:raise ValueError('目标账号不存在或已停用')
    with closing(sqlite3.connect(cases_db)) as db:
        db.execute('BEGIN IMMEDIATE')
        row=db.execute('SELECT owner_user_id FROM cases WHERE id=?',(case_id,)).fetchone()
        if row is None or row[0] is not None:raise ValueError('案件不存在或已有归属，不会覆盖')
        # Back up through a separate read connection before changing ownership.
        backup=cases_db.with_name(cases_db.name+'.before-claim-'+uuid.uuid4().hex+'.sqlite3')
        with closing(sqlite3.connect(cases_db)) as source,closing(sqlite3.connect(backup)) as dest:source.backup(dest)
        db.execute('UPDATE cases SET owner_user_id=? WHERE id=? AND owner_user_id IS NULL',(user['id'],case_id));db.commit()
    return backup

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--cases-db',type=Path,required=True);p.add_argument('--auth-db',type=Path,required=True);p.add_argument('--case-id',required=True);p.add_argument('--username',required=True);a=p.parse_args()
    try:claim(a.cases_db,a.auth_db,a.case_id,a.username);print('Ownership assigned; consistent backup retained beside the case database.')
    except (ValueError,sqlite3.Error) as exc:print(str(exc),file=sys.stderr);sys.exit(1)
