import {assertAIStatus,buildAskRequest,createAnswerDecoder} from '../../../packages/client-contracts/src/index.ts'
import type {AIStatus,ChatMessage} from '../../../packages/client-contracts/src/index.ts'
import {apiURL,readJSON} from './http.ts'
export const assistantStatus=(signal:AbortSignal):Promise<AIStatus>=>readJSON('/api/ai/status',{signal,cache:'no-store'}).then(assertAIStatus)
export async function askAssistant(question:string,messages:ChatMessage[],signal:AbortSignal,onChunk:(text:string)=>void):Promise<void>{
  const response=await fetch(apiURL('/api/ask'),{method:'POST',signal,headers:{'Content-Type':'application/json'},body:JSON.stringify(buildAskRequest(question,messages))})
  if(!response.ok||!response.body)throw new Error('远程问答服务暂不可用。')
  const reader=response.body.getReader(),decoder=createAnswerDecoder()
  try{while(true){const {value,done}=await reader.read();if(done){onChunk(decoder.finish());break}onChunk(decoder.push(value))}}
  finally{reader.releaseLock()}
}
