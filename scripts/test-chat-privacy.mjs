import assert from 'node:assert/strict'
import {createAssistantChat} from '../frontend/src/composables/useAssistantChat.ts'

const legacyKey='labourlawyer.chat.v1',legacy=JSON.stringify([{role:'user',content:'PRIVATE_LEGACY_CONTEXT'}])
const values=new Map([[legacyKey,legacy]]),reads=[],writes=[]
const storage={getItem(key){reads.push(key);return values.get(key)??null},setItem(key,value){writes.push(key);values.set(key,value)}}
const received=[]
const transport=async(question,history,signal,chunk)=>{received.push(history);chunk('Synthetic response')}
const original=createAssistantChat(transport,storage,'https://service-a.invalid|account-a')
assert.equal(original.messages.value.length,1,'A new context must not import the unscoped legacy conversation')
original.inputQuery.value='PRIVATE_SERVICE_A_ACCOUNT_A';await original.sendMessage()
const otherService=createAssistantChat(transport,storage,'https://service-b.invalid|account-a')
otherService.inputQuery.value='ONLY_NEW_SERVICE';await otherService.sendMessage()
const otherAccount=createAssistantChat(transport,storage,'https://service-a.invalid|account-b')
otherAccount.inputQuery.value='ONLY_NEW_ACCOUNT';await otherAccount.sendMessage()
for(const history of received.slice(1))assert(!JSON.stringify(history).includes('PRIVATE_'),'Old private context crossed a service/account boundary')
const restored=createAssistantChat(transport,storage,'https://service-a.invalid|account-a')
assert(restored.messages.value.some(message=>message.content==='PRIVATE_SERVICE_A_ACCOUNT_A'),'The same context should retain its own tab history')
assert.equal(values.get(legacyKey),legacy,'Legacy bytes must remain untouched')
assert(!reads.includes(legacyKey)&&!writes.includes(legacyKey),'Legacy storage must never be loaded or rewritten automatically')
const unscoped=createAssistantChat(transport,storage)
assert.equal(unscoped.messages.value.length,1,'The default context must use the safe v2 key')
for(const chat of [original,otherService,otherAccount,restored,unscoped])chat.cancel()
console.log('PASS actual chat transport isolates service/account context, preserves legacy bytes, and resumes only the matching v2 scope')
