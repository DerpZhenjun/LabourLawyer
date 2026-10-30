import {onBeforeUnmount,onMounted,ref} from 'vue'
import {sha256} from '@noble/hashes/sha2.js'
import {bytesToHex} from '@noble/hashes/utils.js'
import {APIError,apiURL,authorizationHeaders,readJSON} from '@/api/http'
import {authSession} from '@/api/authSession'
import {downloadDocument} from './downloadDocument'
import {collectorEvidencePath,parseCollectorStatus} from '../../../packages/client-contracts/src/collector.ts'
import type {CollectorStatus,CollectorRegion,CollectorJob,CollectorEvidence} from '../../../packages/client-contracts/src/collector.ts'

export function useOfficialCollector(){
 const data=ref<CollectorStatus|null>(null),loading=ref(false),busy=ref(false),error=ref(''),message=ref('')
 let disposed=false,revision=0,poll:ReturnType<typeof setTimeout>|undefined,loadController:AbortController|undefined
 const requests=new Set<AbortController>()
 const identity=()=>authSession.get()?.access_token
 const text=(e:unknown)=>e instanceof Error?e.message:'暂时无法连接采集服务，请稍后重试。'
 function schedule(){clearTimeout(poll);if(!disposed)poll=setTimeout(()=>void refresh(),data.value&&(data.value.counts.queued+data.value.counts.running)>0?5000:30000)}
 async function refresh(){
  if(disposed)return
  const request=++revision,token=identity();loadController?.abort();const controller=new AbortController();loadController=controller;loading.value=true
  try{
   const raw=await readJSON('/api/official-collector',{signal:controller.signal})
   if(disposed||request!==revision||identity()!==token)return
   data.value=parseCollectorStatus(raw);error.value=''
  }catch(e){if(!disposed&&request===revision&&!controller.signal.aborted){if(e instanceof APIError&&[401,403].includes(e.status))data.value=null;error.value=text(e)}}
  finally{if(!disposed&&request===revision){loading.value=false;schedule()}}
 }
 async function mutate(path:string,body?:unknown){
  if(busy.value||disposed)return
  busy.value=true;message.value='';error.value='';const token=identity(),controller=new AbortController();requests.add(controller)
  try{
   await readJSON(path,{method:'POST',signal:controller.signal,...(body===undefined?{}:{headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})})
   if(disposed||identity()!==token)return
   message.value='操作已保存。页面访问完成后仍须核对地区、材料和模板，才可接入填写。';await refresh()
  }catch(e){if(!disposed&&identity()===token&&!controller.signal.aborted)error.value=text(e)}
  finally{requests.delete(controller);if(!disposed)busy.value=false}
 }
 const submit=(url:string,region:CollectorRegion)=>data.value?mutate('/api/official-collector/jobs',{items:[{url,region}]}):Promise.resolve()
 const action=(job:CollectorJob,operation:'retry'|'cancel')=>mutate(`/api/official-collector/jobs/${job.id}/${operation}`)
 async function download(job:CollectorJob,item:CollectorEvidence){
  if(busy.value||disposed)return
  const token=identity(),controller=new AbortController();requests.add(controller);busy.value=true;error.value=''
  try{
   const response=await fetch(apiURL(collectorEvidencePath(job.id,item.file,job.attempt)),{headers:authorizationHeaders(),signal:controller.signal,cache:'no-store'})
   if(!response.ok)throw Error('采集证据暂时无法下载，请刷新后重试。')
   const blob=await response.blob();if(blob.size!==item.bytes||blob.size>50*1024*1024)throw Error('采集证据大小与记录不匹配，已停止下载。')
   // Trusted-LAN preview pages do not expose WebCrypto's secure-context API.
   const hash=bytesToHex(sha256(new Uint8Array(await blob.arrayBuffer())))
   if(hash!==item.sha256)throw Error('采集证据校验不一致，已停止下载。')
   if(!disposed&&identity()===token)await downloadDocument(blob,`采集-${job.region.region_code}-${job.id.slice(0,8)}-${item.file}`)
  }catch(e){if(!disposed&&identity()===token&&!controller.signal.aborted)error.value=text(e)}
  finally{requests.delete(controller);if(!disposed)busy.value=false}
 }
 onMounted(refresh)
 onBeforeUnmount(()=>{disposed=true;revision++;clearTimeout(poll);loadController?.abort();for(const c of requests)c.abort();data.value=null})
 return{data,loading,busy,error,message,refresh,submit,action,download}
}
