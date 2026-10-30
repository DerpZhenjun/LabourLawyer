/** Local workspace and existing administrative response boundaries. No service access. */
export interface WorkspaceCase {
  id:string;title:string;client:string;employer:string;region:string;amount:number
  stage:string;risk:string;deadline:string;evidence:number;evidenceReady:number;updatedAt:string
  [key:string]:unknown
}
export interface WorkspaceSnapshot {cases:WorkspaceCase[];recentDocuments:unknown[];[key:string]:unknown}
export interface NewCaseInput {title?:string;client?:string;employer?:string;region?:string;amount?:string|number;deadline?:string}
export interface WorkspaceStorage {getItem(key:string):string|null;setItem(key:string,value:string):void}
export type WorkspaceMutationResult={ok:true;persisted:boolean}|{ok:false;error:string}
const record=(value:unknown):value is Record<string,unknown>=>value!==null && typeof value==='object' && !Array.isArray(value) && [Object.prototype,null].includes(Object.getPrototypeOf(value))
const finite=(value:unknown):value is number=>typeof value==='number' && Number.isFinite(value)
const caseStrings=['id','title','client','employer','region','stage','risk','deadline','updatedAt'] as const
function caseValue(value:unknown):WorkspaceCase|null {
  if(!record(value) || caseStrings.some(key=>typeof value[key]!=='string') || !finite(value.amount) || value.amount<0 ||
     !finite(value.evidence) || !Number.isInteger(value.evidence) || value.evidence<0 ||
     !finite(value.evidenceReady) || value.evidenceReady<0 || value.evidenceReady>100)return null
  return {...value,id:String(value.id),title:String(value.title),client:String(value.client),employer:String(value.employer),
    region:String(value.region),amount:value.amount,stage:String(value.stage),risk:String(value.risk),deadline:String(value.deadline),
    evidence:value.evidence,evidenceReady:value.evidenceReady,updatedAt:String(value.updatedAt)}
}
export function parseWorkspaceSnapshot(value:unknown):WorkspaceSnapshot|null {
  if(!record(value) || (value.cases!==undefined && !Array.isArray(value.cases)) ||
     (value.recentDocuments!==undefined && !Array.isArray(value.recentDocuments)))return null
  const cases:WorkspaceCase[]=[]
  for(const row of value.cases??[]){const item=caseValue(row);if(!item)return null;cases.push(item)}
  return {...value,cases,recentDocuments:value.recentDocuments??[]}
}
const invalid=():never=>{throw new Error('返回的工作区资料格式不正确，请稍后重试。')}
const asRecord=(value:unknown):Record<string,unknown>=>record(value)?value:invalid()
const text=(row:Record<string,unknown>,key:string):string=>row[key]===undefined || row[key]===null?'':typeof row[key]==='string'?row[key]:invalid()
const count=(row:Record<string,unknown>,key:string):number=>row[key]===undefined || row[key]===null?0:finite(row[key]) && row[key]>=0?row[key]:invalid()
const flag=(row:Record<string,unknown>,key:string):boolean=>row[key]===undefined || row[key]===null?false:typeof row[key]==='boolean'?row[key]:invalid()
const id=(row:Record<string,unknown>):string=>typeof row.id==='string' && row.id.length>0?row.id:invalid()
const list=(value:unknown,key:string):unknown[]=>{const row=asRecord(value);return row[key]===undefined?[]:Array.isArray(row[key])?row[key]:invalid()}
export interface PortalReport {
  id:string;state:string;phase:string;completed:number;total:number;recommended:boolean;scope_label:string
  regions_saved:number;searches_saved:number;current:string;ai_report:string|boolean|null;ai_completed:number;ai_state:string;report_ready:boolean;error:string
}
export function parsePortalReports(value:unknown):PortalReport[] {
  return list(value,'items').map(value=>{
    const row=asRecord(value),ai=row.ai_report
    if(ai!==undefined && ai!==null && typeof ai!=='boolean' && typeof ai!=='string')return invalid()
    return {id:id(row),state:text(row,'state'),phase:text(row,'phase'),completed:count(row,'completed'),total:count(row,'total'),
      recommended:flag(row,'recommended'),scope_label:text(row,'scope_label'),regions_saved:count(row,'regions_saved'),
      searches_saved:count(row,'searches_saved'),current:text(row,'current'),ai_report:ai??null,ai_completed:count(row,'ai_completed'),
      ai_state:text(row,'ai_state'),report_ready:flag(row,'report_ready'),error:text(row,'error')}
  })
}
export interface AgentResult {status:Record<string,boolean>;screenshot:string;error:string}
export interface AgentTask {id:string;state:string;completed:number;total:number;current:string;current_task:AgentResult|null;provinces:Record<string,AgentResult>;error:string}
function agentResult(value:unknown):AgentResult {
  const row=asRecord(value),flags=row.status===undefined || row.status===null?{}:asRecord(row.status),status:Record<string,boolean>={}
  for(const [key,value] of Object.entries(flags)){if(typeof value!=='boolean')return invalid();Object.defineProperty(status,key,{value,enumerable:true,writable:true,configurable:true})}
  return{status,screenshot:text(row,'screenshot'),error:text(row,'error')}
}
export function parseAgentTasks(value:unknown):AgentTask[] {
  return list(value,'items').map(value=>{
    const row=asRecord(value),raw=row.provinces===undefined || row.provinces===null?{}:asRecord(row.provinces),provinces:Record<string,AgentResult>={}
    for(const [key,value] of Object.entries(raw))Object.defineProperty(provinces,key,{value:agentResult(value),enumerable:true,writable:true,configurable:true})
    return{id:id(row),state:text(row,'state'),completed:count(row,'completed'),total:count(row,'total'),current:text(row,'current'),
      current_task:row.current_task===undefined || row.current_task===null?null:agentResult(row.current_task),provinces,error:text(row,'error')}
  })
}
export interface WorkflowGuide {id:string;guide_url:string;region_name:string;authority:string;service_name:string;captured_at:string;steps:unknown[];plain_steps:{title:string;text:string}[];plain_materials:string[]}
export function parseDistrictGuides(value:unknown):WorkflowGuide[] {
  const result:WorkflowGuide[]=[]
  for(const raw of list(value,'guides')){
    const row=asRecord(raw),url=text(row,'guide_url')
    try{if(!['http:','https:'].includes(new URL(url).protocol))continue}catch{continue}
    const steps=list(row,'plain_steps').map(value=>{const step=asRecord(value);return{title:text(step,'title'),text:text(step,'text')}})
    const materials=list(row,'plain_materials').map(value=>typeof value==='string'?value:invalid())
    result.push({id:id(row),guide_url:url,region_name:text(row,'region_name'),authority:text(row,'authority'),service_name:text(row,'service_name'),
      captured_at:text(row,'captured_at'),steps:list(row,'steps'),plain_steps:steps,plain_materials:materials})
  }
  return result
}
export function workspaceError(value:unknown,fallback:string):string {
  if(record(value) && record(value.response) && record(value.response.data) && typeof value.response.data.detail==='string')return value.response.data.detail
  return fallback
}
export function responseIdentifier(value:unknown):string{return id(asRecord(value))}
