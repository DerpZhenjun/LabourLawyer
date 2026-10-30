import {computed,reactive,ref} from 'vue'
import {readJSON} from '../api/http.ts'
import {authSession} from '../api/authSession.ts'
import type {NewCaseInput,WorkspaceCase,WorkspaceMutationResult,WorkspaceSnapshot} from '../../../packages/regional-contracts/src/workspace.ts'

export function createServerWorkspace(){
 const state=reactive<WorkspaceSnapshot>({cases:[],recentDocuments:[]}),storageIssue=ref(''),busy=ref(false)
 let revision=0
 function reset(){revision++;state.cases=[];state.recentDocuments=[];storageIssue.value='';busy.value=false}
 async function refresh(){
  const session=authSession.get();if(!session){reset();return}
  const rev=++revision;busy.value=true
  try{
   const raw=await readJSON('/api/platform/cases')
   if(rev!==revision||authSession.get()?.access_token!==session.access_token)return
   if(!raw||typeof raw!=='object'||!('items' in raw)||!Array.isArray(raw.items))throw Error('案件资料格式不正确')
   const cases:WorkspaceCase[]=raw.items.map((v:unknown)=>{
    if(!v||typeof v!=='object')throw Error('案件资料格式不正确')
    const r=v as Record<string,unknown>
    for(const name of ['id','title','client_name','employer_name','region','stage','updated_at'])if(typeof r[name]!=='string')throw Error('案件资料格式不正确')
    if(typeof r.dispute_amount!=='number'||!Number.isFinite(r.dispute_amount)||r.dispute_amount<0)throw Error('案件金额格式不正确')
    return {id:String(r.id),title:String(r.title),client:String(r.client_name),employer:String(r.employer_name),region:String(r.region),stage:String(r.stage),amount:r.dispute_amount,deadline:typeof r.deadline==='string'?r.deadline:'未设置',evidence:typeof r.evidence_count==='number'?r.evidence_count:0,evidenceReady:0,risk:r.stage==='已结案'?'done':'progress',updatedAt:String(r.updated_at)}
   })
   state.cases=cases;storageIssue.value=cases.length?'':'当前账号还没有案件。旧浏览器资料和未归属的历史案件均已保留，不会自动导入。'
  }catch(e){if(rev===revision)storageIssue.value=e instanceof Error?e.message:'暂时无法读取案件'}finally{if(rev===revision)busy.value=false}
 }
 async function addCase(input:NewCaseInput):Promise<WorkspaceMutationResult>{
  const token=authSession.get()?.access_token;if(!token)return{ok:false,error:'请先登录'}
  try{
   await readJSON('/api/platform/cases',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({title:input.title,client_name:input.client,employer_name:input.employer,region:input.region,dispute_amount:Number(input.amount||0),deadline:input.deadline||null})})
   if(authSession.get()?.access_token!==token)return{ok:false,error:'登录状态已变化，请重新查看当前账号案件'}
   await refresh();return{ok:true,persisted:true}
  }catch(e){return{ok:false,error:e instanceof Error?e.message:'暂时无法保存案件'}}
 }
 // Never carry a previous account's state across login/logout or expired sessions.
 authSession.subscribe(()=>{reset();if(authSession.get())void refresh()})
 if(authSession.get())void refresh()
 return{state,storageIssue,busy,refresh,addCase,activeCases:computed(()=>state.cases.filter(v=>v.stage!=='已结案')),totalAmount:computed(()=>state.cases.filter(v=>v.stage!=='已结案').reduce((n,v)=>n+v.amount,0))}
}
