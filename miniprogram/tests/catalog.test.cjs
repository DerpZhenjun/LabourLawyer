const assert=require('node:assert/strict')
const docs=require('../utils/documents')
let request,loaded,failed=false
global.getApp=()=>({globalData:{apiBase:'http://synthetic.invalid'}})
global.wx={request:options=>{request=options}}
docs.loadCatalog(items=>{loaded=items},()=>{failed=true})
const local=docs.findProvince('zhejiang')
const wire={...local};delete wire.shortName
request.success({statusCode:200,data:{items:[wire]}})
assert(!failed&&loaded?.[0].slug==='zhejiang','Live catalog omits local display shortName; it must remain compatible')
failed=false;loaded=null
request.success({statusCode:200,data:{items:[{...wire,forms:{applicationFields:[],evidenceFields:[],limits:{},fieldDefinitions:{}}}]}})
assert(failed&&!loaded,'Malformed limits must not become usable form metadata')
console.log('PASS actual mini catalog accepts server wire shape and rejects malformed form metadata')
