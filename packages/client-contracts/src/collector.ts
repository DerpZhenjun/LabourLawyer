/** Observations awaiting review, never a claim that a guide or template is verified. */
export interface CollectorRegion {province:string;city:string;district:string;region_code:string}
export type CollectorJobState='queued'|'running'|'complete'|'cancelled'
export type ObservationState='guide_observed'|'blocked'|'auth_required'|'captcha_required'|'network_failed'|'runtime_failed'|'unverified'|'http_failed'|'blank'|'interrupted'
export interface CollectorEvidence {file:string;bytes:number;sha256:string}
export interface CollectorJob {id:string;url:string;region:CollectorRegion;state:CollectorJobState;attempt:number;created_at:string;updated_at:string;result?:{state:ObservationState;title:string;evidence:CollectorEvidence[];review_required:true;service_verified:false}}
export type CollectorIssueJournalState='pending'|'disabled'|'outbox_persisted'|'rejected'|'error'
export interface CollectorIssueEvents {
 enabled:boolean
 journal:{status:'available'|'error';observations:number|null;states:Partial<Record<CollectorIssueJournalState,number>>|null}
 outbox:{status:'disabled'|'missing'|'available'|'error';events:number|null;pending:number|null;acknowledged:number|null}
 model_calls:0
 ai_reviewed:false
}
export interface CollectorStatus {counts:Record<CollectorJobState,number>;items:CollectorJob[];worker:{state:string;alive:boolean;updated_at:string}|null;capacity:number;concurrency:1;allowed_hosts:string[];issue_events?:CollectorIssueEvents}
const jobStates=['queued','running','complete','cancelled'] as const
const observations=['guide_observed','blocked','auth_required','captcha_required','network_failed','runtime_failed','unverified','http_failed','blank','interrupted'] as const
const record=(value:unknown):Record<string,unknown>=>{if(!value||typeof value!=='object'||Array.isArray(value))throw Error('采集服务返回的资料格式不正确。');return value as Record<string,unknown>}
const text=(value:unknown,max=3000):string=>{if(typeof value!=='string'||value.length>max||/[\x00-\x08\x0b\x0c\x0e-\x1f]/.test(value))throw Error('采集资料文字格式不正确。');return value}
const number=(value:unknown,max=Number.MAX_SAFE_INTEGER):number=>{if(typeof value!=='number'||!Number.isSafeInteger(value)||value<0||value>max)throw Error('采集服务返回的数量不正确。');return value}
const officialURL=(value:unknown):string=>{
 const raw=text(value),u=new URL(raw)
 if(!['https:','http:'].includes(u.protocol)||!u.hostname.endsWith('.gov.cn')||u.username||u.password||!['','80','443'].includes(u.port))throw Error('采集记录中的官方地址不正确。')
 return raw
}
const evidenceName=(value:string)=>/^(?:(?:page|failure|materials)\.(?:png|txt)|attachment-\d+\.(?:docx?|pdf|xlsx?))$/.test(value)
const exact=(value:Record<string,unknown>,keys:string[])=>{if(Object.keys(value).length!==keys.length||keys.some(key=>!Object.hasOwn(value,key)))throw Error('采集问题状态包含未识别资料。')}
function parseIssueEvents(input:unknown):CollectorIssueEvents{
 const raw=record(input),journal=record(raw.journal),outbox=record(raw.outbox)
 exact(raw,['enabled','journal','outbox','model_calls','ai_reviewed']);exact(journal,['status','observations','states']);exact(outbox,['status','events','pending','acknowledged'])
 if(typeof raw.enabled!=='boolean'||raw.model_calls!==0||raw.ai_reviewed!==false)throw Error('问题送达不能冒充模型审核。')
 let parsedJournal:CollectorIssueEvents['journal']
 if(journal.status==='available'){
  const states=record(journal.states),known=['pending','disabled','outbox_persisted','rejected','error']
  if(Object.keys(states).some(key=>!known.includes(key)))throw Error('采集观察日志状态不正确。')
  const parsed=Object.fromEntries(Object.entries(states).map(([key,value])=>[key,number(value)])),observations=number(journal.observations)
  if(Object.values(parsed).reduce((sum,value)=>sum+value,0)!==observations)throw Error('采集观察日志数量不一致。')
  parsedJournal={status:'available',observations,states:parsed}
 }else{
  if(journal.status!=='error'||journal.observations!==null||journal.states!==null)throw Error('未读取日志不能视为零条观察。')
  parsedJournal={status:'error',observations:null,states:null}
 }
 let parsedOutbox:CollectorIssueEvents['outbox']
 if(outbox.status==='available'){
  const events=number(outbox.events),pending=number(outbox.pending),acknowledged=number(outbox.acknowledged)
  if(!raw.enabled||events!==pending+acknowledged)throw Error('独立问题库数量不一致。')
  parsedOutbox={status:'available',events,pending,acknowledged}
 }else{
  if(!['disabled','missing','error'].includes(String(outbox.status))||raw.enabled!==(outbox.status!=='disabled')||[outbox.events,outbox.pending,outbox.acknowledged].some(value=>value!==null))throw Error('未读取问题库不能视为成功零条。')
  parsedOutbox={status:outbox.status as 'disabled'|'missing'|'error',events:null,pending:null,acknowledged:null}
 }
 return{enabled:raw.enabled,journal:parsedJournal,outbox:parsedOutbox,model_calls:0,ai_reviewed:false}
}
export function collectorEvidencePath(id:string,file:string,attempt:number):string{
 if(!/^[a-f0-9]{32}$/.test(id)||!evidenceName(file)||!Number.isSafeInteger(attempt)||attempt<1||attempt>2)throw Error('采集证据地址不正确。')
 return `/api/official-collector/jobs/${id}/evidence/${file}?attempt=${attempt}`
}
export function parseCollectorStatus(input:unknown):CollectorStatus{
 const raw=record(input),counts=record(raw.counts)
 if(raw.concurrency!==1||raw.model_used!==false||raw.review_required!==true||!Array.isArray(raw.items)||raw.items.length>100||!Array.isArray(raw.allowed_hosts))throw Error('采集服务状态格式不正确。')
 const parsedCounts=Object.fromEntries(jobStates.map(key=>[key,number(counts[key]??0)])) as Record<CollectorJobState,number>
 const items=raw.items.map((value):CollectorJob=>{
  const v=record(value),r=record(v.region),id=text(v.id,32),state=text(v.state)
  if(!/^[a-f0-9]{32}$/.test(id)||!jobStates.includes(state as CollectorJobState))throw Error('采集任务状态不正确。')
  const region={province:text(r.province,80),city:text(r.city,80),district:text(r.district,80),region_code:text(r.region_code,12)}
  if(!region.province.trim()||!region.city.trim()||!region.district.trim()||!/^\d{6,12}$/.test(region.region_code))throw Error('采集任务缺少明确地区。')
  const job:CollectorJob={id,url:officialURL(v.url),region,state:state as CollectorJobState,attempt:number(v.attempt,2),created_at:text(v.created_at,80),updated_at:text(v.updated_at,80)}
  if(v.result!=null){
   const result=record(v.result),observed=text(result.state)
   if(result.service_verified!==false||result.model_used!==false||result.review_required!==true||!observations.includes(observed as ObservationState)||!Array.isArray(result.evidence)||result.evidence.length>20)throw Error('页面访问不能冒充官方核验。')
   const evidence=result.evidence.map(value=>{const e=record(value),file=text(e.file,80),sha256=text(e.sha256,64);if(!evidenceName(file)||!/^[a-f0-9]{64}$/.test(sha256))throw Error('采集证据校验信息不正确。');return{file,sha256,bytes:number(e.bytes)}})
   job.result={state:observed as ObservationState,title:result.title==null?'':text(result.title,1000),evidence,service_verified:false,review_required:true}
  }
  return job
 })
 let worker:CollectorStatus['worker']=null
 if(raw.worker!=null){const w=record(raw.worker);if(typeof w.alive!=='boolean')throw Error('执行器状态不正确。');worker={state:text(w.state,80),alive:w.alive,updated_at:text(w.updated_at,80)}}
 const allowed_hosts=raw.allowed_hosts.map(v=>{const h=text(v,253);if(!/^[a-z0-9.-]+\.gov\.cn$/.test(h))throw Error('采集站点范围不正确。');return h})
 return{counts:parsedCounts,items,worker,capacity:number(raw.capacity,1000),concurrency:1,allowed_hosts,...(raw.issue_events===undefined?{}:{issue_events:parseIssueEvents(raw.issue_events)})}
}
