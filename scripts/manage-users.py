"""Local operator CLI. Passwords never appear in command arguments or output."""
import argparse,getpass,os,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from auth_store import AuthStore,password_hash

def main():
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['create-admin','create-user','reset-password','disable','list']);parser.add_argument('--username');parser.add_argument('--auth-db',type=Path,required=True)
    args=parser.parse_args();store=AuthStore(args.auth_db.resolve())
    if args.action=='list':
        for row in store.list_users():print(row['username'],row['role'],'enabled' if row['active'] else 'disabled')
        return
    if not args.username:parser.error('--username is required')
    if args.action=='disable':
        with store.connection() as db:
            row=db.execute('SELECT * FROM auth_users WHERE username=?',(args.username.lower(),)).fetchone()
            if not row:raise ValueError('账号不存在')
            if row['role']=='admin' and row['active'] and db.execute("SELECT COUNT(*) FROM auth_users WHERE role='admin' AND active=1").fetchone()[0]<=1:raise ValueError('不能禁用最后一位管理员')
            db.execute('UPDATE auth_users SET active=0 WHERE id=?',(row['id'],));db.execute('DELETE FROM auth_sessions WHERE user_id=?',(row['id'],))
    else:
        password=getpass.getpass('New password (12-128 characters): ')
        if password!=getpass.getpass('Confirm password: '):raise ValueError('两次密码不一致')
        if args.action=='reset-password':
            value=password_hash(password)
            with store.connection() as db:
                row=db.execute('SELECT id FROM auth_users WHERE username=?',(args.username.lower(),)).fetchone()
                if not row:raise ValueError('账号不存在')
                db.execute('UPDATE auth_users SET password_hash=? WHERE id=?',(value,row['id']));db.execute('DELETE FROM auth_sessions WHERE user_id=?',(row['id'],))
        else:store.create_user(args.username,password,'admin' if args.action=='create-admin' else 'user')
    print('Account operation complete; password omitted.')

if __name__=='__main__':
    try:main()
    except ValueError as exc:print(str(exc),file=sys.stderr);sys.exit(1)
