/** Portable application API contracts. No network, storage or model side effects. */
export interface ChatMessage { role:'user'|'ai'; content:string }
import type {components} from './generated/stable-api'
import {API_LIMITS} from './generated/api-limits.ts'
export {API_LIMITS}
export type AskMessage=components['schemas']['ChatMessage']
export type AskRequest=Omit<components['schemas']['QuestionRequest'],'history'>&{history:AskMessage[]}
type StatusWire=components['schemas']['AIStatusResponse']
export type AIStatus=Pick<StatusWire,'ready'|'provider'|'model'|'local_model_started'>&{message?:NonNullable<StatusWire['message']>;status?:NonNullable<StatusWire['status']>}
const record=(v:unknown):v is Record<string,unknown>=>v!==null&&typeof v==='object'&&!Array.isArray(v)
const length=(s:string)=>Array.from(s).length
/** Explicit user-selected server. HTTP is limited to local/private preview networks. */
export function normalizeServiceAddress(input:string):string {
  if(typeof input!=='string')throw new Error('请填写服务地址。')
  const value=input.trim(),match=/^(https?):\/\/(\[::1\]|[a-z0-9.-]+)(?::([0-9]{1,5}))?\/?$/i.exec(value)
  if(!match)throw new Error('地址应为HTTPS域名或局域网地址，不能包含账号、路径或查询参数。')
  const scheme=match[1]!.toLowerCase(),host=match[2]!.toLowerCase(),port=match[3]
  if(port&&(!/^[1-9][0-9]*$/.test(port)||Number(port)>65535))throw new Error('端口号无效。')
  let privateHost=host==='localhost'||host==='[::1]'
  if(/^[0-9.]+$/.test(host)){
    const parts=host.split('.')
    if(parts.length!==4||parts.some(p=>! /^(0|[1-9][0-9]{0,2})$/.test(p)||Number(p)>255))throw new Error('IP地址无效。')
    const [a,b]=parts.map(Number)
    privateHost=a===127||a===10||a===192&&b===168||a===172&&b!==undefined&&b>=16&&b<=31
  }else if(host!=='[::1]'&&(host.length>253||host.split('.').some(p=>! /^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/.test(p))))throw new Error('域名格式无效。')
  if(scheme==='http'&&!privateHost)throw new Error('公网服务必须使用HTTPS；HTTP仅用于本机或局域网预览。')
  return `${scheme}://${host}${port?':'+port:''}`
}
export function apiURL(base:string,path:string):string {
  if(!path.startsWith('/')||path.startsWith('//')||path.includes('..')||path.includes('\\')||/[\r\n]/.test(path))throw new Error('接口路径无效。')
  // WeChat's script runtime does not provide the browser URL constructor.
  if(!/^https?:\/\/[^/?#\s@\\]+(?:\/[^?#\s\\]*)?$/.test(base))throw new Error('服务地址无效。')
  return base.replace(/\/$/,'')+path
}
export function assertAIStatus(raw:unknown):AIStatus {
  if(!record(raw)||typeof raw.ready!=='boolean'||typeof raw.provider!=='string'||typeof raw.model!=='string'||typeof raw.local_model_started!=='boolean')throw new Error('助手状态格式不正确，请重试。')
  return {ready:raw.ready,provider:raw.provider,model:raw.model,local_model_started:raw.local_model_started,...(typeof raw.message==='string'?{message:raw.message}:{}),...(typeof raw.status==='string'?{status:raw.status}:{})}
}
export const remoteReady=(s:AIStatus):boolean=>s.ready&&s.provider==='Ubuntu Ollama'&&s.model==='qwen3.8:27b'&&!s.local_model_started
export function buildAskRequest(question:string,raw:unknown):AskRequest {
  const text=question.trim()
  if(!text||length(text)>API_LIMITS.questionMax)throw new Error(`请填写不超过${API_LIMITS.questionMax}字符的问题。`)
  if(!Array.isArray(raw))throw new Error('对话记录格式不正确。')
  const history:AskMessage[]=[]
  for(const item of raw){
    if(!record(item)||!['ai','assistant','user'].includes(String(item.role))||typeof item.content!=='string')throw new Error('对话记录格式不正确。')
    if(!item.content)continue
    if(length(item.content)>API_LIMITS.messageMax)throw new Error(`单条对话超过${API_LIMITS.messageMax}字符，请清空对话后重试。`)
    history.push({role:item.role==='user'?'user':'assistant',content:item.content})
  }
  return {question:text,history:history.slice(-API_LIMITS.historyMax)}
}
export function parseStoredChat(text:string|null):ChatMessage[]|null {
  if(!text)return null
  try{const raw:unknown=JSON.parse(text);if(!Array.isArray(raw)||!raw.length)return null
    const result:ChatMessage[]=[]
    for(const item of raw){if(!record(item)||!['ai','user'].includes(String(item.role))||typeof item.content!=='string')return null;result.push({role:item.role==='user'?'user':'ai',content:item.content})}
    return result
  }catch{return null}
}
export function createAnswerDecoder(){const decoder=new TextDecoder();return{push:(value:Uint8Array)=>decoder.decode(value,{stream:true}),finish:()=>decoder.decode()}}
