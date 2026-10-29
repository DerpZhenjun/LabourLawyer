import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {createRequire} from 'node:module'
import {spawnSync} from 'node:child_process'
import {
  FEIDONG_ADAPTER_KEY, createFeidongApplicationExample, createEmptyFeidongApplication,
  feidongDisplayWidth, feidongFieldWidth, wrapFeidongText, validateFeidongApplication, feidongApplicationPayload,
} from '../frontend/src/data/feidongApplicationFields.js'

assert.equal(FEIDONG_ADAPTER_KEY, 'anhui-feidong-official-application-20261029')
const example=createFeidongApplicationExample()
assert(validateFeidongApplication(example).valid)
assert.match(JSON.stringify(example), /虚构/)
assert(validateFeidongApplication({}).valid)
assert(validateFeidongApplication(createEmptyFeidongApplication()).valid)
const expectedKeys=['agent_lines','applicant_lines','facts','representative_lines','requests','respondent_lines']
assert.deepEqual(Object.keys(feidongApplicationPayload({})).sort(),expectedKeys)

const boundary={...createEmptyFeidongApplication(),applicant_lines:['汉'.repeat(20),'汉'.repeat(25)],
  requests:['汉'.repeat(246)],facts:'汉'.repeat(280)}
assert(validateFeidongApplication(boundary).valid)
assert.equal(wrapFeidongText(boundary.requests.join('\n'),44,56).length,9)
assert.equal(wrapFeidongText(boundary.facts).length,10)
for(const key of ['applicant_lines','agent_lines','respondent_lines','representative_lines']){
  for(const [line,width] of [[0,20],[1,25]]){
    const value=createEmptyFeidongApplication();value[key][line]='汉'.repeat(width+1)
    const result=validateFeidongApplication(value)
    assert(!result.valid)
    assert(result.errors.some(error=>error.field===`${key}.${line}` && /超出/.test(error.message)))
    assert.throws(()=>feidongApplicationPayload(value),/超出/)
  }
}
for(const value of [
  {...boundary,requests:['汉'.repeat(247)]}, {...boundary,facts:'汉'.repeat(281)},
  {...boundary,requests:Array(10).fill('请求')}, {...boundary,facts:Array(11).fill('事实').join('\n')},
  {signature:'不应自动签名'}, {applicant_lines:['第一行','第二行','第三行']},
  {applicant_lines:['第一行\n第二行']}, {facts:'不可\x00用'}, {facts:'CR\rLF'},
  {requests:'必须数组'}, {facts:42}, null,
]){
  assert(!validateFeidongApplication(value).valid,JSON.stringify(value))
  assert.throws(()=>feidongApplicationPayload(value))
}
assert(validateFeidongApplication({applicant_lines:['A'.repeat(40),'A'.repeat(50)]}).valid)
assert(!validateFeidongApplication({applicant_lines:['A'.repeat(41)]}).valid)
assert.equal(feidongDisplayWidth('A汉Ｂ😀é'),8)
assert.equal(feidongFieldWidth('  汉  '),2)
assert.equal(wrapFeidongText('\n  汉\n\n字  \n').join('|'),'汉||字')
const original={...example,requests:['  第一项  ','','第二项'],facts:'  保留所有输入文字。\n最后一行  '}
const payload=feidongApplicationPayload(original)
assert.deepEqual(payload,original,'Payload must not silently trim, filter or truncate inputs')
payload.applicant_lines[0]='Changed'
assert.notEqual(payload.applicant_lines[0],original.applicant_lines[0])
assert.notStrictEqual(createFeidongApplicationExample().requests,example.requests)

// Compare frontend width and line rules against the actual adapter rather than
// another JavaScript implementation of its rules. No server or model is used.
const samples=['ASCII汉字，ＡＢ😀é','\u0085\u3000汉\n\n字\u0085','\u0378','\u{20000}','汉'.repeat(246), 'A'.repeat(492)]
const python=spawnSync('.venv/Scripts/python.exe',['-c',
  'import sys,json;sys.path.insert(0,"backend");from regional_anhui_oct29 import _width,_wrap;print(json.dumps([[_width(s),_wrap(s,44,56)] for s in json.loads(sys.stdin.buffer.read().decode("utf8"))]))'],
{input:JSON.stringify(samples),encoding:'utf8'})
assert.equal(python.status,0,python.stderr)
assert.deepEqual(samples.map(value=>[feidongDisplayWidth(value),wrapFeidongText(value,44,56)]),JSON.parse(python.stdout))

const require=createRequire(new URL('../frontend/package.json',import.meta.url))
const {parse,compileScript,compileTemplate}=require('@vue/compiler-sfc')
const path=new URL('../frontend/src/components/FeidongApplicationFields.vue',import.meta.url)
const {descriptor,errors}=parse(readFileSync(path,'utf8'),{filename:path.pathname})
assert.deepEqual(errors,[])
const compiled=compileScript(descriptor,{id:'feidong-test'})
const template=compileTemplate({source:descriptor.template.content,filename:path.pathname,id:'feidong-test',compilerOptions:{bindingMetadata:compiled.bindings}})
assert.deepEqual(template.errors,[])
assert(!descriptor.template.content.includes('maxlength'),'Overcapacity input must remain visible for correction')
console.log('PASS Feidong: blank/example, exact capacity, overflow/control rejection, lossless payload, Python parity and Vue SFC compilation')
