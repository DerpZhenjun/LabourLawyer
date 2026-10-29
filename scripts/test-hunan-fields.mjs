import assert from 'node:assert/strict'
import {existsSync, readFileSync} from 'node:fs'
import {createRequire} from 'node:module'
import {fileURLToPath} from 'node:url'
import {spawnSync} from 'node:child_process'

const dataUrl=new URL('../frontend/src/data/hunanApplicationFields.js',import.meta.url)
const componentUrl=new URL('../frontend/src/components/HunanApplicationFields.vue',import.meta.url)
const data=existsSync(dataUrl)?await import(dataUrl):{}
let passed=0
const test=(label,run)=>{run();passed++;console.log(`PASS ${label}`)}
test('public Hunan field functions exist',()=>{
  for(const key of ['createHunanApplicationExample','validateHunanApplication','hunanApplicationPayload']){
    assert.equal(typeof data[key],'function',`${key} 尚未实现`)
  }
})
const {createHunanApplicationExample,validateHunanApplication,hunanApplicationPayload}=data
const ordinary=['applicantName','gender','birthDate','occupation','nationality','idAddress','postalCode','phone','workUnit','workUnitPostalCode','workUnitPhone',
  'respondentName','registeredAddress','respondentPostalCode','legalRepName','legalRepPosition','legalRepPhone','hrContactName','hrContactPosition','hrContactPhone',
  'thirdParty','committeeName','copyCount','applicationDate']
const keys=[...ordinary,'requests','factsReason','evidenceList'].sort()
const example=createHunanApplicationExample()
test('example is substantive, fictional, isolated and contains only supported keys',()=>{
  assert.deepEqual(Object.keys(example).sort(),keys)
  assert(validateHunanApplication(example).valid)
  assert.match(example.applicantName,/虚构/);assert.match(example.respondentName,/虚构/)
  assert.match(example.factsReason,/虚构/);assert.match(example.requests.join(''),/\d/)
  assert.equal(example.evidenceList.length,1);assert(example.evidenceList[0].name&&example.evidenceList[0].source&&example.evidenceList[0].purpose)
  assert.equal(example.applicationDate,'');assert.equal(example.copyCount,'')
  const other=createHunanApplicationExample();other.requests[0]='changed';other.evidenceList[0].name='changed'
  assert.notDeepEqual(other.requests,example.requests);assert.notDeepEqual(other.evidenceList,example.evidenceList)
  assert(validateHunanApplication({}).valid)
})
test('ordinary limits count Python Unicode characters, including boundary whitespace',()=>{
  for(const key of ordinary){
    const good={[key]:'汉'.repeat(160)},bad={[key]:'汉'.repeat(161)}
    assert(validateHunanApplication(good).valid,key)
    const validation=validateHunanApplication(bad)
    assert(!validation.valid,key);assert(validation.errors.some(e=>e.field===key&&e.label&&/160/.test(e.message)))
    assert.throws(()=>hunanApplicationPayload(bad),/160/)
  }
  assert(validateHunanApplication({applicantName:'😀'.repeat(160)}).valid)
  assert(!validateHunanApplication({applicantName:'😀'.repeat(161)}).valid)
  assert(!validateHunanApplication({applicantName:' '+ '汉'.repeat(160)}).valid)
  assert.equal(hunanApplicationPayload({copyCount:2}).copyCount,2)
})
test('requests, facts and embedded evidence enforce the own provider capacities',()=>{
  assert(validateHunanApplication({requests:Array(8).fill('请求')}).valid)
  assert(!validateHunanApplication({requests:Array(9).fill('请求')}).valid)
  assert(validateHunanApplication({requests:['汉'.repeat(2000)]}).valid,'No uncontracted per-request character limit')
  assert(validateHunanApplication({factsReason:'😀'.repeat(1800)}).valid)
  assert(!validateHunanApplication({factsReason:'😀'.repeat(1801)}).valid)
  const item={name:'汉'.repeat(300),source:'汉'.repeat(300),purpose:'汉'.repeat(300)}
  assert(validateHunanApplication({evidenceList:Array.from({length:10},()=>({...item}))}).valid)
  assert(!validateHunanApplication({evidenceList:Array.from({length:11},()=>({...item}))}).valid)
  for(const key of ['name','source','purpose']){
    const value={evidenceList:[{...item,[key]:'汉'.repeat(301)}]}
    const result=validateHunanApplication(value);assert(!result.valid)
    assert(result.errors.some(e=>e.field===`evidenceList.0.${key}`&&/300/.test(e.message)))
  }
})
test('unknown legacy fields, signatures, invalid shapes and XML-invalid text are rejected in Chinese',()=>{
  for(const value of [
    {idNumber:'旧隐藏身份证号'},{signature:'自动签名'},{submitterName:'自动签名'},{address:'合同外别名'},
    {evidenceList:[{name:'证据',idNumber:'旧隐藏身份证号'}]}, {requests:'请求'}, {requests:[12]},
    {evidenceList:[null]},{evidenceList:[{name:12}]},{applicantName:12},{factsReason:'坏\0字符'},null,[],
  ]){
    const result=validateHunanApplication(value);assert(!result.valid,JSON.stringify(value))
    assert(result.errors.every(e=>e.field&&e.label&&/[\u4e00-\u9fff]/u.test(e.message)))
    assert.throws(()=>hunanApplicationPayload(value),error=>error instanceof Error&&/[\u4e00-\u9fff]/u.test(error.message)&&Array.isArray(error.fieldErrors))
  }
})
test('unknown properties on lists cannot be silently discarded during serialization',()=>{
  const requests=['请求'];requests.idNumber='旧隐藏身份证号'
  const evidenceList=[{name:'证据',source:'来源',purpose:'目的'}];evidenceList.signature='旧签名'
  for(const value of [{requests},{evidenceList}]){
    assert(!validateHunanApplication(value).valid)
    assert.throws(()=>hunanApplicationPayload(value),/[\u4e00-\u9fff]/u)
  }
})
test('payload is a lossless deep copy and does not filter blank list items',()=>{
  const input={...example,applicantName:'  虚构姓名  ',applicationDate:'',copyCount:'',requests:['  第一项  ','','最后一项\n第二行'],
    factsReason:'\n  保留全部输入、空白和换行。\r\n',evidenceList:[{name:'  证据  ',source:'',purpose:'\n目的\n'}]}
  const payload=hunanApplicationPayload(input);assert.deepEqual(payload,input)
  payload.requests[0]='changed';payload.evidenceList[0].name='changed'
  assert.notEqual(payload.requests[0],input.requests[0]);assert.notEqual(payload.evidenceList[0].name,input.evidenceList[0].name)
  const ownHidden=Object.defineProperty({},'applicantName',{value:'保留已允许字段的值',enumerable:false})
  assert.equal(hunanApplicationPayload(ownHidden).applicantName,'保留已允许字段的值')
})
test('capacity decisions match the actual offline Hunan provider without Word or a service',()=>{
  const cases=[{applicantName:'😀'.repeat(160)},{applicantName:'😀'.repeat(161)},{factsReason:'汉'.repeat(1800)},
    {factsReason:'汉'.repeat(1801)},{requests:Array(8).fill('请求')},{requests:Array(9).fill('请求')},
    {evidenceList:[{name:'汉'.repeat(300),source:'来源',purpose:'目的'}]},{evidenceList:[{name:'汉'.repeat(301),source:'来源',purpose:'目的'}]},
    {evidenceList:Array.from({length:10},()=>({name:'证据',source:'来源',purpose:'目的'}))},
    {evidenceList:Array.from({length:11},()=>({name:'证据',source:'来源',purpose:'目的'}))}]
  const python=spawnSync('.venv/Scripts/python.exe',['-B','-c',
    'import json,sys;sys.path.insert(0,"backend");from regional_hunan_oct29b import ROOT,parse_capture,with_capabilities,fill_document;g=with_capabilities(parse_capture("tianxin"));t=next(t for t in g["templates"] if t["can_generate"]);out=[]\nfor values in json.loads(sys.stdin.buffer.read().decode("utf8")):\n try: fill_document(g,t,"application",ROOT/t["file"],values);out.append(True)\n except ValueError: out.append(False)\nprint(json.dumps(out))'],
    {cwd:fileURLToPath(new URL('../',import.meta.url)),input:JSON.stringify(cases),encoding:'utf8'})
  assert.equal(python.status,0,python.stderr)
  assert.deepEqual(cases.map(v=>validateHunanApplication(v).valid),JSON.parse(python.stdout))
})

const require=createRequire(new URL('../frontend/package.json',import.meta.url))
const compiler=require('@vue/compiler-sfc')
assert(existsSync(componentUrl),'湖南字段组件尚未实现')
const componentText=readFileSync(componentUrl,'utf8')
const {descriptor,errors}=compiler.parse(componentText,{filename:fileURLToPath(componentUrl)})
let compiled
test('Vue SFC script, template and scoped styles compile',()=>{
  assert.deepEqual(errors,[]);compiled=compiler.compileScript(descriptor,{id:'hunan-fields-test',inlineTemplate:true})
  const template=compiler.compileTemplate({source:descriptor.template.content,filename:fileURLToPath(componentUrl),id:'hunan-fields-test',compilerOptions:{bindingMetadata:compiled.bindings}})
  assert.deepEqual(template.errors,[])
  for(const style of descriptor.styles)assert.deepEqual(compiler.compileStyle({source:style.content,filename:fileURLToPath(componentUrl),id:'hunan-fields-test',scoped:true}).errors,[])
  assert(!descriptor.template.content.includes('maxlength'),'Overlimit text must remain visible, not silently clipped')
  assert.match(descriptor.template.content,/aria-invalid/);assert.match(descriptor.template.content,/aria-describedby/)
  assert.match(componentText,/min-height:\s*44px/);assert.match(componentText,/@media/)
})

// Mount the compiled component in Vue's in-memory renderer. This exercises
// v-model/list actions and labels without opening a browser or starting a server.
const vue=require('vue')
const transformed=compiled.content.replace(/import\s*\{([^}]+)\}\s*from\s*['"]([^'"]+)['"];?/g,(_,names,source)=>
  `const {${names.replace(/\s+as\s+/g,':')}}=${source==='vue'?'__vue':'__fields'};`).replace('export default','return')
const Component=new Function('__vue','__fields',transformed)(vue,data)
const node=(type,text='')=>({type,text,children:[],props:{},parent:null})
const remove=el=>{if(el.parent){const i=el.parent.children.indexOf(el);if(i>=0)el.parent.children.splice(i,1);el.parent=null}}
const insert=(el,parent,anchor)=>{remove(el);const i=anchor?parent.children.indexOf(anchor):-1;parent.children.splice(i<0?parent.children.length:i,0,el);el.parent=parent}
const renderer=vue.createRenderer({createElement:node,createText:text=>node('#text',text),createComment:text=>node('#comment',text),
  setText:(el,text)=>{el.text=text},setElementText:(el,text)=>{el.text=text;el.children=[]},patchProp:(el,key,old,value)=>{el.props[key]=value},
  insert,remove,parentNode:el=>el.parent,nextSibling:el=>el.parent?.children[el.parent.children.indexOf(el)+1]||null,setScopeId:()=>{},
  insertStaticContent:(html,parent,anchor)=>{const el=node('#static',html);insert(el,parent,anchor);return[el,el]}})
const root=node('root'),state=vue.ref(undefined)
const app=renderer.createApp({setup:()=>()=>vue.h(Component,{modelValue:state.value,'onUpdate:modelValue':value=>{state.value=value}})})
app.mount(root);await vue.nextTick()
const all=(el=root)=>[el,...el.children.flatMap(child=>all(child))]
const text=el=>String(el.text||'')+el.children.map(text).join('')
const button=label=>all().find(el=>el.type==='button'&&(el.props['aria-label']===label||text(el).trim()===label))
const click=async label=>{const el=button(label);assert(el,`Missing button ${label}`);assert(!el.props.disabled);el.props.onClick();await vue.nextTick()}
test('mounted default is fictional and every editable control has an associated label',()=>{
  assert.deepEqual(state.value,example)
  for(const control of all().filter(el=>['input','textarea'].includes(el.type))){
    assert(control.props.id)
    assert(all().some(el=>el.type==='label'&&el.props.for===control.props.id),`Missing label for ${control.props.id}`)
    assert(control.props['aria-describedby'])
  }
})
const beforeAdd=state.value
await click('添加附随证据')
test('evidence add copies v-model without mutating the previous object',()=>{
  assert.equal(state.value.evidenceList.length,2);assert.equal(beforeAdd.evidenceList.length,1)
  assert.notStrictEqual(state.value,beforeAdd)
})
await click('删除第2项附随证据')
test('evidence removal preserves at least one row',()=>{
  assert.equal(state.value.evidenceList.length,1);assert(button('删除第1项附随证据').props.disabled)
})
state.value={...state.value,applicantName:'汉'.repeat(161)};await vue.nextTick()
test('overlimit input remains visible and its error is linked to the field',()=>{
  const input=all().find(el=>el.type==='input'&&el.props.value==='汉'.repeat(161));assert(input)
  assert.equal(input.props['aria-invalid'],'true')
  const ids=input.props['aria-describedby'].split(/\s+/)
  assert(ids.some(id=>all().some(el=>el.props.id===id&&/160/.test(text(el)))))
})
await click('添加请求事项');await click('删除第2项请求')
test('request removal preserves one row',()=>{
  assert.equal(state.value.requests.length,1);assert(button('删除第1项请求').props.disabled)
})
state.value={...createHunanApplicationExample(),requests:Array(8).fill('请求'),evidenceList:Array.from({length:10},()=>({name:'证据',source:'来源',purpose:'目的'}))}
await vue.nextTick()
test('list additions stop at eight requests and ten evidence items',()=>{
  assert(button('添加请求事项').props.disabled);assert(button('添加附随证据').props.disabled)
})
await click('清空填写内容')
test('explicit clear resets only supported fields and keeps one evidence row',()=>{
  assert.deepEqual(Object.keys(state.value).sort(),keys)
  assert.equal(state.value.applicantName,'');assert.equal(state.value.requests.length,1);assert.equal(state.value.evidenceList.length,1)
  assert(validateHunanApplication(state.value).valid)
})
app.unmount()
console.log(`PASS Hunan fields: ${passed} checks; own-provider parity, lossless payload, v-model actions, accessibility associations and Vue SFC compilation`)
