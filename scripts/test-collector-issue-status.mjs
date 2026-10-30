import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {createRequire} from 'node:module'
import vm from 'node:vm'
import {parseCollectorStatus} from '../packages/client-contracts/src/collector.ts'

if(process.argv.includes('--wire-only')){
 const wire=JSON.parse(readFileSync(0,'utf8')),parsed=parseCollectorStatus(wire)
 assert('issue_events' in wire)
 assert.deepEqual(parsed.issue_events,wire.issue_events)
 console.log('PASS actual collector issue wire');process.exit(0)
}
const raw={counts:{},items:[],worker:null,capacity:128,concurrency:1,model_used:false,allowed_hosts:['www.zjzwfw.gov.cn'],review_required:true}
const available={enabled:true,journal:{status:'available',observations:4,states:{outbox_persisted:4}},outbox:{status:'available',events:4,pending:1,acknowledged:3},model_calls:0,ai_reviewed:false}
assert.equal(parseCollectorStatus(raw).issue_events,undefined,'Old service field omission remains compatible')
assert.deepEqual(parseCollectorStatus({...raw,issue_events:available}).issue_events,available)
const allAcknowledged={...structuredClone(available),outbox:{status:'available',events:4,pending:0,acknowledged:4}}
assert.deepEqual(parseCollectorStatus({...raw,issue_events:allAcknowledged}).issue_events,allAcknowledged)
for(const status of ['disabled','missing','error']){
 const issue={...structuredClone(available),enabled:status!=='disabled',outbox:{status,events:null,pending:null,acknowledged:null}}
 assert.deepEqual(parseCollectorStatus({...raw,issue_events:issue}).issue_events,issue)
}
const journalError={...structuredClone(available),journal:{status:'error',observations:null,states:null}}
assert.deepEqual(parseCollectorStatus({...raw,issue_events:journalError}).issue_events,journalError)
for(const mutate of [x=>x.outbox.events=true,x=>x.outbox.pending=-1,x=>x.outbox.acknowledged=2,x=>x.model_calls=1,x=>x.ai_reviewed=true,x=>x.enabled=false,
 x=>x.outbox.status='published',x=>x.outbox.path='/private/operator',x=>x.journal.observations=3,x=>x.journal.states.unknown=0,x=>x.journal.states.outbox_persisted=true,
 x=>x.journal.status='error',x=>x.outbox.status='error',x=>x.enabled='yes']){
 const issue=structuredClone(available);mutate(issue);assert.throws(()=>parseCollectorStatus({...raw,issue_events:issue}))
}
assert.throws(()=>parseCollectorStatus({...raw,issue_events:null}))
console.log('PASS strict optional collector issue contract; unavailable counts cannot masquerade as zero/success')

const require=createRequire(new URL('../frontend/package.json',import.meta.url)),vue=require('vue'),compiler=require('@vue/compiler-sfc'),ts=require('typescript')
const {renderToString}=require('@vue/server-renderer')
const filename=new URL('../frontend/src/views/OfficialCollector.vue',import.meta.url)
const source=readFileSync(filename,'utf8'),{descriptor,errors}=compiler.parse(source,{filename:filename.pathname});assert.deepEqual(errors,[])
const compiled=compiler.compileScript(descriptor,{id:'collector-issue-status-test',inlineTemplate:true})
assert.deepEqual(compiler.compileTemplate({source:descriptor.template.content,filename:filename.pathname,id:'collector-issue-status-test',compilerOptions:{bindingMetadata:compiled.bindings}}).errors,[])
const css=compiler.compileStyle({source:descriptor.styles[0].content,filename:filename.pathname,id:'collector-issue-status-test',scoped:true});assert.deepEqual(css.errors,[])
const code=ts.transpileModule(compiled.content,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020}}).outputText
let fixture,refreshCalls=0
const controller={data:vue.ref(null),loading:vue.ref(false),busy:vue.ref(false),error:vue.ref(''),message:vue.ref(''),refresh:()=>refreshCalls++,submit(){},action(){},download(){}}
const module={exports:{}}
vm.runInNewContext(code,{module,exports:module.exports,require:name=>{
 if(name==='vue')return vue
 if(name==='@/data/provinces')return{provinces:[{slug:'jiangsu',name:'江苏省'}]}
 if(name==='@/composables/useOfficialCollector')return{useOfficialCollector:()=>controller}
 throw Error('Unexpected component import '+name)
}})
async function render(issue){controller.data.value=parseCollectorStatus({...raw,...(issue===undefined?{}:{issue_events:issue})});return renderToString(vue.createSSRApp(module.exports.default))}
let html=await render(available)
for(const label of ['本采集链路','已持久问题','待 OpenClaw','实际送达','不代表 AI 已审核','指南已核验','模型调用'])assert(html.includes(label),label)
assert(html.includes('4')&&html.includes('1')&&html.includes('3'))
assert(html.includes('role="status"')&&html.includes('aria-atomic="true"'))
html=await render(allAcknowledged);assert(html.includes('<dd>0</dd>'),'An available zero pending count remains truthful after real receipt reconciliation')
for(const [status,message] of [['disabled','未配置'],['missing','尚未建立'],['error','暂不可读取']]){
 html=await render({...structuredClone(available),enabled:status!=='disabled',outbox:{status,events:null,pending:null,acknowledged:null}})
 assert(html.includes(message));assert(!html.includes('<dd>0</dd>'),'Unavailable counts must not be shown as successful zeroes')
 assert(html.includes('添加一条当地指南')&&html.includes('最近任务'))
}
html=await render(undefined);assert(html.includes('尚未提供独立问题投递状态'))
html=await render(journalError);assert(html.includes('观察日志暂不可读取'))
let tree
const probe={setup(){const draw=module.exports.default.setup({}, {expose(){}});return()=>{tree=draw({},[]);return tree}}}
await renderToString(vue.createSSRApp(probe))
const nodes=[];function walk(node){if(!node||typeof node!=='object')return;nodes.push(node);if(Array.isArray(node.children))node.children.forEach(walk)}walk(tree)
const refresh=nodes.find(n=>n.type==='button'&&String(n.children).includes('刷新状态'));assert(refresh);assert.equal(refresh.props.type,'button');refresh.props.onClick();assert.equal(refreshCalls,1)
assert(css.code.includes('minmax(0,1fr)')&&css.code.includes('@media'),'Existing responsive CSS still compiles')
console.log('PASS actual Vue SFC renders independent counts/disabled/missing/error/old-service states and preserves keyboard button action; no browser/screenshots')
