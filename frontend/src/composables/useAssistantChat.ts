import {ref} from 'vue'
import {buildAskRequest,parseStoredChat} from '../../../packages/client-contracts/src/index.ts'
import type {ChatMessage} from '../../../packages/client-contracts/src/index.ts'
interface Transport { (question:string,messages:ChatMessage[],signal:AbortSignal,chunk:(text:string)=>void):Promise<void> }
interface ChatStorage { getItem(key:string):string|null; setItem(key:string,value:string):void }
const welcome:ChatMessage={role:'ai',content:'你好，我是你的劳动法律助手。\n\n工资没发、没有签合同，或是不知道怎么申请仲裁？说说发生了什么，我可以帮你理清思路和需要准备的材料。'}
export function createAssistantChat(transport:Transport,storage:ChatStorage|undefined,namespace='default'){
  const key='labourlawyer.chat.v2:'+encodeURIComponent(namespace)
  let saved:ChatMessage[]|null=null
  try{saved=parseStoredChat(storage?.getItem(key)??null)}catch{ /* Storage may be disabled. */ }
  const messages=ref<ChatMessage[]>(saved??[{...welcome}]),inputQuery=ref(''),isLoading=ref(false)
  let dirty=false,sequence=0,controller:AbortController|undefined
  const save=()=>{try{storage?.setItem(key,JSON.stringify(messages.value))}catch{ /* Keep the conversation usable. */ }}
  function cancel(){if(dirty)save();++sequence;controller?.abort();controller=undefined;isLoading.value=false}
  function clearHistory(){dirty=true;cancel();messages.value=[{...welcome}];save()}
  async function sendMessage(ready=true){
    if(!ready||isLoading.value||!inputQuery.value.trim())return
    const question=inputQuery.value.trim(),history=messages.value.filter((m,i)=>!(i===0&&m.role==='ai'&&m.content===welcome.content))
    try{buildAskRequest(question,history)}catch{return}
    dirty=true;const request=++sequence;controller=new AbortController();const signal=controller.signal
    messages.value.push({role:'user',content:question},{role:'ai',content:''});const index=messages.value.length-1
    inputQuery.value='';isLoading.value=true
    try{await transport(question,[...history,{role:'user',content:question}],signal,text=>{if(request===sequence&&messages.value[index])messages.value[index].content+=text})}
    catch(error:unknown){if(request===sequence&&!(error instanceof Error&&error.name==='AbortError'))messages.value.push({role:'ai',content:'暂时无法连接远程助手。请检查项目后端和 Ubuntu AI 连接；文书填写和生成仍可使用。'})}
    finally{if(request===sequence){isLoading.value=false;controller=undefined;save()}}
  }
  return{messages,inputQuery,isLoading,sendMessage,clearHistory,cancel}
}
