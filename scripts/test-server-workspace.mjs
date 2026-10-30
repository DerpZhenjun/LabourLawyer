import assert from 'node:assert/strict'
import {authSession} from '../frontend/src/api/authSession.ts'
import {createServerWorkspace} from '../frontend/src/composables/serverWorkspace.ts'
const pending=[]
globalThis.fetch=async(url,options)=>new Promise(resolve=>pending.push({url,options,resolve}))
const pause=()=>new Promise(resolve=>setImmediate(resolve))
const session=(id)=>({access_token:id.repeat(43),token_type:'bearer',expires_at:Date.now()/1000+100,user:{id,username:'test-'+id,role:'admin'}})
const row=(id)=>({id,title:'fictional',client_name:'fictional',employer_name:'fictional',region:'fictional',stage:'材料准备',dispute_amount:1,updated_at:'today'})
const result=(items)=>new Response(JSON.stringify({items}),{headers:{'Content-Type':'application/json'}})
authSession.clear();const workspace=createServerWorkspace();assert.equal(workspace.state.cases.length,0)
authSession.set(session('a'));assert.equal(pending.length,1);assert.equal(pending[0].options.headers.get('Authorization'),'Bearer '+'a'.repeat(43))
authSession.set(session('b'));assert.equal(pending.length,2)
pending[0].resolve(result([row('old-a')]));await pause();assert.equal(workspace.state.cases.length,0,'Late account A must not populate account B')
pending[1].resolve(result([row('own-b')]));await pause();assert.equal(workspace.state.cases[0].id,'own-b')
authSession.clear();assert.equal(workspace.state.cases.length,0,'Logout immediately clears private data')
authSession.set(session('a'));pending[2].resolve(new Response(JSON.stringify({detail:'expired'}),{status:401}));await pause();assert.equal(authSession.get(),null);assert.equal(workspace.state.cases.length,0)
console.log('PASS actual server workspace Bearer requests, A/B late-response isolation, logout purge and 401 expiry; synthetic transport only')
