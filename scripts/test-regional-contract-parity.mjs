import assert from 'node:assert/strict'
import {createHash} from 'node:crypto'
import {readFileSync, writeFileSync, mkdirSync, existsSync} from 'node:fs'
import {createRequire} from 'node:module'
import {fileURLToPath} from 'node:url'
import {resolve, relative} from 'node:path'
import {spawnSync} from 'node:child_process'

// Full contracts come from actual, checked source providers; no local field catalogue.
// Their versions belong to a temporary fixture store, not the live publication.
const root=fileURLToPath(new URL('../',import.meta.url))
const arg=name=>{const i=process.argv.indexOf(name);return i<0?undefined:process.argv[i+1]}
const fixture=resolve(root,arg('--contracts')??'.runtime/typescript-full-contracts.json')
const reportDir=resolve(root,arg('--report-dir')??'reports/typescript-regional-contracts-20261030/shared-parity')
const python=arg('--python')??resolve(root,'.venv/Scripts/python.exe')
const pythonRun=(program,input)=>spawnSync(python,['-c',program],{cwd:root,env:{...process.env,PYTHONPATH:resolve(root,'backend'),PYTHONIOENCODING:'utf-8'},input,encoding:'utf8',maxBuffer:64*1024*1024})
let fixtureBytes
const freshSourceContracts=!existsSync(fixture) || process.argv.includes('--fresh-source-contracts')
if(!freshSourceContracts)fixtureBytes=readFileSync(fixture)
else{
  // Reproducible without a private runtime fixture or any SQLite store. Every
  // selected template still passes the real builder's own-source/root checks.
  const built=pythonRun(String.raw`
import json,socket
from pathlib import Path
from regional_form_contracts import build_form_contract
socket.create_connection=lambda *a,**k: (_ for _ in ()).throw(AssertionError('No network permitted'))
root=Path.cwd();out={};version=0
for raw in json.loads((root/'data/public-regions/guides.json').read_text(encoding='utf8')):
    if not any(t.get('can_generate') for t in raw['templates']):continue
    version+=1;guide=dict(raw,version=version)
    for template in guide['templates']:
        if not template.get('can_generate'):continue
        for kind in template['document_types']:
            key=template['adapter']+':'+kind
            if key not in out:out[key]=build_form_contract(guide,template,kind,root=root)
json.dump(out,__import__('sys').stdout,ensure_ascii=True,separators=(',',':'))
`)
  if(built.status!==0)throw new Error('Pure actual-source contract construction failed; no database was opened.')
  fixtureBytes=Buffer.from(built.stdout)
}
const contracts=JSON.parse(fixtureBytes.toString('utf8'))
const entries=Object.entries(contracts)
assert.equal(entries.length,23,'Expected all 23 actual adapter/kind profiles')
const shared=await import(new URL('../packages/regional-contracts/src/index.ts',import.meta.url))
const require=createRequire(import.meta.url)
const mini=require('../miniprogram/utils/generated/regional-contracts.js')
const clone=v=>structuredClone(v)
const sha=bytes=>createHash('sha256').update(bytes).digest('hex')
const vectors=[],local=[],failures=[],observations=[]
const fail=(profile,name,detail)=>failures.push({profile,vector:name,detail})
const add=(profile,name,data,expected)=>vectors.push({profile,name,data,expected})
const changed=(contract,key,value)=>({...clone(contract.defaults),[key]:value})
const runtimes=[['shared_ts',shared],['mini_cjs',mini]]
const sourceHash=sha(readFileSync(resolve(root,'packages/regional-contracts/src/index.ts')))
const miniHash=sha(readFileSync(resolve(root,'miniprogram/utils/generated/regional-contracts.js')))
if(!readFileSync(resolve(root,'miniprogram/utils/generated/regional-contracts.js'),'utf8').startsWith(`// Generated from packages/regional-contracts/src/index.ts. Do not edit.\n// source-sha256: ${sourceHash}\n`))fail('all','generated_source_binding','Mini generated runtime does not bind the current shared source SHA')

function localCheck(profile,name,makeData,expected=false){
  local.push({profile,name})
  for(const [runtime,api] of runtimes){
    try{assert.equal(api.validateForm(contracts[profile],makeData()).valid,expected)}
    catch{fail(profile,name,`${runtime} local shape rejection differs`)}
  }
}

for(const [profile,c] of entries){
  for(const [runtime,api] of runtimes){
    try{api.assertFormContract(c,c.context)}catch{fail(profile,'full_context_binding',`${runtime} rejected actual contract`)}
  }
  const empty=shared.createEmptyForm(c),example=shared.createExampleForm(c)
  assert.deepEqual(empty,c.defaults)
  try{assert.deepEqual(mini.createEmptyForm(c),empty);assert.deepEqual(mini.createExampleForm(c),example)}
  catch{fail(profile,'shared_mini_defaults_examples','Shared TS and mini CJS produce different defaults or examples')}
  add(profile,'defaults',empty,true)
  add(profile,'fictional_example',example,true)
  if(JSON.stringify(example)===JSON.stringify(empty))fail(profile,'fictional_example','Example fell back to the entirely blank default')
  for(const f of c.fields){
    if(f.type==='copies' || /date/i.test(f.key)){
      if(example[f.key]!==empty[f.key])fail(profile,'fictional_blank_date_copies',`Example filled ${f.key}`)
    }
  }
  add(profile,'unknown_empty_key',{...empty,unknownContractKey:''},false)
  add(profile,'unknown_empty_name',{...empty,'':''},false)
  add(profile,'top_level_array',[],false)
  add(profile,'partial_empty_record',{},true)
  localCheck(profile,'unknown_symbol',()=>({...clone(empty),[Symbol('unknown')]:''}))
  localCheck(profile,'inherited_record',()=>Object.assign(Object.create({unexpected:''}),clone(empty)))
  localCheck(profile,'null_prototype_record',()=>Object.assign(Object.create(null),clone(empty)),true)
  const checkField=(f,wrap,path)=>{
    add(profile,`${path}:null`,wrap(null),Boolean(f.nullable))
    if(f.type==='copies'){
      for(const value of ['',null,'01','000000000000000000000000000000000000001',' 2 ',-1,0,1,30,31,1.5,true,'按实际份数'])
        add(profile,`${path}:copies:${JSON.stringify(value)}`,wrap(value))
      localCheck(profile,`${path}:infinity`,()=>wrap(Infinity))
      localCheck(profile,`${path}:nan`,()=>wrap(NaN))
      return
    }
    for(const value of ['x\u0000','x\ud800','x\ufffe','x\uffff'])add(profile,`${path}:invalid_xml:${value.codePointAt(1).toString(16)}`,wrap(value),false)
    if(f.format==='iso-date'){
      for(const [value,expected] of [['',true],['0001-01-01',true],['2000-02-29',true],['2024-02-29',true],['1900-02-29',false],['2023-02-29',false],['0000-01-01',false],['2024-2-09',false],['２０２４-02-09',false]])
        add(profile,`${path}:calendar:${value}`,wrap(value),expected)
    }else if(f.choices){
      for(const value of ['',...f.choices])add(profile,`${path}:choice:${value}`,wrap(value),true)
      add(profile,`${path}:unknown_choice`,wrap('本表未列明的虚构选项'),false)
    }else if(f.maxLength){
      add(profile,`${path}:preserve_raw_whitespace`,wrap('  虚构文字\n  '))
      for(const value of ['a','文','🙂','e\u0301']){
        const unitLength=Array.from(value).length,n=Math.floor(f.maxLength/unitLength)
        add(profile,`${path}:codepoint_boundary:${value.codePointAt(0).toString(16)}`,wrap(value.repeat(n)))
        add(profile,`${path}:codepoint_over:${value.codePointAt(0).toString(16)}`,wrap(value.repeat(n+1)),false)
      }
    }
    for(const value of ['\t','\r','\n','\u0085','\ufeff','\u0378','\u{10ffff}'])add(profile,`${path}:unicode_control:${value.codePointAt(0).toString(16)}`,wrap(value))
  }
  for(const f of c.fields){
    if(f.type==='text' || f.type==='copies')checkField(f,v=>changed(c,f.key,v),f.key)
    else{
      const blank=f.type==='text_list'?'':Object.fromEntries(f.fields.map(child=>[child.key,'']))
      add(profile,`${f.key}:max_items`,changed(c,f.key,Array.from({length:f.maxItems},()=>clone(blank))))
      add(profile,`${f.key}:over_items`,changed(c,f.key,Array.from({length:f.maxItems+1},()=>clone(blank))),false)
      localCheck(profile,`${f.key}:sparse`,()=>changed(c,f.key,new Array(2)))
      localCheck(profile,`${f.key}:extra_key`,()=>changed(c,f.key,Object.assign([clone(blank)],{unexpected:''})))
      localCheck(profile,`${f.key}:symbol`,()=>changed(c,f.key,Object.assign([clone(blank)],{[Symbol('extra')]:''})))
      if(f.type==='text_list')checkField(f,v=>changed(c,f.key,[v]),`${f.key}[0]`)
      else{
        add(profile,`${f.key}:unknown_nested`,changed(c,f.key,[{...blank,unknownNested:''}]),false)
        localCheck(profile,`${f.key}:nested_symbol`,()=>changed(c,f.key,[{...clone(blank),[Symbol('extra')]:''}]))
        for(const child of f.fields)checkField(child,v=>changed(c,f.key,[{...blank,[child.key]:v}]),`${f.key}[0].${child.key}`)
      }
    }
  }
  for(const [key,max] of Object.entries(c.policy.text_list_total_max_length??{})){
    add(profile,`${key}:aggregate_equal`,changed(c,key,['a'.repeat(max)]),true)
    add(profile,`${key}:aggregate_separator_over`,changed(c,key,['a'.repeat(max),'']),false)
  }
  const layout=c.policy.layout_limits
  if(layout)for(const [key,rule] of Object.entries(layout.fields)){
    const field=c.fields.find(f=>f.key===key)
    const wrap=value=>changed(c,key,field.type==='text_list'?[value]:value)
    const limit=rule.line_widths?.[0]??rule.first_width+rule.later_width*(rule.max_lines-1)
    for(const text of ['a','文','🙂','\u0378','\u{10ffff}','e\u0301']){
      const width=Array.from(text).reduce((sum,char)=>sum+(layout.wide_ranges.some(([a,b])=>a<=char.codePointAt(0)&&char.codePointAt(0)<=b)?2:1),0)
      add(profile,`${key}:layout_width_boundary:${text.codePointAt(0).toString(16)}`,wrap(text.repeat(Math.floor(limit/width))))
      add(profile,`${key}:layout_width_over:${text.codePointAt(0).toString(16)}`,wrap(text.repeat(Math.floor(limit/width)+1)))
    }
    for(const char of ['\u0085','\u001c','\ufeff',' ']){
      add(profile,`${key}:layout_python_strip_prefix:${char.codePointAt(0).toString(16)}`,wrap(char+'a'.repeat(limit)))
      add(profile,`${key}:layout_python_strip_suffix:${char.codePointAt(0).toString(16)}`,wrap('a'.repeat(limit)+char))
    }
    add(profile,`${key}:layout_embedded_newline`,wrap('a\nb'))
    add(profile,`${key}:layout_empty_lines`,wrap('\n'.repeat(rule.max_lines+1)))
    add(profile,`${key}:layout_tab`,wrap('\t'))
    add(profile,`${key}:layout_cr`,wrap('\r'))
    if(rule.line_widths?.length>1){
      for(const [i,width] of rule.line_widths.entries()){
        const lines=Array.from({length:i},()=>''),wide='文'.repeat(Math.floor(width/2))+'a'.repeat(width%2)
        add(profile,`${key}:line_${i+1}_exact_width`,changed(c,key,[...lines,wide]),true)
        add(profile,`${key}:line_${i+1}_over_width`,changed(c,key,[...lines,wide+'a']),false)
      }
    }
  }
}

const py=String.raw`
import json,sys
from regional_form_contracts import validate_contract_data
payload=json.load(sys.stdin); out=[]
for item in payload['vectors']:
    try:
        data=validate_contract_data(payload['contracts'][item['profile']],item['data'])
        out.append({'valid':True,'normalized':data})
    except ValueError:
        out.append({'valid':False})
json.dump(out,sys.stdout,ensure_ascii=True,separators=(',',':'))
`
const child=pythonRun(py,JSON.stringify({contracts,vectors}))
if(child.status!==0)throw new Error(`Pure Python validator failed (exit ${child.status}); inspect the local runtime trace.`)
const answers=JSON.parse(child.stdout)
assert.equal(answers.length,vectors.length)
for(let i=0;i<vectors.length;i++){
  const vector=vectors[i],c=contracts[vector.profile],expected=answers[i].valid
  if(vector.expected!==undefined && expected!==vector.expected)fail(vector.profile,vector.name,'Python result differs from this invariant')
  if(expected){
    const withoutCopies=(record,fields)=>Object.fromEntries(Object.entries(record).filter(([key])=>fields.find(f=>f.key===key)?.type!=='copies').map(([key,value])=>{
      const f=fields.find(f=>f.key===key)
      return [key,f?.type==='object_list'?value.map(item=>withoutCopies(item,f.fields)):value]
    }))
    try{assert.deepEqual(withoutCopies(answers[i].normalized,c.fields),withoutCopies(vector.data,c.fields))}
    catch{fail(vector.profile,vector.name,'Python changed raw values outside declared copy normalization')}
  }
  for(const [runtime,api] of runtimes){
    let result
    try{result=api.validateForm(c,vector.data)}catch{fail(vector.profile,vector.name,`${runtime} threw during validation`);continue}
    if(result.valid!==expected)fail(vector.profile,vector.name,`${runtime}=${result.valid}; Python=${expected}`)
    if(result.valid){
      const request=api.buildGenerateRequest(c,vector.data)
      try{
        assert.deepEqual(request.data,vector.data)
        const {province,city,district,source_id,version,template_id,kind,mode}=c.context
        assert.deepEqual({...request,data:undefined},{province,city,district,source_id,version,template_id,kind,mode,contract_id:c.contract_id,data:undefined})
      }
      catch{fail(vector.profile,vector.name,`${runtime} changed raw input or exact context`)}
    }
  }
}
for(const [profile,c] of entries)observations.push({profile,adapter:c.context.adapter,kind:c.context.kind,json_vectors:vectors.filter(v=>v.profile===profile).length,local_shape_vectors:local.filter(v=>v.profile===profile).length})
if(sourceHash!==sha(readFileSync(resolve(root,'packages/regional-contracts/src/index.ts'))) || miniHash!==sha(readFileSync(resolve(root,'miniprogram/utils/generated/regional-contracts.js'))))fail('all','source_changed_during_run','Runtime sources changed while this run was executing; run again on stable bytes')
const report={schema_version:1,status:failures.length?'FAIL':'PASS',scope:'Pure runtime comparison; actual checked source contracts with synthetic fixture versions; no database or document generation.',fixtures_origin:freshSourceContracts?'fresh actual-source build_form_contract with explicit root; no store':'previously generated full-context fixture',profiles:entries.length,json_vectors:vectors.length,local_shape_vectors:local.length,runtime_checks:vectors.length*2+local.length*2,fixtures_sha256:sha(fixtureBytes),shared_source_sha256:sha(readFileSync(resolve(root,'packages/regional-contracts/src/index.ts'))),mini_generated_sha256:sha(readFileSync(resolve(root,'miniprogram/utils/generated/regional-contracts.js'))),script_sha256:sha(readFileSync(fileURLToPath(import.meta.url))),normalization:'Shared request builders retain raw values; Python may normalize declared integer copy fields. Validity is compared directly; no inferred official requirements.',coverage:observations,failures}
mkdirSync(reportDir,{recursive:true})
writeFileSync(resolve(reportDir,'RESULT.json'),JSON.stringify(report,null,2)+'\n')
console.log(`${report.status}: ${entries.length} profiles, ${vectors.length} Python/TS/CJS vectors, ${local.length} local shape vectors, ${failures.length} differences`)
for(const failure of failures.slice(0,30))console.log(`${failure.profile} | ${failure.vector} | ${failure.detail}`)
console.log(`Report: ${relative(root,resolve(reportDir,'RESULT.json')).replaceAll('\\','/')}`)
process.exitCode=failures.length?1:0
