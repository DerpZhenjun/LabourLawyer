const assert=require('node:assert/strict'),crypto=require('node:crypto')
const docs=require('../utils/documents')
const before=require('./fixtures/legacy-payloads-sha256.json')
for(const item of before.payloads){
  const province=docs.findProvince(item.slug)
  const payload=docs.payloadFor(province[item.kind+'Example'],docs.formConfig(province,item.kind),item.kind)
  assert.equal(crypto.createHash('sha256').update(JSON.stringify(payload)).digest('hex'),item.sha256,item.slug+'/'+item.kind)
}
assert.equal(before.payloads.length,34)
console.log('PASS 34 provincial requests match pre-migration runtime SHA256 exactly')
