import assert from 'node:assert/strict'
import {existsSync, readFileSync} from 'node:fs'
import {createRequire} from 'node:module'
import {fileURLToPath} from 'node:url'
import {spawnSync} from 'node:child_process'

const base=new URL('../',import.meta.url)
const dataUrl=new URL('../frontend/src/data/jiangsuOwnFields.js',import.meta.url)
const componentUrl=new URL('../frontend/src/components/JiangsuOwnFields.vue',import.meta.url)
const fields=existsSync(dataUrl)?await import(dataUrl):{}
let passed=0
const test=async(label,run)=>{await run();passed++;console.log(`PASS ${label}`)}
await test('Jiangsu own field API exists',()=>{
  for(const key of ['createEmptyJiangsuOwn','createJiangsuOwnExample','validateJiangsuOwn','jiangsuOwnPayload'])
    assert.equal(typeof fields[key],'function',`${key} 尚未实现`)
})
const {createEmptyJiangsuOwn,createJiangsuOwnExample,validateJiangsuOwn,jiangsuOwnPayload}=fields
const appKeys='committeeName applicantName birthDate gender idNumber idAddress otherDocumentType otherDocumentNumber applicantMailingAddress phone acceptMediation legalAid respondentName respondentType registeredAddress socialCreditCode legalRepName legalRepPosition departmentHead departmentHeadPosition mailingAddress companyContact companyContactPhone requests factsReason applicationDate copyCount evidenceCopyCount'.split(' ').sort()
const evidenceKeys=['committeeName','caseNumber','submitDate','evidenceList'].sort()
const itemKeys=['name','source','purpose','originalType','pageCount'].sort()
await test('examples use exactly the own keys, fictional facts, blank date/copies and independent rows',()=>{
  const app=createJiangsuOwnExample('application'),ev=createJiangsuOwnExample('evidence')
  assert.deepEqual(Object.keys(app).sort(),appKeys);assert.deepEqual(Object.keys(ev).sort(),evidenceKeys)
  assert.deepEqual(Object.keys(ev.evidenceList[0]).sort(),itemKeys)
  assert(validateJiangsuOwn(app,'application').valid);assert(validateJiangsuOwn(ev,'evidence').valid)
  assert.match(app.applicantName,/虚构/);assert.match(app.respondentName,/虚构/)
  assert.match(app.factsReason,/虚构/);assert.match(app.requests[0],/虚构/)
  assert.equal(app.applicationDate,'');assert.equal(app.birthDate,'');assert.equal(app.copyCount,'');assert.equal(app.evidenceCopyCount,'');assert.equal(app.acceptMediation,'');assert.equal(app.legalAid,'')
  assert.equal(ev.submitDate,'');assert(!Object.hasOwn(ev,'copyCount'));assert.equal(ev.evidenceList.length,1)
  const other=createJiangsuOwnExample('evidence');other.evidenceList[0].name='changed'
  assert.notEqual(other.evidenceList[0].name,ev.evidenceList[0].name)
  assert.equal(createEmptyJiangsuOwn('application').requests.length,1)
})
await test('ordinary 300, request 4 x 1200, facts 12000 and evidence 40 limits preserve overlong drafts',()=>{
  for(const key of appKeys.filter(k=>!['requests','copyCount','evidenceCopyCount','factsReason','birthDate','applicationDate'].includes(k))){
    assert(validateJiangsuOwn({[key]:'😀'.repeat(300)},'application').valid,key)
    assert(!validateJiangsuOwn({[key]:'😀'.repeat(301)},'application').valid,key)
  }
  for(const [kind,good,bad] of [
    ['application',{requests:Array(4).fill('汉'.repeat(1200))},{requests:Array(5).fill('请求')}],
    ['application',{factsReason:'😀'.repeat(12000)},{factsReason:'😀'.repeat(12001)}],
    ['application',{requests:['汉'.repeat(1200)]},{requests:['汉'.repeat(1201)]}],
    ['evidence',{evidenceList:Array.from({length:40},()=>({name:'证据'}))},{evidenceList:Array.from({length:41},()=>({name:'证据'}))}],
  ]){assert(validateJiangsuOwn(good,kind).valid);assert(!validateJiangsuOwn(bad,kind).valid);assert.throws(()=>jiangsuOwnPayload(bad,kind))}
  for(const key of itemKeys){const limit=key==='purpose'?1200:300
    assert(validateJiangsuOwn({evidenceList:[{[key]:'汉'.repeat(limit)}]},'evidence').valid)
    assert(!validateJiangsuOwn({evidenceList:[{[key]:'汉'.repeat(limit+1)}]},'evidence').valid)
  }
})
await test('copy count accepts only blank or ASCII integers 1 through 30',()=>{
  for(const key of ['copyCount','evidenceCopyCount'])for(const v of ['',null,1,30,'1','30'])assert(validateJiangsuOwn({[key]:v},'application').valid,key+String(v))
  for(const key of ['copyCount','evidenceCopyCount'])for(const v of [true,false,0,31,-1,1.2,'1.0','01',' 2','２','٢',NaN,Infinity])assert(!validateJiangsuOwn({[key]:v},'application').valid,key+String(v))
  assert(!validateJiangsuOwn({copyCount:''},'evidence').valid)
})
await test('unknown keys even empty, invalid Unicode/XML, array extras and wrong shapes cannot be discarded',()=>{
  const requests=['请求'];requests.legacy=''
  const evidenceList=[{name:'证据'}];evidenceList.extra=''
  for(const [kind,v] of [
    ['application',{signature:''}],['application',{evidenceList:[]}],['application',{requests}],['application',{requests:new Array(2)}],
    ['evidence',{evidenceList}],['evidence',{evidenceList:[{name:'证据',unsupported:''}]}],
    ['application',{factsReason:'坏\0字符'}],['application',{applicantName:'\ud800'}],
    ['application',{applicantName:'\ufffe'}],['application',{requests:[5]}],['evidence',{evidenceList:[null]}],
    ['evidence',{evidenceList:new Array(1)}],
    ['application',null],['application',[]],['evidence',{requests:[]}],
  ]){const result=validateJiangsuOwn(v,kind);assert(!result.valid,JSON.stringify(v));assert.throws(()=>jiangsuOwnPayload(v,kind),e=>e.fieldErrors?.length>0)}
  const hidden=Object.defineProperty({},'unknown',{value:'',enumerable:false})
  assert(!validateJiangsuOwn(hidden,'application').valid)
  assert(validateJiangsuOwn({factsReason:'中文😀\t\r\n'},'application').valid)
})
await test('strict Gregorian dates keep year0001..9999 and reject normalized or partial dates',()=>{
  for(const [kind,key] of [['application','birthDate'],['application','applicationDate'],['evidence','submitDate']]){
    for(const v of ['','0001-01-01','0099-02-28','2000-02-29','2024-02-29','9999-12-31'])assert(validateJiangsuOwn({[key]:v},kind).valid,v)
    for(const v of [null,1,'0000-01-01','10000-01-01','1900-02-29','2023-02-29','2026-04-31','2026-13-01','2026-1-02','2026-01-1',' 2026-01-01','2026-01-01T00:00:00Z'])assert(!validateJiangsuOwn({[key]:v},kind).valid,String(v))
  }
  assert(validateJiangsuOwn({acceptMediation:'本人待核对的自由文字',legalAid:'不预设答案'},'application').valid)
  assert(validateJiangsuOwn({evidenceList:[{source:'自由来源，不限制枚举',originalType:'本人核对的文字'}]},'evidence').valid)
})
await test('payload preserves all whitespace, blank rows and numeric values in a deep copy',()=>{
  const input={...createJiangsuOwnExample('application'),applicantName:'  虚构姓名  ',requests:[' 第一项 ','','最后一项\n第二行'],factsReason:'\n 保留所有空白\r\n',copyCount:2}
  const out=jiangsuOwnPayload(input,'application');assert.deepEqual(out,input)
  out.requests[0]='changed';assert.notEqual(out.requests[0],input.requests[0])
  const ev={evidenceList:[{name:'  证据  ',pageCount:'200页',source:'',purpose:'\n目的\n'}]}
  const copy=jiangsuOwnPayload(ev,'evidence');assert.deepEqual(copy,ev)
  copy.evidenceList[0].name='changed';assert.notEqual(copy.evidenceList[0].name,ev.evidenceList[0].name)
})
await test('DATA_FIELDS/LIMITS and representative validity match the actual EJS provider',()=>{
  const cases=[['application',{}],['application',{applicantName:'汉'.repeat(200)}],['application',{applicantName:'😀'.repeat(301)}],
    ['application',{requests:Array(4).fill('汉'.repeat(1200))}],['application',{requests:['汉'.repeat(1201)]}],
    ['application',{factsReason:'汉'.repeat(12001)}],['application',{applicationDate:'1900-02-29'}],
    ['application',{signature:''}],['application',{copyCount:'01'}],['application',{copyCount:true}],
    ['evidence',{evidenceList:[{pageCount:'汉'.repeat(300),purpose:'汉'.repeat(1200)}]}],
    ['evidence',{evidenceList:[{source:'汉'.repeat(301)}]}],['evidence',{evidenceList:Array.from({length:41},()=>({name:'证据'}))}],
    ['evidence',{copyCount:''}]]
  const result=spawnSync('.venv/Scripts/python.exe',['-B','-c',
    'import json,sys;sys.path.insert(0,"backend");import regional_jiangsu_oct29e as p;out=[]\nfor kind,data in json.loads(sys.stdin.buffer.read().decode("utf8")):\n try:p._validate_data(kind,data);out.append(True)\n except ValueError:out.append(False)\nprint(json.dumps({"adapter":p.ADAPTER,"fields":{k:sorted(v) for k,v in p.DATA_FIELDS.items()},"limits":p.LIMITS,"valid":out}))'],
    {cwd:fileURLToPath(base),input:JSON.stringify(cases),encoding:'utf8'})
  assert.equal(result.status,0,result.stderr);const backend=JSON.parse(result.stdout)
  assert.deepEqual(backend.fields,{application:appKeys,evidence:evidenceKeys,evidence_item:itemKeys})
  assert.deepEqual(fields.JIANGSU_OWN_LIMITS,backend.limits);assert.equal(fields.JIANGSU_OWN_ADAPTER,backend.adapter)
  assert.deepEqual(cases.map(([kind,data])=>validateJiangsuOwn(data,kind).valid),backend.valid)
})

const require=createRequire(new URL('../frontend/package.json',import.meta.url)),compiler=require('@vue/compiler-sfc')
assert(existsSync(componentUrl),'江苏字段组件尚未实现')
const source=readFileSync(componentUrl,'utf8'),{descriptor,errors}=compiler.parse(source,{filename:fileURLToPath(componentUrl)})
let compiled
await test('Vue SFC script/template/styles compile with accessible controls and no input truncation',()=>{
  assert.deepEqual(errors,[]);compiled=compiler.compileScript(descriptor,{id:'jiangsu-own-test',inlineTemplate:true})
  assert.deepEqual(compiler.compileTemplate({source:descriptor.template.content,filename:fileURLToPath(componentUrl),id:'jiangsu-own-test',compilerOptions:{bindingMetadata:compiled.bindings}}).errors,[])
  for(const s of descriptor.styles)assert.deepEqual(compiler.compileStyle({source:s.content,filename:fileURLToPath(componentUrl),id:'jiangsu-own-test',scoped:true}).errors,[])
  assert(!descriptor.template.content.includes('maxlength'));assert.match(source,/aria-invalid/);assert.match(source,/aria-describedby/)
  assert.match(source,/min-height:\s*44px/);assert.match(source,/@media/)
})
const vue=require('vue')
const transformed=compiled.content.replace(/import\s*\{([^}]+)\}\s*from\s*['"]([^'"]+)['"];?/g,(_,names,from)=>`const {${names.replace(/\s+as\s+/g,':')}}=${from==='vue'?'__vue':'__fields'};`).replace('export default','return')
const Component=new Function('__vue','__fields',transformed)(vue,fields)
const node=(type,text='')=>({type,text,children:[],props:{},parent:null})
const remove=el=>{if(el.parent){const i=el.parent.children.indexOf(el);if(i>=0)el.parent.children.splice(i,1);el.parent=null}}
const insert=(el,parent,anchor)=>{remove(el);const i=anchor?parent.children.indexOf(anchor):-1;parent.children.splice(i<0?parent.children.length:i,0,el);el.parent=parent}
const renderer=vue.createRenderer({createElement:node,createText:t=>node('#text',t),createComment:t=>node('#comment',t),setText:(el,t)=>{el.text=t},setElementText:(el,t)=>{el.text=t;el.children=[]},patchProp:(el,key,old,v)=>{el.props[key]=v},insert,remove,parentNode:el=>el.parent,nextSibling:el=>el.parent?.children[el.parent.children.indexOf(el)+1]||null,setScopeId:()=>{},insertStaticContent:(html,p,a)=>{const n=node('#static',html);insert(n,p,a);return[n,n]}})
const root=node('root'),state=vue.ref(undefined),kind=vue.ref('application'),instance=vue.ref()
const app=renderer.createApp({setup:()=>()=>vue.h(Component,{ref:instance,kind:kind.value,modelValue:state.value,'onUpdate:modelValue':v=>{state.value=v}})})
app.mount(root);await vue.nextTick()
const all=(el=root)=>[el,...el.children.flatMap(child=>all(child))]
const text=el=>String(el.text||'')+el.children.map(text).join('')
const button=label=>all().find(el=>el.type==='button'&&(el.props['aria-label']===label||text(el).trim()===label))
const click=async label=>{const el=button(label);assert(el,label);assert(!el.props.disabled,label);el.props.onClick();await vue.nextTick()}
const inputFor=key=>all().find(el=>['input','textarea','select'].includes(el.type)&&el.props.id?.endsWith(`-${key}`))
await test('mounted default is fictional with labels on every control',()=>{
  assert.deepEqual(state.value,createJiangsuOwnExample('application'))
  for(const c of all().filter(el=>['input','textarea','select'].includes(el.type))){assert(c.props.id);assert(all().some(el=>el.type==='label'&&el.props.for===c.props.id));assert(c.props['aria-describedby']);for(const id of c.props['aria-describedby'].split(/\s+/))assert(all().some(el=>el.props.id===id),id)}
  assert.equal(all().filter(el=>['input','textarea','select'].includes(el.type)&&/copyCount$/.test(el.props.id)).length,1)
  for(const key of appKeys.filter(k=>k!=='requests'))assert(inputFor(key),key)
})
await test('mounted labels identify the worker own department and every aria target exists',()=>{
  const id=inputFor('departmentHead').props.id
  const label=all().find(el=>el.type==='label'&&el.props.for===id)
  assert.match(text(label),/劳动者所在部门负责人/)
})
await test('200 characters survive input and 301 characters remain visible with linked field error',async()=>{
  inputFor('applicantName').props.onInput({target:{value:'汉'.repeat(200)}});await vue.nextTick()
  assert.equal(state.value.applicantName.length,200);assert(instance.value.validate().valid)
  inputFor('applicantName').props.onInput({target:{value:'汉'.repeat(301)}});await vue.nextTick()
  const input=inputFor('applicantName');assert.equal(input.props.value.length,301);assert.equal(input.props['aria-invalid'],'true')
  assert(input.props['aria-describedby'].split(/\s+/).some(id=>all().some(el=>el.props.id===id&&/300/.test(text(el)))))
})
await click('清空填写内容')
await test('request controls keep one row, stop at four and preserve existing text',async()=>{
  assert(button('删除第1项请求').props.disabled)
  await click('添加请求事项');await click('添加请求事项');await click('添加请求事项')
  assert.equal(state.value.requests.length,4);assert(button('添加请求事项').props.disabled);assert.match(text(root),/已填写 4 \/ 4 项请求/)
  await click('删除第2项请求');assert.equal(state.value.requests.length,3)
})
kind.value='evidence';state.value=createJiangsuOwnExample('evidence');await vue.nextTick()
await test('evidence rows expose exactly five columns and enforce one through forty rows',async()=>{
  assert(button('删除第1项证据').props.disabled)
  const before=state.value;await click('添加证据');assert.equal(before.evidenceList.length,1);assert.equal(state.value.evidenceList.length,2)
  await click('删除第2项证据');assert.equal(state.value.evidenceList.length,1)
  for(const key of itemKeys)assert(inputFor(`evidenceList.0.${key}`),key)
  state.value={...state.value,evidenceList:Array.from({length:40},()=>({name:'',pageCount:'',source:'',purpose:''}))};await vue.nextTick()
  assert(button('添加证据').props.disabled);assert.match(text(root),/已填写 40 \/ 40 项证据/)
})
await test('evidence overcapacity has a linked row error and retains the full text',async()=>{
  state.value=createJiangsuOwnExample('evidence');await vue.nextTick()
  inputFor('evidenceList.0.purpose').props.onInput({target:{value:'汉'.repeat(1201)}});await vue.nextTick()
  const control=inputFor('evidenceList.0.purpose')
  assert.equal(control.props.value.length,1201);assert.equal(control.props['aria-invalid'],'true')
  assert(control.props['aria-describedby'].split(/\s+/).some(id=>all().some(el=>el.props.id===id&&/1200/.test(text(el)))))
})
await test('editing never silently drops unknown fields from a draft or list',async()=>{
  const draft=createJiangsuOwnExample('evidence');Object.defineProperty(draft,'oldHidden',{value:'',enumerable:false})
  draft.evidenceList.extra='';draft.evidenceList[0].legacy=''
  state.value=draft;await vue.nextTick();inputFor('evidenceList.0.name').props.onInput({target:{value:'汉'.repeat(200)}});await vue.nextTick()
  assert(Object.hasOwn(state.value,'oldHidden'));assert(Object.hasOwn(state.value.evidenceList,'extra'));assert(Object.hasOwn(state.value.evidenceList[0],'legacy'))
  assert(!instance.value.validate().valid);assert.throws(()=>instance.value.getPayload())
  const empty=createEmptyJiangsuOwn('evidence');empty.evidenceList=[];empty.evidenceList.extra=''
  Object.defineProperty(empty.evidenceList,'__proto__',{value:'',enumerable:true})
  state.value=empty;await vue.nextTick();inputFor('evidenceList.0.name').props.onInput({target:{value:'证据'}});await vue.nextTick()
  assert(Object.hasOwn(state.value.evidenceList,'extra'));assert(Object.hasOwn(state.value.evidenceList,'__proto__'))
  assert(!instance.value.validate().valid)
})
await click('清空填写内容')
await test('evidence clear leaves exact keys and a single row without date or copies',()=>{
  assert.deepEqual(state.value,createEmptyJiangsuOwn('evidence'));assert(instance.value.validate().valid)
})
await test('dates and both copy inputs retain invalid text with linked errors, source stays a textarea',async()=>{
  kind.value='application';state.value=createEmptyJiangsuOwn('application');await vue.nextTick()
  for(const [key,value] of [['applicationDate','2023-02-29'],['copyCount','01'],['evidenceCopyCount','31']]){
    inputFor(key).props.onInput({target:{value}});await vue.nextTick()
    assert.equal(inputFor(key).props.value,value);assert.equal(inputFor(key).props['aria-invalid'],'true')
    assert(inputFor(key).props['aria-describedby'].split(/\s+/).some(id=>all().some(el=>el.props.id===id&&el.type==='p')))
  }
  kind.value='evidence';state.value=createEmptyJiangsuOwn('evidence');await vue.nextTick()
  assert.equal(inputFor('evidenceList.0.source').type,'textarea')
  assert(!inputFor('copyCount'));assert(!inputFor('evidenceCopyCount'))
})
app.unmount()
await test('dual drafts survive asynchronous kind changes without overwriting either draft',async()=>{
  const {useJiangsuOwnDrafts}=await import(new URL('../frontend/src/composables/useJiangsuOwnDrafts.js',import.meta.url))
  const selected=vue.ref('application'),draft=useJiangsuOwnDrafts(selected)
  draft.value={...createEmptyJiangsuOwn('application'),factsReason:'申请草稿保留'}
  await vue.nextTick();selected.value='evidence';await vue.nextTick()
  draft.value={...createEmptyJiangsuOwn('evidence'),caseNumber:'证据草稿保留'}
  await Promise.resolve();selected.value='application';await vue.nextTick()
  assert.equal(draft.value.factsReason,'申请草稿保留');assert(!Object.hasOwn(draft.value,'caseNumber'))
  selected.value='evidence';await vue.nextTick();assert.equal(draft.value.caseNumber,'证据草稿保留')
})
console.log(`PASS Jiangsu own fields: ${passed} checks; provider parity, mounted controls, lossless payload and SFC compilation`)
