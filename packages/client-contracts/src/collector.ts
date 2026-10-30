/** Observations awaiting review, never a claim that a guide or template is verified. */
export interface CollectorRegion {province:string;city:string;district:string;region_code:string}
export type CollectorJobState='queued'|'running'|'complete'|'cancelled'
export type ObservationState='guide_observed'|'blocked'|'auth_required'|'captcha_required'|'network_failed'|'runtime_failed'|'unverified'|'http_failed'|'blank'|'interrupted'
export interface CollectorEvidence {file:string;bytes:number;sha256:string}
export interface CollectorJob {id:string;url:string;region:CollectorRegion;state:CollectorJobState;attempt:number;created_at:string;updated_at:string;result?:{state:ObservationState;title:string;evidence:CollectorEvidence[];review_required:true;service_verified:false}}
export interface CollectorStatus {counts:Record<CollectorJobState,number>;items:CollectorJob[];worker:{state:string;alive:boolean;updated_at:string}|null;capacity:number;concurrency:1;allowed_hosts:string[]}
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
 return{counts:parsedCounts,items,worker,capacity:number(raw.capacity,1000),concurrency:1,allowed_hosts}
}
