import assert from 'node:assert/strict'
import {createRequire} from 'node:module'
import {readFileSync} from 'node:fs'
import vm from 'node:vm'
const require=createRequire(new URL('../frontend/package.json',import.meta.url)),ts=require('typescript')
const source=readFileSync(new URL('../frontend/src/api/authSession.ts',import.meta.url),'utf8')
const output=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText
const timers=new Map();let nextTimer=0,now=Date.now()
class Clock extends Date{static now(){return now}}
const context={exports:{},require:()=>({savedConnection:()=>null}),Date:Clock,Set,console,globalThis:{},setTimeout:(fn,delay)=>{const id=++nextTimer;timers.set(id,{fn,delay});return id},clearTimeout:id=>timers.delete(id)};vm.runInNewContext(output,context)
const create=context.exports.createAuthSession
const good={access_token:'a'.repeat(43),token_type:'bearer',expires_at:Date.now()/1000+1000,user:{id:'a',username:'alice',role:'admin'}}
let raw='{broken',writes=0
const storage={getItem:()=>raw,setItem:(k,v)=>{raw=v;writes++},removeItem:()=>{raw=null}}
const s=create(storage);assert.equal(s.get(),null);assert.equal(writes,0);assert.equal(raw,'{broken')
for(const change of [{user:{...good.user,role:'root'}},{access_token:'short'},{expires_at:0}])assert.throws(()=>s.set({...good,...change}))
s.set(good);assert.equal(s.get().user.id,'a');assert.equal(writes,1)
const reload=create(storage);assert.equal(reload.get().access_token,good.access_token)
s.clear();assert.equal(s.get(),null);assert.equal(raw,null)
const unavailable=create({getItem(){throw Error('denied')},setItem(){throw Error('denied')},removeItem(){throw Error('denied')}})
unavailable.set(good);assert.equal(unavailable.get().user.username,'alice');unavailable.clear();assert.equal(unavailable.get(),null)
const idle=create();idle.set(good);let notified=0;idle.subscribe(()=>notified++);const due=[...timers.values()].at(-1);assert(due.delay>0);now=(good.expires_at+1)*1000;due.fn();assert.equal(notified,1,'Expiry must notify even without a request or navigation');assert.equal(idle.get(),null)
const scoped=new Map(),bound={getItem:k=>scoped.get(k)||null,setItem:(k,v)=>scoped.set(k,v),removeItem(){throw Error('denied removal')}};const a=create(bound,'server-a');a.set({...good,expires_at:now/1000+1000});a.clear();const b=create(bound,'server-b');assert.equal(b.get(),null,'A failed token removal must not send old server credentials to a changed server')
assert(!source.includes('localStorage'))
console.log('PASS auth session validation, corrupt-storage retention, explicit logout and storage-denied memory fallback; no network')
