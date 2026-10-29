import assert from 'node:assert/strict'
import {existsSync} from 'node:fs'
const url=new URL('../packages/regional-contracts/src/index.ts',import.meta.url)
const api=existsSync(url)?await import(url):{}
assert.equal(typeof api.validateForm,'function','Shared typed form contract runtime is missing')
const context={province:'jiangsu',city:'苏州市',district:'相城区',region_code:'320507',source_id:'fictional-own-source',version:207,template_id:'own-application',kind:'application',mode:'blank',adapter:'jiangsu_own_blank_oct29e_v1'}
const contract={schema_version:1,contract_id:'a'.repeat(64),context,fields:[
  {key:'applicantName',label:'申请人姓名',type:'text',maxLength:300,nullable:false},
  {key:'birthDate',label:'出生日期',type:'text',maxLength:300,format:'iso-date'},
  {key:'copyCount',label:'副本份数',type:'copies',min:1,max:30,integer:true,nullable:true,allow_leading_zero:false},
  {key:'requests',label:'请求',type:'text_list',maxLength:1200,maxItems:4},
  {key:'factsReason',label:'事实',type:'text',maxLength:12000},
],defaults:{applicantName:'',birthDate:'',copyCount:'',requests:[''],factsReason:''},policy:{unknown_fields:'reject',invalid_xml:'reject',capacity_is_official_requirement:false,trim_text:false}}
let count=0
function test(name,run){run();count++;console.log(`PASS ${name}`)}
test('bind contract to exact scope/source/version/template/kind',()=>{
  assert.equal(api.assertFormContract(contract,context).contract_id,contract.contract_id)
  for(const key of ['province','city','district','source_id','template_id','kind','adapter'])assert.throws(()=>api.assertFormContract(contract,{...context,[key]:'foreign'}))
  assert.throws(()=>api.assertFormContract(contract,{...context,version:208}))
  assert.throws(()=>api.assertFormContract({...contract,schema_version:2},context))
})
test('pending guides have no inherited version or capability',()=>{
  const g={province:'zhejiang',city:'杭州市',district:'桐庐县',source_id:null,fields:{},materials:[],templates:[],sections:{},channel:{},verification_status:'unverified'}
  assert.equal(api.assertRegionalGuide(g,g).source_id,null)
  assert.throws(()=>api.assertRegionalGuide({...g,templates:[{id:'wrong',can_generate:true,document_types:['application']}]},g))
  assert.throws(()=>api.assertRegionalGuide(g,{...g,district:'富阳区'}))
})
test('fictional examples keep date/copies blank and never mutate defaults',()=>{
  const a=api.createExampleForm(contract),b=api.createEmptyForm(contract)
  assert.match(a.applicantName,/虚构/);assert.equal(a.birthDate,'');assert.equal(a.copyCount,'')
  assert.equal(b.applicantName,'');assert.equal(b.requests.length,1)
  a.requests.push('changed');assert.equal(contract.defaults.requests.length,1)
})
test('unknown empty keys, symbols, invalid XML, sparse arrays never disappear',()=>{
  for(const bad of [{ghost:''},{[Symbol('ghost')]:''},{applicantName:'\u0001'},{applicantName:'\ud800'},{requests:new Array(2)},{requests:Object.assign(['x'],{hidden:''})}])assert.equal(api.validateForm(contract,{...contract.defaults,...bad}).valid,false)
  assert.throws(()=>api.buildGenerateRequest(contract,{...contract.defaults,ghost:''}))
  assert.equal(api.validateForm(contract,{...contract.defaults,applicantName:'文'.repeat(301)}).valid,false)
  assert.equal(api.validateForm(contract,{...contract.defaults,applicantName:'😀'.repeat(300)}).valid,true)
})
test('copies use descriptor rules without default consent or invented ranges',()=>{
  for(const value of ['01',true,1.5,0,31,' 2 '])assert.equal(api.validateForm(contract,{...contract.defaults,copyCount:value}).valid,false)
  for(const value of ['',null,1,'30'])assert.equal(api.validateForm(contract,{...contract.defaults,copyCount:value}).valid,true)
  const free={...contract,fields:contract.fields.map(f=>f.key==='copyCount'?{key:'copyCount',label:'份数',type:'copies',integer:false,maxLength:160}:f)}
  assert(api.validateForm(free,{...contract.defaults,copyCount:'按本人实际份数填写'}).valid)
  assert(!api.validateForm(free,{...contract.defaults,copyCount:Infinity}).valid)
})
test('strict date uses calendar including leap years and year0001',()=>{
  for(const value of ['0001-01-01','2000-02-29','2024-02-29',''])assert(api.validateForm(contract,{...contract.defaults,birthDate:value}).valid)
  for(const value of ['1900-02-29','2023-02-29','2024-2-9','0000-01-01'])assert(!api.validateForm(contract,{...contract.defaults,birthDate:value}).valid)
})
test('request builder preserves whitespace and exact own binding',()=>{
  const form={...contract.defaults,applicantName:'  虚构测试  ',requests:[' 一项\n二行 '],factsReason:'\n事实\n'}
  const r=api.buildGenerateRequest(contract,form)
  assert.equal(r.contract_id,contract.contract_id);assert.equal(r.source_id,context.source_id);assert.equal(r.version,207)
  assert.deepEqual(r.data,form);r.data.requests.push('new');assert.equal(form.requests.length,1)
  assert.equal(Object.hasOwn(r,'adapter'),false)
})
test('object lists reject foreign fields, start one row, preserve 40 item capacity',()=>{
  const c={...contract,context:{...context,kind:'evidence'},fields:[{key:'evidenceList',label:'证据',type:'object_list',maxItems:40,fields:[{key:'name',label:'名称',type:'text',maxLength:300},{key:'purpose',label:'用途',type:'text',maxLength:1200}]}],defaults:{evidenceList:[{name:'',purpose:''}]}}
  assert.equal(api.createEmptyForm(c).evidenceList.length,1)
  assert.equal(api.validateForm(c,{evidenceList:[{name:'',purpose:'',copyCount:''}]}).valid,false)
  assert.equal(api.validateForm(c,{evidenceList:Array.from({length:41},()=>({name:'',purpose:''}))}).valid,false)
  assert.equal(api.validateForm(c,{copyCount:'',evidenceList:[]}).valid,false)
})
test('portable query and error rendering need no browser or WeChat globals',()=>{
  assert.equal(api.regionQuery({province:'zhejiang',city:'杭州市',district:'富阳区'}),'province=zhejiang&city=%E6%9D%AD%E5%B7%9E%E5%B8%82&district=%E5%AF%8C%E9%98%B3%E5%8C%BA')
  assert.equal(api.parseApiError({detail:'来源已改变'}),'来源已改变')
  assert.equal(api.parseApiError({detail:[{input:'sensitive'}]},'请重新核对'),'请重新核对')
})
test('malformed contract cannot allocate huge arrays or introduce executable field names',()=>{
  assert.throws(()=>api.assertFormContract({...contract,fields:[{key:'__proto__',label:'wrong',type:'text'}]},context))
  assert.throws(()=>api.assertFormContract({...contract,fields:[{key:'requests',label:'wrong',type:'text_list',maxItems:1e10,maxLength:300}]},context))
  assert.throws(()=>api.assertFormContract({...contract,defaults:{...contract.defaults,extra:''}},context))
})
test('guide-only original attachments may omit generation capability',()=>{
  const g={province:'anhui',city:'合肥市',district:'瑶海区',source_id:'own-guide',region_code:'340102',version:1,fields:{},materials:[],templates:[{id:'own-original',document_types:[]}],sections:{},channel:{}}
  const actual=api.assertRegionalGuide(g,g);assert.equal(actual.templates[0].can_generate,undefined)
  assert.throws(()=>api.assertRegionalGuide({...g,templates:[{id:'bad',can_generate:'yes',document_types:[]}]},g))
})
test('known non-enumerable slots survive the request boundary',()=>{
  const raw={...contract.defaults};Object.defineProperty(raw,'applicantName',{value:'虚构保留文字',enumerable:false});assert(api.validateForm(contract,raw).valid);assert.equal(api.buildGenerateRequest(contract,raw).data.applicantName,'虚构保留文字')
})
console.log(`PASS shared regional contracts: ${count} runtime cases`)
