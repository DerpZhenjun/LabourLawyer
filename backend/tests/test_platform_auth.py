import sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
import httpx
from fastapi import FastAPI

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import platform_api
from auth_store import AuthStore,AuthFailure
from routes.auth import router as auth_router
import sqlite3,time,os
from contextlib import closing


class PlatformAuthenticationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        folder=Path(self.temp.name)
        self.env=patch.dict(os.environ,{'LABOURLAWYER_AUTH_DB':str(folder/'auth.sqlite')});self.env.start();self.addCleanup(self.env.stop)
        for key,value in [('DATA_DIR',folder),('DB_PATH',folder/'cases.sqlite')]:
            p=patch.object(platform_api,key,value);p.start();self.addCleanup(p.stop)
        platform_api.init_database();self.store=AuthStore()
        self.a=self.store.create_user('tester-a','fictional-password-a','admin');self.b=self.store.create_user('tester-b','fictional-password-b')
        app=FastAPI();app.include_router(auth_router);app.include_router(platform_api.router)
        self.client=httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test');self.addAsyncCleanup(self.client.aclose)
        self.ha={'Authorization':'Bearer '+self.store.login('tester-a','fictional-password-a','test')['access_token']}
        self.hb={'Authorization':'Bearer '+self.store.login('tester-b','fictional-password-b','test')['access_token']}

    async def make_case(self,headers):
        r=await self.client.post('/api/platform/cases',headers=headers,json={'title':'虚构测试案件','client_name':'测试人','employer_name':'虚构单位','region':'测试地区','dispute_amount':123})
        self.assertEqual(r.status_code,201,r.text);return r.json()['id']

    async def test_case_data_requires_authentication(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(platform_api,'DATA_DIR',Path(folder)), patch.object(platform_api,'DB_PATH',Path(folder)/'cases.sqlite'):
            platform_api.init_database()
            app=FastAPI();app.include_router(platform_api.router)
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
                self.assertEqual((await client.get('/api/platform/cases')).status_code,401)

    async def test_case_summary_deadline_and_mutation_isolation(self):
        case=await self.make_case(self.ha)
        for path in [f'/api/platform/cases/{case}',f'/api/platform/cases/{case}/deadlines']:
            self.assertEqual((await self.client.get(path,headers=self.hb)).status_code,404)
        self.assertEqual((await self.client.patch(f'/api/platform/cases/{case}',headers=self.hb,json={'stage':'已结案'})).status_code,404)
        payload={'title':'虚构日程','due_at':'2026-10-31T10:00:00Z','kind':'材料任务'}
        self.assertEqual((await self.client.post(f'/api/platform/cases/{case}/deadlines',headers=self.hb,json=payload)).status_code,404)
        self.assertEqual((await self.client.post(f'/api/platform/cases/{case}/deadlines',headers=self.ha,json=payload)).status_code,201)
        self.assertEqual((await self.client.get('/api/platform/cases',headers=self.hb)).json()['items'],[])
        self.assertEqual((await self.client.get('/api/platform/summary',headers=self.hb)).json()['active_dispute_amount'],0)
        self.assertEqual((await self.client.get('/api/platform/summary',headers=self.ha)).json()['active_dispute_amount'],123)

    async def test_no_default_admin_or_role_escalation(self):
        r=await self.client.post('/api/auth/users',headers=self.hb,json={'username':'hacker','password':'fictional-password-z','role':'admin'})
        self.assertEqual(r.status_code,403)
        self.assertEqual((await self.client.post('/api/auth/users',headers=self.ha,json={'username':'new-user','password':'fictional-password-z'})).status_code,201)
        self.assertEqual((await self.client.post('/api/auth/login',json={'username':'admin','password':'admin'})).status_code,401)
        self.assertEqual((await self.client.post('/api/auth/login',json={'username':'tester-a','password':'fictional-password-a','role':'admin'})).status_code,422)

    async def test_hashed_tokens_logout_expiry_and_disabled_account(self):
        token=self.ha['Authorization'].split()[1]
        with self.store.connection() as db:
            rows=[dict(r) for r in db.execute('SELECT * FROM auth_sessions')]
            self.assertNotIn(token,str(rows));self.assertNotIn('fictional-password',str([dict(r) for r in db.execute('SELECT * FROM auth_users')]))
        self.assertEqual((await self.client.post('/api/auth/logout',headers=self.ha)).status_code,204)
        self.assertEqual((await self.client.get('/api/auth/me',headers=self.ha)).status_code,401)
        with self.store.connection() as db:db.execute('UPDATE auth_sessions SET expires_at=0')
        self.assertEqual((await self.client.get('/api/auth/me',headers=self.hb)).status_code,401)
        self.hb={'Authorization':'Bearer '+self.store.login('tester-b','fictional-password-b','test')['access_token']}
        with self.store.connection() as db:db.execute('UPDATE auth_users SET active=0 WHERE id=?',(self.b.id,))
        self.assertEqual((await self.client.get('/api/auth/me',headers=self.hb)).status_code,401)

    async def test_login_rate_limit_is_durable_and_generic(self):
        for _ in range(6):self.assertEqual((await self.client.post('/api/auth/login',json={'username':'absent','password':'bad'})).status_code,401)
        r=await self.client.post('/api/auth/login',json={'username':'absent','password':'bad'})
        self.assertEqual(r.status_code,429);self.assertEqual(r.headers['Retry-After'],'900')
        # A recreated store still enforces the attempt window.
        with self.assertRaises(AuthFailure) as context:AuthStore().login('absent','bad','other-peer')
        self.assertEqual(context.exception.status,429)

    async def test_legacy_case_is_backed_up_preserved_and_not_auto_claimed(self):
        path=Path(self.temp.name)/'legacy.sqlite'
        with closing(sqlite3.connect(path)) as db:
            db.execute('CREATE TABLE cases(id TEXT PRIMARY KEY,title TEXT,client_name TEXT,employer_name TEXT,region TEXT,stage TEXT,dispute_amount REAL,deadline TEXT,summary TEXT,evidence_count INTEGER,created_at TEXT,updated_at TEXT)')
            db.execute("INSERT INTO cases VALUES('old','历史','原客户','原单位','原地区','材料准备',9,NULL,'保留',0,'old','old')");db.commit()
        with patch.object(platform_api,'DB_PATH',path):
            platform_api.init_database();platform_api.init_database()
            with platform_api.connection() as db:
                row=dict(db.execute('SELECT * FROM cases').fetchone());self.assertEqual(row['summary'],'保留');self.assertIsNone(row['owner_user_id'])
            self.assertEqual((await self.client.get('/api/platform/cases',headers=self.ha)).json()['items'],[])
            backups=list(path.parent.glob('legacy.sqlite.pre-ownership-*.sqlite3'));self.assertEqual(len(backups),1)
            with closing(sqlite3.connect(backups[0])) as db:self.assertEqual(db.execute('SELECT summary FROM cases').fetchone()[0],'保留')

    async def test_case_owner_cannot_be_supplied_or_changed_by_client(self):
        case=await self.make_case(self.hb)
        await self.client.patch(f'/api/platform/cases/{case}',headers=self.hb,json={'owner_user_id':self.a.id})
        self.assertEqual((await self.client.get(f'/api/platform/cases/{case}',headers=self.ha)).status_code,404)
        self.assertEqual((await self.client.get(f'/api/platform/cases/{case}',headers=self.hb)).status_code,200)


if __name__=='__main__':unittest.main()
