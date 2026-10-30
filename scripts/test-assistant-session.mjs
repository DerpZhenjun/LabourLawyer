import assert from 'node:assert/strict'
import {createAssistantChat} from '../frontend/src/composables/useAssistantChat.ts'
const held=[];let written='broken storage'
const storage={getItem:()=>written,setItem:(_k,v)=>{written=v}}
const chat=createAssistantChat((q,h,s,c)=>new Promise((resolve,reject)=>held.push({q,h,s,c,resolve,reject})),storage)
assert.equal(written,'broken storage','Invalid stored bytes must not be overwritten by loading')
chat.inputQuery.value='虚构测试';const first=chat.sendMessage();assert(chat.isLoading.value);held[0].c('部分回答');assert.equal(chat.messages.value.at(-1).content,'部分回答')
chat.clearHistory();assert(held[0].s.aborted);held[0].c('不能回填');held[0].resolve();await first;assert.equal(chat.messages.value.length,1)
chat.inputQuery.value='新的虚构问题';const second=chat.sendMessage();held[1].c('测试成功');held[1].resolve();await second;assert.equal(chat.messages.value.at(-1).content,'测试成功');assert(!chat.isLoading.value)
const restored=createAssistantChat(async()=>{},storage);assert.equal(restored.messages.value.at(-1).content,'测试成功')
const disabled=createAssistantChat(async()=>{throw Error('must not send')},undefined);disabled.inputQuery.value='测试';await disabled.sendMessage(false);assert.equal(disabled.messages.value.length,1)
console.log('PASS chat clear/abort race, incremental answer, storage recovery and remote-readiness gate; synthetic only')
