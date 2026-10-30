import assert from 'node:assert/strict'
import {createRequire} from 'node:module'
import {readFileSync} from 'node:fs'
import vm from 'node:vm'
import {createAuthSession} from '../frontend/src/api/authSession.ts'
const require=createRequire(new URL('../frontend/package.json',import.meta.url)),ts=require('typescript')
const source=readFileSync(new URL('../frontend/src/api/auth.ts',import.meta.url),'utf8')
const code=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText
const authSession=createAuthSession();const a={access_token:'a'.repeat(43),token_type:'bearer',expires_at:Date.now()/1000+1000,user:{id:'a',username:'alice',role:'admin'}}
let request=async()=>{throw Error('Network unavailable')}
class APIError extends Error{constructor(status){super('synthetic');this.status=status}}
const context={exports:{},require:ref=>ref==='vue'?{shallowRef:value=>({value})}:ref.includes('authSession')?{authSession}:{readJSON:(...args)=>request(...args),APIError}}
vm.runInNewContext(code,context)
authSession.set(a)
await assert.rejects(context.exports.logout(),/Network unavailable/)
assert.equal(authSession.get(),null,'Offline logout must remove private local session even if revocation is unconfirmed')
let complete;request=()=>new Promise(resolve=>{complete=resolve});authSession.set(a);const old=context.exports.logout();authSession.set({...a,access_token:'b'.repeat(43),user:{...a.user,id:'b'}});complete(null);await old
assert.equal(authSession.get().user.id,'b','Late logout cannot clear a newly logged-in account');authSession.clear()
const pending=[];request=()=>new Promise(resolve=>pending.push(resolve))
const older=context.exports.login('alice','synthetic'),newer=context.exports.login('bob','synthetic')
const b={...a,access_token:'b'.repeat(43),user:{...a.user,id:'b'}}
pending[1](b);await newer;pending[0](a);await older
assert.equal(authSession.get().user.id,'b','Late login cannot replace a newer identity');authSession.clear()
const cancelled=context.exports.login('alice','synthetic');await context.exports.logout();pending[2](a);await cancelled
assert.equal(authSession.get(),null,'Logout invalidates an in-flight login even without a current token')
assert.equal(context.exports.safeAdminPath('//untrusted.invalid'),'/admin');assert.equal(context.exports.safeAdminPath('/admin/cases'),'/admin/cases')
console.log('PASS actual auth logout offline purge, late response identity guard and safe local return path; synthetic transport only')
