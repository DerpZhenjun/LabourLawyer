/** Portable application API contracts. No network, storage or model side effects. */
export interface ChatMessage { role:'user'|'ai'; content:string }
export interface AskMessage { role:'user'|'assistant'; content:string }
export interface AskRequest { question:string; history:AskMessage[] }
export interface AIStatus { ready:boolean; provider:string; model:string; local_model_started:boolean; message?:string; status?:string }
const record=(v:unknown):v is Record<string,unknown>=>v!==null&&typeof v==='object'&&!Array.isArray(v)
const length=(s:string)=>Array.from(s).length
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
  if(!text||length(text)>8000)throw new Error('请填写不超过8000字符的问题。')
  if(!Array.isArray(raw))throw new Error('对话记录格式不正确。')
  const history:AskMessage[]=[]
  for(const item of raw){
    if(!record(item)||!['ai','assistant','user'].includes(String(item.role))||typeof item.content!=='string')throw new Error('对话记录格式不正确。')
    if(!item.content)continue
    if(length(item.content)>8000)throw new Error('单条对话超过8000字符，请清空对话后重试。')
    history.push({role:item.role==='user'?'user':'assistant',content:item.content})
  }
  return {question:text,history:history.slice(-12)}
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
