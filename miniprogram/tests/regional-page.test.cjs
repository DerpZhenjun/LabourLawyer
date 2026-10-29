const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const vm = require('node:vm')
const root = path.resolve(__dirname, '../..')
const pageFile = path.join(root, 'miniprogram/pages/regional/index.js')
const transportFile = path.join(root, 'miniprogram/utils/regionalTransport.js')
assert(fs.existsSync(pageFile), 'Regional Page has not been implemented')
assert(fs.existsSync(transportFile), 'Own wx regional transport has not been implemented')
const sharedFile = path.join(root, 'miniprogram/utils/generated/regional-contracts.js')
assert(fs.existsSync(sharedFile), 'Root-owned compiled shared contract runtime is required; no local schema fallback')
const shared = require(sharedFile)
const transportModule = require(transportFile)
let passed = 0
const test = (name, run) => { run(); passed++; console.log('PASS ' + name) }
const clone = value => JSON.parse(JSON.stringify(value))
const event = (value, dataset = {}) => ({detail:{value},currentTarget:{dataset}})
const regionA = {province:'zhejiang', city:'合成市', district:'虚构甲区'}
const regionB = {...regionA, district:'虚构乙区'}
const template = (id, kind) => ({id, original_name:'虚构验收.docx',file_type:'docx',official_kind:'blank',download_status:'downloaded',file:'public/synthetic.docx',sha256:'b'.repeat(64),source_url:'https://example.gov.cn/fiction',can_generate:true,document_types:[kind],adapter:'synthetic_shared_adapter'})
const guide = (region=regionA, version=1) => ({...region,region_code:region.district===regionA.district?'330199':'330198',source_id:region.district===regionA.district?'synthetic-a':'synthetic-b',version,published:true,verification_status:'verified',source_url:'https://example.gov.cn/fiction',fields:{'虚构窗口':{raw_value:'仅验收使用'}},sections:{},channel:{form:'window_and_online',online_status:'auth_required'},warnings:['虚构来源警告'],materials:[{id:'material-a',name:'虚构材料',copies:'2',required:'必要',source_url:'https://example.gov.cn/fiction'}],templates:[template('synthetic-app','application'),template('synthetic-evidence','evidence')]})
function contract(g=guide(),kind='application') {
 const context={province:g.province,city:g.city,district:g.district,region_code:g.region_code,source_id:g.source_id,version:g.version,template_id:kind==='application'?'synthetic-app':'synthetic-evidence',kind,mode:'blank',adapter:'synthetic_shared_adapter'}
 const fields=kind==='application'?[{key:'applicantName',label:'虚构申请人',type:'text',maxLength:300},{key:'applicationDate',label:'申请日期',type:'text',format:'iso-date',maxLength:300},{key:'copyCount',label:'副本份数',type:'copies',nullable:true,integer:true,min:1,max:30,allow_leading_zero:false},{key:'requests',label:'请求事项',type:'text_list',maxLength:1200,maxItems:2},{key:'factsReason',label:'事实与理由',type:'text',maxLength:12000}]:[{key:'committeeName',label:'仲裁委员会',type:'text',maxLength:300},{key:'evidenceList',label:'证据',type:'object_list',maxItems:3,fields:[{key:'name',label:'名称',type:'text',maxLength:300},{key:'source',label:'来源',type:'text',maxLength:300},{key:'purpose',label:'证明内容',type:'text',maxLength:1200}]}]
 const defaults=kind==='application'?{applicantName:'',applicationDate:'',copyCount:'',requests:[''],factsReason:''}:{committeeName:'',evidenceList:[{name:'',source:'',purpose:''}]}
 return {schema_version:1,contract_id:(kind==='application'?'a':'e').repeat(64),context,fields,defaults,policy:{unknown_fields:'reject',invalid_xml:'reject',capacity_is_official_requirement:false,trim_text:false}}
}
function harness(storage={}) {
 let definition
 const requests=[],modals=[],writes=[],opens=[]
 const wx={env:{USER_DATA_PATH:'/synthetic-device'},getStorageSync:key=>storage[key],setStorageSync:(key,value)=>{storage[key]=clone(value)},removeStorageSync:key=>{delete storage[key]},setNavigationBarTitle(){},setClipboardData(){},showModal:opts=>modals.push(opts),request:opts=>{const task={aborted:false,abort(){this.aborted=true;opts.fail?.({errMsg:'abort'})}};requests.push({...opts,task});return task},getFileSystemManager:()=>({writeFile:opts=>writes.push(opts)}),openDocument:opts=>opens.push(opts)}
 const transport=transportModule.createRegionalTransport(wx,()=> 'https://synthetic.invalid')
 vm.runInNewContext(fs.readFileSync(pageFile,'utf8'),{Page:d=>{definition=d},wx,getApp:()=>({globalData:{apiBase:'https://synthetic.invalid'}}),require:request=>request.includes('generated/regional-contracts')?shared:request.includes('regionalTransport')?{...transportModule,createRegionalTransport:()=>transport}:request.endsWith('data/provinces')?[{slug:'zhejiang',name:'浙江省'},{slug:'jiangsu',name:'江苏省'}]:(()=>{throw new Error('Unexpected local rule dependency '+request)})(),Array,Object,JSON,String,Number,Date,Set,Reflect,ArrayBuffer,Uint8Array,DataView,encodeURIComponent,decodeURIComponent})
 const page=definition;page.data=clone(definition.data);page.setData=value=>Object.assign(page.data,value)
 const last=needle=>[...requests].reverse().find(r=>r.url.includes(needle))
 const respond=(request,data,statusCode=200,header={})=>request.success({statusCode,data,header})
 const start=()=>{page.onLoad({province:'zhejiang'});respond(last('/areas'),{items:[{province:'zhejiang',city:'合成市'}]});page.onCityChange(event('0'));respond(last('/areas'),{items:[{...regionA,code:'330199'},{...regionB,code:'330198'}]})}
 const select=(index=0)=>{page.onDistrictChange(event(String(index)));const g=guide(index===0?regionA:regionB);respond(last('/lookup'),g);respond(last('/form-contract'),contract(g));return g}
 return {page,wx,requests,modals,writes,opens,storage,last,respond,start,select}
}
function headers(c, t=template('synthetic-app','application')) {return {'X-Guide-Source-ID':c.context.source_id,'X-Guide-Version':String(c.context.version),'X-Template-SHA256':t.sha256,'X-Form-Contract-ID':c.contract_id}}
function zip() {
 const names=['[Content_Types].xml','_rels/.rels','word/document.xml'];const locals=[],central=[];let offset=0
 for(const name of names){const n=Buffer.from(name),text=Buffer.from('<x/>'),l=Buffer.alloc(30+n.length+text.length);l.writeUInt32LE(0x04034b50,0);l.writeUInt32LE(text.length,18);l.writeUInt32LE(text.length,22);l.writeUInt16LE(n.length,26);n.copy(l,30);text.copy(l,30+n.length);locals.push(l);const c=Buffer.alloc(46+n.length);c.writeUInt32LE(0x02014b50,0);c.writeUInt32LE(text.length,20);c.writeUInt32LE(text.length,24);c.writeUInt16LE(n.length,28);c.writeUInt32LE(offset,42);n.copy(c,46);central.push(c);offset+=l.length}
 const cd=Buffer.concat(central),end=Buffer.alloc(22);end.writeUInt32LE(0x06054b50);end.writeUInt16LE(names.length,8);end.writeUInt16LE(names.length,10);end.writeUInt32LE(cd.length,12);end.writeUInt32LE(offset,16);const b=Buffer.concat([...locals,cd,end]);return b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength)
}

test('transport encodes exact region, source/version/template/kind and uses arraybuffer without model routes',()=>{
 const h=harness();h.start();h.select();const c=contract();assert.match(h.last('/form-contract').url,/source_id=synthetic-a/);assert.match(h.last('/form-contract').url,/version=1/);h.page.generate();h.modals.at(-1).success({confirm:true});const r=h.last('/generate');assert.equal(r.responseType,'arraybuffer');assert.equal(r.data.contract_id,c.contract_id);assert.deepEqual(r.data,shared.buildGenerateRequest(c,h.page._form));assert(h.requests.every(r=>r.url.includes('/api/regional-guides/')))
})
test('scope changes clear guide+contract immediately, abort and ignore A-B-A old callbacks',()=>{
 const h=harness();h.start();h.select();h.page.onDistrictChange(event('1'));const old=h.last('/lookup');assert.equal(h.page.data.guide,null);assert.equal(h.page.data.contract,null);h.page.onDistrictChange(event('0'));assert(old.task.aborted);h.respond(old,guide(regionB));assert.equal(h.page.data.guide,null);h.respond(h.last('/lookup'),guide());h.respond(h.last('/form-contract'),contract());h.respond(old,guide(regionB));assert.equal(h.page.data.guide.district,regionA.district)
})
test('wrong source/version/template contract fails closed and pending locality never falls back',()=>{
 const h=harness();h.start();h.page.onDistrictChange(event('0'));h.respond(h.last('/lookup'),guide());const bad=contract();bad.context.source_id='another-source';h.respond(h.last('/form-contract'),bad);assert(!h.page.data.available);assert.equal(h.page.data.contract,null)
 h.page.onDistrictChange(event('1'));h.respond(h.last('/lookup'),{...regionB,region_id:'pending',source_id:null,verification_status:'unverified',fields:{},materials:[],templates:[],sections:{},channel:{},message:'该地区办事指南尚未核验'});assert(!h.page.data.available);assert.match(h.page.data.notice,/待核验|尚未核验/)
})
test('all wire controls, limits and lossless input use shared validation, not province config',()=>{
 const h=harness();h.start();h.select();assert.equal(h.page.data.controls.filter(c=>c.viewType==='scalar').length,4);h.page.onInput(event('  中文😀 '+ '字'.repeat(301),{path:JSON.stringify(['applicantName'])}));assert.equal(h.page._form.applicantName,'  中文😀 '+ '字'.repeat(301));assert(!h.page.data.formValid);h.page.generate();assert.equal(h.modals.length,0);assert(h.page.data.errors.length)
})
test('dynamic list budgets and single evidence row do not hardcode four or forty',()=>{
 const h=harness();h.start();h.select();h.page.addItem(event('',{path:JSON.stringify(['requests'])}));h.page.addItem(event('',{path:JSON.stringify(['requests'])}));assert.equal(h.page._form.requests.length,2)
 h.page.onKindChange(event('1'));h.respond(h.last('/form-contract'),contract(guide(),'evidence'));assert.equal(h.page._form.evidenceList.length,1);h.page.removeItem(event('',{path:JSON.stringify(['evidenceList']),index:0}));assert.equal(h.page._form.evidenceList.length,1);h.page.addItem(event('',{path:JSON.stringify(['evidenceList'])}));h.page.addItem(event('',{path:JSON.stringify(['evidenceList'])}));h.page.addItem(event('',{path:JSON.stringify(['evidenceList'])}));assert.equal(h.page._form.evidenceList.length,3)
})
test('cancel and stale modal confirmations never generate or clear another scope',()=>{
 const h=harness();h.start();h.select();h.page.generate();const cancel=h.modals.at(-1);cancel.success({confirm:false,cancel:true});assert(!h.last('/generate'));h.page.generate();const old=h.modals.at(-1);h.page.onDistrictChange(event('1'));old.success({confirm:true});assert(!h.last('/generate'))
})
test('generated valid Word package saves and opens; invalid ZIP or wrong source headers are rejected',()=>{
 const h=harness();h.start();h.select();h.page.generate();h.modals.at(-1).success({confirm:true});h.respond(h.last('/generate'),new Uint8Array([80,75,3,4]).buffer,200,headers(contract()));assert.equal(h.writes.length,0);assert(!h.page.data.busy)
 h.page.generate();h.modals.at(-1).success({confirm:true});h.respond(h.last('/generate'),zip(),200,{...headers(contract()),'X-Guide-Source-ID':'wrong'});assert.equal(h.writes.length,0)
 h.page.generate();h.modals.at(-1).success({confirm:true});h.respond(h.last('/generate'),zip(),200,headers(contract()));assert.equal(h.writes.length,1);h.writes[0].success();assert.equal(h.opens.length,1);assert.equal(h.opens[0].fileType,'docx');h.opens[0].success();assert(!h.page.data.busy)
})
test('late binary/write/open callbacks cannot report success in a changed locality',()=>{
 const h=harness();h.start();h.select();h.page.generate();h.modals.at(-1).success({confirm:true});const r=h.last('/generate');h.respond(r,zip(),200,headers(contract()));const write=h.writes[0];h.page.onDistrictChange(event('1'));write.success();assert.equal(h.opens.length,0);assert.equal(h.page.data.result,'');h.respond(r,zip(),200,headers(contract()));assert.equal(h.writes.length,1)
})
test('draft identities isolate region+source+version+template+kind and unknown data is not discarded',()=>{
 const h=harness();h.start();h.select();h.page.onInput(event('甲区私有草稿',{path:JSON.stringify(['applicantName'])}));h.page.saveDraft();const first=h.page.draftKey;h.page.onDistrictChange(event('1'));h.respond(h.last('/lookup'),guide(regionB));h.respond(h.last('/form-contract'),contract(guide(regionB)));assert.notEqual(h.page.draftKey,first);assert.notEqual(h.page._form.applicantName,'甲区私有草稿')
 const envelope=clone(h.storage[first]);envelope.form.legacy='不能被丢弃';h.storage[first]=envelope;h.page.onDistrictChange(event('0'));h.respond(h.last('/lookup'),guide());h.respond(h.last('/form-contract'),contract());assert.equal(h.page._form.legacy,'不能被丢弃');assert(!h.page.data.formValid);h.page.onInput(event('继续保留',{path:JSON.stringify(['applicantName'])}));assert.equal(h.page._form.legacy,'不能被丢弃')
})
test('stale draft envelope is blocked, clear requires confirmation, storage exceptions do not block generation',()=>{
 const h=harness();h.start();h.select();h.page.saveDraft();const key=h.page.draftKey;h.storage[key].context.version=999;h.page.onDistrictChange(event('0'));h.respond(h.last('/lookup'),guide());h.respond(h.last('/form-contract'),contract());assert(h.page.data.draftBlocked);h.page.clear();h.modals.at(-1).success({confirm:false});assert(h.page.data.draftBlocked);h.page.clear();h.modals.at(-1).success({confirm:true});assert(!h.page.data.draftBlocked)
 h.wx.setStorageSync=()=>{throw new Error('capacity')};h.page.generate();h.modals.at(-1).success({confirm:true});assert(h.last('/generate'));assert.match(h.page.data.storageNotice,/草稿|保存/)
})
test('original blank GET binds source/version and verifies template SHA headers before save',()=>{
 const h=harness();h.start();h.select();h.page.downloadBlank(event('',{index:0}));h.modals.at(-1).success({confirm:true});const r=h.last('/templates/');assert.match(r.url,/source_id=synthetic-a/);assert.match(r.url,/version=1/);assert.equal(r.responseType,'arraybuffer');h.respond(r,zip(),200,headers(contract()));assert.equal(h.writes.length,1)
})
test('Unicode/XML, copy/date lexical rules and sparse/extra lists are validated losslessly',()=>{
 const h=harness();h.start();h.select();const input=(key,value)=>h.page.onInput(event(value,{path:JSON.stringify([key])}));input('applicantName','😀');assert.equal(h.page.data.controls.find(c=>c.label==='虚构申请人').count,1);input('applicationDate','2025-02-29');assert(!h.page.data.formValid);input('applicationDate','0001-01-01');input('copyCount','01');assert(!h.page.data.formValid);input('copyCount','');input('applicantName','甲\u0000乙');assert.equal(h.page._form.applicantName,'甲\u0000乙');assert(!h.page.data.formValid);input('applicantName','甲\n乙😀');assert(h.page.data.formValid)
 const sparse=new Array(2);sparse[1]='保留';h.page._form.requests=sparse;h.page.refresh();assert(!h.page.data.formValid);h.page.saveDraft();assert.match(h.page.data.storageNotice,/保存/);assert(!(0 in h.page._form.requests));h.page._form.requests=[''];h.page._form.requests.extra='保留';h.page.refresh();assert(!h.page.data.formValid);h.page.saveDraft();assert.equal(h.page._form.requests.extra,'保留')
})
test('HTTP failures and old preview callbacks do not create current success or lose form data',()=>{
 const h=harness();h.start();h.select();h.page.onInput(event('保留原文',{path:JSON.stringify(['applicantName'])}));h.page.generate();h.modals.at(-1).success({confirm:true});h.respond(h.last('/generate'),new TextEncoder().encode('{"detail":"请核对份数"}').buffer,422);assert.equal(h.writes.length,0);assert.equal(h.page._form.applicantName,'保留原文');assert.match(h.page.data.error,/份数/)
 h.page.generate();h.modals.at(-1).success({confirm:true});h.respond(h.last('/generate'),zip(),200,headers(contract()));h.writes.at(-1).success();const old=h.opens.at(-1);h.page.onDistrictChange(event('1'));old.success();old.fail();assert.equal(h.page.data.result,'');assert.equal(h.page.data.error,'')
})
test('contract-driven choices and own source details are rendered without a province rule filter',()=>{
 const h=harness();h.start();h.page.onDistrictChange(event('0'));const g=guide();g.sections={'受理条件':'自己的条件','窗口':[{address:'自己的窗口',addressPhone:'虚构电话'}]};g.channel.raw_value='网上申请和现场窗口';h.respond(h.last('/lookup'),g);const c=contract();c.fields.push({key:'consent',label:'本人意愿',type:'text',maxLength:10,choices:['同意','不同意']});c.defaults.consent='';h.respond(h.last('/form-contract'),c);const control=h.page.data.controls.find(x=>x.label==='本人意愿');assert.deepEqual(control.choices,['同意','不同意']);h.page.onChoice(event('1',{path:control.path}));assert.equal(h.page._form.consent,'不同意');assert(h.page.data.sections.some(s=>s.label==='受理条件'&&s.value.includes('自己的条件')));assert.match(h.page.data.channelText,/网上申请/)
})
test('multiple confirmations and duplicate callbacks run a single file operation',()=>{
 const h=harness();h.start();h.select();h.page.generate();const first=h.modals.at(-1);h.page.generate();const second=h.modals.at(-1);first.success({confirm:true});first.success({confirm:true});second.success({confirm:true});assert.equal(h.requests.filter(r=>r.url.includes('/generate')).length,1);const r=h.last('/generate');h.respond(r,zip(),200,headers(contract()));h.respond(r,zip(),200,headers(contract()));assert.equal(h.writes.length,1);h.writes[0].success();h.writes[0].success();assert.equal(h.opens.length,1);h.opens[0].success();const result=h.page.data.result;h.opens[0].fail();assert.equal(h.page.data.result,result);assert.equal(h.page.data.error,'')
})
test('template SHA mismatch and stale 409 block saving/generation without replacing old content',()=>{
 const h=harness();h.start();h.select();h.page.downloadBlank(event('',{index:0}));h.modals.at(-1).success({confirm:true});h.respond(h.last('/templates/'),zip(),200,{...headers(contract()),'X-Template-SHA256':'c'.repeat(64)});assert.equal(h.writes.length,0);h.page.generate();h.modals.at(-1).success({confirm:true});h.respond(h.last('/generate'),new TextEncoder().encode('{"detail":"版本已变更"}').buffer,409);assert.equal(h.page.data.contract,null);assert(!h.page.data.available);h.page.generate();assert.equal(h.requests.filter(r=>r.url.includes('/generate')).length,1)
})
test('generated response must identify the exact submitted form contract',()=>{
 const h=harness();h.start();h.select();h.page.generate();h.modals.at(-1).success({confirm:true});const bad={...headers(contract()),'X-Form-Contract-ID':'c'.repeat(64)};h.respond(h.last('/generate'),zip(),200,bad);assert.equal(h.writes.length,0);assert(!h.page.data.busy)
 h.page.generate();h.modals.at(-1).success({confirm:true});const missing=headers(contract());delete missing['X-Form-Contract-ID'];h.respond(h.last('/generate'),zip(),200,missing);assert.equal(h.writes.length,0)
})
test('WXML keeps visible labels, safe text controls, official/technical distinction and province entry',()=>{
 const wxml=fs.readFileSync(path.join(root,'miniprogram/pages/regional/index.wxml'),'utf8');assert.match(wxml,/aria-label=/);assert.match(wxml,/<label/);assert.match(wxml,/maxlength="-1"/);assert.match(wxml,/技术容量/);assert.match(wxml,/本人.*签/);const app=JSON.parse(fs.readFileSync(path.join(root,'miniprogram/app.json'),'utf8'));assert(app.pages.includes('pages/regional/index'));assert.match(fs.readFileSync(path.join(root,'miniprogram/pages/province/index.wxml'),'utf8'),/区县/)
})
console.log(`PASS miniprogram regional: ${passed} Page/transport checks; synthetic only; no network or device claims`)
