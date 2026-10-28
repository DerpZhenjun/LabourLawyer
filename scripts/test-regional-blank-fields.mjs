import assert from 'node:assert/strict'
import {regionalApplicationFields,regionalExtraFields,applicationPayload} from '../frontend/src/data/regionalDocumentFields.js'
const base=[{key:'nationality',label:'民族'},{key:'idAddress',label:'户籍地址'},{key:'currentAddress',label:'现在住址'}]
const jsExtra=[{key:'copyCount'},{key:'evidenceCopyCount'}]
const own='zhejiang_own_blank_v1'
const shown=[...regionalApplicationFields(base,true,own),...regionalExtraFields(jsExtra,own)]
for(const key of ['nationality','householdType','workAddress','legalRepPhone'])assert(shown.some(f=>f.key===key),'Missing editable own Zhejiang field: '+key)
assert(!regionalApplicationFields(base,true,'jiangsu_xishan_blank_v1').some(f=>f.key==='nationality'))
assert(!regionalExtraFields(jsExtra,own).some(f=>f.key==='evidenceCopyCount'))
const payload=applicationPayload({nationality:'已修改民族',workAddress:'真实工作地址',secretExample:'不可见默认示例',factsReason:'事情经过'},shown,'请求支付工资')
assert.equal(payload.workAddress,'真实工作地址');assert.equal(payload.nationality,'已修改民族')
assert.equal(payload.secretExample,undefined);assert.deepEqual(payload.requests,['请求支付工资'])
console.log('PASS Zhejiang consumed fields are editable, per-template fields differ, hidden values are excluded')
