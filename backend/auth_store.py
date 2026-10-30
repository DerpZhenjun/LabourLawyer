"""Local account/session persistence; no default accounts, passwords or import IO."""
from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import hmac
import os
from pathlib import Path
import re
import secrets
import sqlite3
import time
import uuid

ROUNDS=600_000
SESSION_SECONDS=8*60*60


class AuthFailure(ValueError):
    def __init__(self,status,detail):self.status=status;super().__init__(detail)


@dataclass(frozen=True)
class Identity:
    id:str
    username:str
    role:str
    session_hash:str=''

    def public(self):return {'id':self.id,'username':self.username,'role':self.role}


def password_hash(password):
    if not isinstance(password,str) or not 12<=len(password)<=128:
        raise ValueError('密码长度应为12至128个字符')
    salt=secrets.token_hex(16)
    digest=hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),ROUNDS).hex()
    return f'pbkdf2_sha256${ROUNDS}${salt}${digest}'


def password_matches(password,stored):
    try:
        scheme,rounds,salt,want=stored.split('$')
        if scheme!='pbkdf2_sha256' or int(rounds)!=ROUNDS:return False
        got=hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),int(rounds)).hex()
        return hmac.compare_digest(got,want)
    except (ValueError,TypeError,AttributeError):return False


class AuthStore:
    def __init__(self,path=None):
        self.path=Path(path or os.getenv('LABOURLAWYER_AUTH_DB',Path(os.getenv('LABOURLAWYER_DATA_DIR',Path(__file__).parent/'data'))/'auth.sqlite3'))

    @contextmanager
    def connection(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        db=sqlite3.connect(self.path,timeout=10);db.row_factory=sqlite3.Row
        db.executescript('''
        CREATE TABLE IF NOT EXISTS auth_users(id TEXT PRIMARY KEY,username TEXT NOT NULL UNIQUE,password_hash TEXT NOT NULL,role TEXT NOT NULL CHECK(role IN ('user','admin')),active INTEGER NOT NULL DEFAULT 1,created_at REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS auth_sessions(token_hash TEXT PRIMARY KEY,user_id TEXT NOT NULL,expires_at REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS auth_attempts(peer TEXT NOT NULL,username TEXT NOT NULL,at REAL NOT NULL);
        CREATE INDEX IF NOT EXISTS auth_attempts_time ON auth_attempts(at);
        ''')
        try:yield db;db.commit()
        except BaseException:db.rollback();raise
        finally:db.close()

    def create_user(self,username,password,role='user'):
        username=username.strip().lower()
        if not re.fullmatch(r'[a-z0-9._@-]{3,64}',username) or role not in {'user','admin'}:raise ValueError('账号须为3至64位字母、数字或 . _ @ -')
        value=password_hash(password);identifier=uuid.uuid4().hex
        with self.connection() as db:
            try:db.execute('INSERT INTO auth_users(id,username,password_hash,role,created_at) VALUES(?,?,?,?,?)',(identifier,username,value,role,time.time()))
            except sqlite3.IntegrityError as exc:raise ValueError('账号已存在') from exc
        return Identity(identifier,username,role)

    def login(self,username,password,peer):
        username=username.strip().lower();now=time.time();peer=hashlib.sha256(peer.encode()).hexdigest()
        failure=None;result=None
        with self.connection() as db:
            # Serialize rate checks and counter writes across worker processes.
            db.execute('BEGIN IMMEDIATE')
            db.execute('DELETE FROM auth_attempts WHERE at<?',(now-900,))
            count=db.execute('SELECT COUNT(*) FROM auth_attempts WHERE peer=?',(peer,)).fetchone()[0]
            account_count=db.execute('SELECT COUNT(*) FROM auth_attempts WHERE username=?',(username,)).fetchone()[0]
            if count>=20 or account_count>=6:failure=AuthFailure(429,'尝试次数较多，请15分钟后重试')
            else:
                row=db.execute('SELECT * FROM auth_users WHERE username=?',(username,)).fetchone()
                # Same work for an unknown account; never reveal account existence.
                stored=row['password_hash'] if row else f'pbkdf2_sha256${ROUNDS}$'+('00'*16)+'$'+('00'*32)
                valid=password_matches(password,stored)
                if not valid or not row or not row['active']:
                    db.execute('INSERT INTO auth_attempts VALUES(?,?,?)',(peer,username,now));failure=AuthFailure(401,'账号或密码不正确')
                else:
                    token=secrets.token_urlsafe(32);expires=now+SESSION_SECONDS
                    db.execute('DELETE FROM auth_sessions WHERE expires_at<=?',(now,))
                    db.execute('INSERT INTO auth_sessions VALUES(?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),row['id'],expires))
                    db.execute('DELETE FROM auth_attempts WHERE username=?',(username,))
                    result={'access_token':token,'token_type':'bearer','expires_at':expires,'user':Identity(row['id'],row['username'],row['role']).public()}
        if failure:raise failure
        return result

    def authenticate(self,token):
        if not token or not re.fullmatch(r'[A-Za-z0-9_-]{43}',token):raise AuthFailure(401,'请先登录')
        digest=hashlib.sha256(token.encode()).hexdigest()
        with self.connection() as db:
            row=db.execute('SELECT u.* FROM auth_sessions s JOIN auth_users u ON u.id=s.user_id WHERE s.token_hash=? AND s.expires_at>? AND u.active=1',(digest,time.time())).fetchone()
        if not row:raise AuthFailure(401,'登录已失效，请重新登录')
        return Identity(row['id'],row['username'],row['role'],digest)

    def logout(self,identity):
        with self.connection() as db:db.execute('DELETE FROM auth_sessions WHERE token_hash=?',(identity.session_hash,))

    def list_users(self):
        with self.connection() as db:return [dict(row) for row in db.execute('SELECT id,username,role,active FROM auth_users ORDER BY created_at')]
