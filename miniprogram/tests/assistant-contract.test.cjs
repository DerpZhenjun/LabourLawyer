const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path')
let page,request,taskAborted=false,toasts=[]
const filename=path.resolve(__dirname,'../pages/assistant/index.js')
vm.runInNewContext(fs.readFileSync(filename,'utf8'),{Page:p=>page=p,require:name=>require(path.resolve(path.dirname(filename),name)),getApp:()=>({globalData:{apiBase:'http://127.0.0.1:8000'}}),wx:{showToast:o=>toasts.push(o.title),request:o=>{request=o;return {abort:()=>{taskAborted=true}}}}})
page.setData=function(value){Object.assign(this.data,value)}
page.data.input='虚构测试';page.send();assert.equal(request.data.question,'虚构测试');assert(request.data.history.every(m=>['user','assistant'].includes(m.role)))
request.success({statusCode:503,data:'service unavailable'});request.complete();assert(!page.data.messages.at(-1).content.includes('service unavailable'),'Non-200 body must not be shown as an answer')
page.data.input='😀'.repeat(8001);request=null;page.send();assert.equal(request,null);assert(toasts.length>0)
page.data.input='虚构新问题';page.send();const before=page.data.messages.length;page.onUnload();request.success({statusCode:200,data:'迟到回答'});assert.equal(page.data.messages.length,before);assert(taskAborted)
console.log('PASS actual mini assistant uses shared payload, rejects HTTP errors and capacity, aborts stale callbacks; no network')
